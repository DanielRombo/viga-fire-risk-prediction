"""Reconstrução explícita e revista. Nunca publica em fwi_diario ou nas rotas."""
import hashlib
import json
import logging
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from sqlalchemy import text
from models.fwi_diario import FWIDiario
from models.fwi_processamento import FWIHorario
from models.fwi_reconstrucao import FWIReconstrucao, FWIHistoricoDia
from services.fwi_diario import EstadoFWI, QualidadeEstado, VERSAO_FWI, calcular_fwi_diario
from services.meteorologia_fwi import (DadosFWIInvalidos, TerritorioFWI, AmostraHorariaFWI,
    UNIDADES_FWI, instante_referencia, preparar_observacao_diaria, numero, utc)
from services.persistencia_fwi import restaurar_estado
from services.processamento_fwi import preparar_estrutura_fwi, guardar_horas, data_db_utc, MAX_DIAS_POR_REGIAO
from services.open_meteo_fwi import ErroRecolhaFWI, HoraRecolhida
from services.open_meteo_historico_fwi import PRODUTO, URL, MODELO, recolher_historico_fwi

logger = logging.getLogger(__name__)
JANELA_INICIAL_DIAS = 365  # Configuração técnica, não critério científico de estabelecimento.
CAMPOS_INDICES = ('ffmc', 'dmc', 'dc', 'isi', 'bui', 'fwi')


def serializar(valor):
    def converter(v):
        if isinstance(v, (datetime, date)):
            return v.isoformat()
        if isinstance(v, Enum):
            return v.value
        raise TypeError(type(v).__name__)
    return json.loads(json.dumps(valor, default=converter, allow_nan=False))


def assinatura(valor):
    return hashlib.sha256(json.dumps(valor, sort_keys=True, allow_nan=False,
                                    separators=(',', ':')).encode()).hexdigest()


def preparar_estrutura_historica(engine):
    preparar_estrutura_fwi(engine)
    with engine.begin() as conn:
        if engine.dialect.name == 'postgresql':
            conn.execute(text('SELECT pg_advisory_xact_lock(4609865, 0)'))
        for modelo in (FWIReconstrucao, FWIHistoricoDia):
            modelo.__table__.create(conn, checkfirst=True)


def bloquear(db, id_regiao):
    if type(id_regiao) is not int or id_regiao <= 0:
        raise DadosFWIInvalidos('Região inválida.')
    if db.get_bind().dialect.name != 'postgresql':
        return True  # SQLite só é suportado nos testes sequenciais.
    return bool(db.execute(text('SELECT pg_try_advisory_xact_lock(4609865, :id)'),
                           {'id': id_regiao}).scalar())


def atual(db, id_regiao):
    return db.query(FWIReconstrucao).filter_by(id_regiao=id_regiao, versao=VERSAO_FWI).order_by(
        FWIReconstrucao.revisao.desc()).first()


def resumo(r):
    if r is None:
        return {'estado': 'sem_estado'}
    return {'estado': r.estado, 'revisao': r.revisao, 'id_reconstrucao': r.id_reconstrucao,
            'data_pendente': r.data_pendente.isoformat(), 'codigo_erro': r.codigo_erro,
            'causa': r.causa, 'proxima_tentativa':
            data_db_utc(r.proxima_tentativa).isoformat() if r.proxima_tentativa else None}


def consultar_reconstrucao(factory, id_regiao):
    with factory() as db:
        return resumo(atual(db, id_regiao))


def estado_snapshot(snapshot):
    valores = dict(snapshot)
    valores['data_referencia'] = date.fromisoformat(valores['data_referencia'])
    valores['qualidade'] = QualidadeEstado(valores['qualidade'])
    return EstadoFWI(**valores)


def validar_semente(db, configuracao):
    semente = estado_snapshot(configuracao['semente'])
    if semente.qualidade == QualidadeEstado.ESTABELECIDO:
        persistido = db.get(FWIDiario, semente.id_fwi) if semente.id_fwi else None
        if (persistido is None or restaurar_estado(persistido) != semente or
                persistido.latitude != configuracao['latitude'] or
                persistido.territorio != configuracao['territorio']):
            raise DadosFWIInvalidos('O estado estabelecido deve corresponder a um FWI válido persistido da região.')
    elif semente.qualidade != QualidadeEstado.CONVENCIONAL or semente.id_fwi is not None:
        raise DadosFWIInvalidos('A semente deve ser convencional explícita ou um estado estabelecido persistido.')
    return semente


def iniciar_reconstrucao(factory, *, id_regiao, latitude, longitude, territorio,
                        data_operacional, estado_inicial, data_inicial=None,
                        janela_dias=JANELA_INICIAL_DIAS, agora=None):
    agora = utc(agora or datetime.now(timezone.utc))
    if type(janela_dias) is not int or not 1 <= janela_dias <= 36525 or type(data_operacional) is not date:
        raise DadosFWIInvalidos('Janela histórica ou data operacional inválida.')
    inicio = data_inicial if data_inicial is not None else data_operacional-timedelta(days=janela_dias)
    if type(inicio) is not date or inicio >= data_operacional or inicio < date(2017, 1, 2):
        raise DadosFWIInvalidos('A janela histórica IFS deve começar após 1 de janeiro de 2017 e preceder a data operacional.')
    instante_referencia(inicio, territorio)
    if not isinstance(estado_inicial, EstadoFWI) or estado_inicial.id_regiao != id_regiao or estado_inicial.data_referencia != inicio-timedelta(days=1):
        raise DadosFWIInvalidos('É necessário um estado inicial explícito do dia imediatamente anterior à janela.')
    config = serializar({'semente': asdict(estado_inicial), 'territorio': territorio,
        'latitude': numero(latitude, 'latitude', -90, 90),
        'longitude': numero(longitude, 'longitude', -180, 180),
        'data_inicial': inicio, 'data_operacional': data_operacional,
        'janela_dias': (data_operacional-inicio).days, 'produto': PRODUTO,
        'endpoint': URL, 'modelo': MODELO, 'unidades': asdict(UNIDADES_FWI)})
    with factory.begin() as db:
        if not bloquear(db, id_regiao):
            return {'estado': 'ocupada'}
        validar_semente(db, config)
        r = atual(db, id_regiao)
        if r is not None:
            if r.assinatura_configuracao != assinatura(config):
                raise DadosFWIInvalidos('Já existe uma reconstrução com outra configuração; não será substituída silenciosamente.')
            return resumo(r)
        r = FWIReconstrucao(id_regiao=id_regiao, versao=VERSAO_FWI, revisao=1,
            estado='inicializado_convencionalmente' if estado_inicial.qualidade == QualidadeEstado.CONVENCIONAL else 'em_reconstrucao',
            data_inicial=inicio, data_operacional=data_operacional, data_pendente=inicio,
            configuracao=config, assinatura_configuracao=assinatura(config), criado_em=agora)
        db.add(r)
        db.flush()
        return resumo(r)


def horas_db(db, r, data):
    fim = instante_referencia(data, TerritorioFWI(r.configuracao['territorio']))
    return db.query(FWIHorario).filter(FWIHorario.id_regiao == r.id_regiao,
        FWIHorario.produto == PRODUTO, FWIHorario.instante_utc > fim-timedelta(hours=24),
        FWIHorario.instante_utc <= fim).order_by(FWIHorario.instante_utc).all()


def snapshot_horas(horas):
    return serializar([{k: (data_db_utc(getattr(h, k)) if k in ('instante_utc', 'ingerido_em') else getattr(h, k))
                        for k in HoraRecolhida.__dataclass_fields__}
                       for h in sorted(horas, key=lambda h: data_db_utc(h.instante_utc))])


def assinatura_horas(horas):
    # Uma nova consulta sem alteração dos dados não exige recálculo.
    return assinatura([{k: v for k, v in h.items() if k != 'ingerido_em'} for h in horas])


def preparar_horas(r, data, horas):
    config = r.configuracao
    if len(horas) != 24:
        raise DadosFWIInvalidos('São necessários exatamente 24 intervalos históricos para o dia FWI.')
    if any(h.produto != PRODUTO or h.qualidade != 'valido' or
           (h.latitude_consultada, h.longitude_consultada) != (config['latitude'], config['longitude'])
           for h in horas):
        raise DadosFWIInvalidos('A janela histórica contém dados inválidos, incompletos ou de outra origem/localização.')
    return preparar_observacao_diaria(id_regiao=r.id_regiao, data_referencia=data,
        territorio=TerritorioFWI(config['territorio']), latitude=config['latitude'], origem=PRODUTO,
        unidades=UNIDADES_FWI, amostras=[AmostraHorariaFWI(data_db_utc(h.instante_utc),
            h.precipitacao_hora, h.temperatura, h.humidade, h.vento) for h in horas])


def nova_revisao(db, r, data, antes, depois, motivo, agora):
    # Não apagar histórico nem reescrever índices antigos: a revisão tem outra cadeia.
    revisoes = db.query(FWIReconstrucao.id_reconstrucao).filter_by(id_regiao=r.id_regiao, versao=r.versao)
    db.query(FWIHistoricoDia).filter(FWIHistoricoDia.id_reconstrucao.in_(revisoes),
        FWIHistoricoDia.data_referencia >= data).update({'validade': 'desatualizado'}, synchronize_session=False)
    r.substituida = 1
    novo = FWIReconstrucao(id_regiao=r.id_regiao, versao=r.versao, revisao=r.revisao+1,
        estado='em_reconstrucao', data_inicial=r.data_inicial, data_operacional=r.data_operacional,
        data_pendente=r.data_inicial, configuracao=r.configuracao,
        assinatura_configuracao=r.assinatura_configuracao,
        correcao={'data': data.isoformat(), 'antes': antes, 'depois': depois,
                  'motivo': motivo, 'revisao_anterior': r.revisao}, criado_em=agora)
    db.add(novo)
    db.flush()
    return novo


def detetar_alteracoes(db, r, agora):
    dias = db.query(FWIHistoricoDia).filter_by(id_reconstrucao=r.id_reconstrucao).order_by(
        FWIHistoricoDia.data_referencia).all()
    for dia in dias:
        depois = snapshot_horas(horas_db(db, r, dia.data_referencia))
        if assinatura_horas(dia.horas) != assinatura_horas(depois):
            return nova_revisao(db, r, dia.data_referencia, dia.horas, depois,
                               'Alteração detetada nos inputs horários persistidos.', agora)
    return r


async def corrigir_dia_historico(factory, id_regiao, data, *, motivo, agora=None,
                               recolher=recolher_historico_fwi):
    """Recolha explícita de uma revisão da fonte; atualização e invalidação atómicas."""
    if not isinstance(motivo, str) or not motivo.strip():
        raise DadosFWIInvalidos('É obrigatório indicar o motivo da revisão histórica.')
    agora = utc(agora or datetime.now(timezone.utc))
    with factory.begin() as db:
        if not bloquear(db, id_regiao):
            return {'estado': 'ocupada'}
        r = atual(db, id_regiao)
        if r is None or type(data) is not date or not r.data_inicial <= data < max(r.data_operacional, r.data_pendente):
            raise DadosFWIInvalidos('A data corrigida deve pertencer à janela de uma reconstrução existente.')
        fim = instante_referencia(data, TerritorioFWI(r.configuracao['territorio']))
        horas = await recolher(r.configuracao['latitude'], r.configuracao['longitude'],
                              fim-timedelta(hours=23), fim, agora=agora)
        preparar_horas(r, data, horas)
        guardadas = horas_db(db, r, data)
        antes, depois = snapshot_horas(guardadas), snapshot_horas(horas)
        if assinatura_horas(antes) == assinatura_horas(depois):
            return resumo(r)
        existentes = {data_db_utc(h.instante_utc): h for h in guardadas}
        for hora in horas:
            registo = existentes.get(hora.instante_utc)
            if registo is None:
                db.add(FWIHorario(id_regiao=id_regiao, **asdict(hora)))
            else:
                for k, v in asdict(hora).items():
                    setattr(registo, k, v)
        novo = nova_revisao(db, r, data, antes, depois, motivo.strip(), agora)
        return resumo(novo)


async def calcular_dia(db, r, agora, recolher):
    data = r.data_pendente
    semente = validar_semente(db, r.configuracao)
    anterior_dia = None
    if data == r.data_inicial:
        anterior = semente
    else:
        anterior_dia = db.query(FWIHistoricoDia).filter_by(id_reconstrucao=r.id_reconstrucao,
            data_referencia=data-timedelta(days=1), validade='calculado').one_or_none()
        if anterior_dia is None:
            raise DadosFWIInvalidos('Falta o dia imediatamente anterior da reconstrução.')
        anterior = EstadoFWI(r.id_regiao, anterior_dia.data_referencia, anterior_dia.ffmc,
            anterior_dia.dmc, anterior_dia.dc, semente.qualidade, semente.origem)
    fim = instante_referencia(data, TerritorioFWI(r.configuracao['territorio']))
    if fim >= agora:
        raise ErroRecolhaFWI('aguardar_referencia', 'A referência histórica ainda não está concluída.')
    horas = horas_db(db, r, data)
    try:
        obs = preparar_horas(r, data, horas)
    except DadosFWIInvalidos:
        novas = await recolher(r.configuracao['latitude'], r.configuracao['longitude'],
                               fim-timedelta(hours=23), fim, agora=agora)
        if any(h.produto != PRODUTO for h in novas):
            raise DadosFWIInvalidos('A fonte histórica devolveu outro produto.')
        guardar_horas(db, r.id_regiao, novas)
        horas = horas_db(db, r, data)
        obs = preparar_horas(r, data, horas)
    resultado = calcular_fwi_diario(obs, anterior)
    observacao = serializar(asdict(obs))
    estado = serializar(asdict(anterior))
    snapshots = snapshot_horas(horas)
    registo = FWIHistoricoDia(id_reconstrucao=r.id_reconstrucao, data_referencia=data,
        id_anterior=anterior_dia.id_dia if anterior_dia else None, observacao=observacao,
        horas=snapshots, estado_anterior=estado,
        assinatura=assinatura({'observacao': observacao, 'anterior': estado,
                              'horas': assinatura_horas(snapshots), 'versao': r.versao}),
        **{k: getattr(resultado, k) for k in CAMPOS_INDICES},
        validade='calculado', calculado_em=resultado.calculado_em)
    db.add(registo)
    db.flush()
    r.data_pendente = data+timedelta(days=1)
    r.estado = 'em_reconstrucao'
    r.codigo_erro = r.causa = r.proxima_tentativa = None
    r.falhas_consecutivas = 0
    if r.data_pendente >= r.data_operacional:
        r.estado = 'estabelecido' if semente.qualidade == QualidadeEstado.ESTABELECIDO else 'reconstruido'
        r.concluido_em = r.concluido_em or agora


async def reconstruir(factory, id_regiao, *, limite_dias=3, agora=None,
                      recolher=recolher_historico_fwi, continuar=False):
    if type(limite_dias) is not int or not 1 <= limite_dias <= 366:
        raise DadosFWIInvalidos('Cada execução histórica deve processar entre 1 e 366 dias.')
    if continuar and limite_dias > MAX_DIAS_POR_REGIAO:
        raise DadosFWIInvalidos('A continuação técnica excede o limite de recuperação diária.')
    agora = utc(agora or datetime.now(timezone.utc))
    calculados = 0
    saida = {'estado': 'sem_estado'}
    for indice in range(limite_dias):
        with factory.begin() as db:
            if not bloquear(db, id_regiao):
                return {'estado': 'ocupada', 'calculados': calculados}
            r = atual(db, id_regiao)
            if r is None:
                return {'estado': 'sem_estado', 'calculados': 0}
            if continuar and (r.substituida or r.concluido_em is None or
                    r.estado not in ('reconstruido', 'falha_reconstrucao') or
                    estado_snapshot(r.configuracao['semente']).qualidade != QualidadeEstado.CONVENCIONAL):
                return {**resumo(r), 'calculados': calculados}
            if indice == 0:
                r = detetar_alteracoes(db, r, agora)
                if continuar and r.concluido_em is None:
                    # Uma revisão invalidada exige reconstrução explícita, não um salto.
                    return {**resumo(r), 'calculados': calculados}
            if r.proxima_tentativa and data_db_utc(r.proxima_tentativa) > agora:
                return {**resumo(r), 'calculados': calculados}
            if not continuar and r.data_pendente >= r.data_operacional:
                return {**resumo(r), 'calculados': calculados}
            if continuar and instante_referencia(r.data_pendente,
                    TerritorioFWI(r.configuracao['territorio'])) >= agora:
                return {**resumo(r), 'calculados': calculados}
            r.tentativas += 1
            r.ultima_tentativa = agora
            sucesso = False
            try:
                with db.begin_nested():
                    if continuar:
                        dias = db.query(FWIHistoricoDia).filter(
                            FWIHistoricoDia.id_reconstrucao == r.id_reconstrucao,
                            FWIHistoricoDia.validade == 'calculado',
                            FWIHistoricoDia.data_referencia >= r.data_inicial,
                            FWIHistoricoDia.data_referencia < r.data_pendente).count()
                        if dias != (r.data_pendente-r.data_inicial).days or dias == 0:
                            raise DadosFWIInvalidos('A sequência reconstruída contém uma lacuna; é necessária revisão.')
                    await calcular_dia(db, r, agora, recolher)
                sucesso = True
            except Exception as erro:
                r.estado = 'falha_reconstrucao'
                r.falhas_consecutivas += 1
                r.codigo_erro = getattr(erro, 'codigo', 'dados_invalidos' if isinstance(erro, DadosFWIInvalidos) else 'erro_interno')
                r.causa = str(erro) if isinstance(erro, (DadosFWIInvalidos, ErroRecolhaFWI)) else 'Não foi possível concluir o dia histórico FWI.'
                r.proxima_tentativa = agora+timedelta(minutes=min(360, 15*2**min(r.falhas_consecutivas-1, 5)))
                if isinstance(erro, (DadosFWIInvalidos, ErroRecolhaFWI)):
                    logger.warning('Reconstrução FWI interrompida: região %s, data %s: %s',
                                   id_regiao, r.data_pendente, r.causa)
                else:
                    logger.exception('Falha interna na reconstrução FWI da região %s', id_regiao)
            saida = resumo(r)
        # Só contar depois do commit. Falhas do próprio commit propagam-se.
        if not sucesso:
            break
        calculados += 1
    return {**saida, 'calculados': calculados}
