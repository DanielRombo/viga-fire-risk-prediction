"""Recolha e recuperação cronológica, sem publicar o FWI nas rotas atuais."""
import logging
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from models.fwi_diario import FWIDiario
from models.fwi_processamento import FWIHorario, FWIProcessamento
from services.fwi_diario import VERSAO_FWI, calcular_fwi_diario
from services.persistencia_fwi import guardar_resultado_fwi, restaurar_estado
from services.meteorologia_fwi import (TerritorioFWI, AmostraHorariaFWI, UNIDADES_FWI,
    DadosFWIInvalidos, instante_referencia, preparar_observacao_diaria, utc)
from services.open_meteo_fwi import PRODUTO, ErroRecolhaFWI, recolher_horas_fwi
from services.regioes_iniciais import REGIOES_RECOLHA, existentes, encontrar, normalizar

logger = logging.getLogger(__name__)
MAX_DIAS_POR_REGIAO = 3
INTERVALO_RETRY = timedelta(minutes=15)
TERRITORIOS = {normalizar(r['distrito']): TerritorioFWI.CONTINENTE for r in REGIOES_RECOLHA}
TERRITORIOS.update(acores=TerritorioFWI.ACORES, madeira=TerritorioFWI.MADEIRA)


def data_db_utc(data):
    # SQLite perde o fuso ao ler DateTime(timezone=True); todos os writes são UTC.
    return data.replace(tzinfo=timezone.utc) if data.tzinfo is None else utc(data)


def preparar_estrutura_fwi(engine):
    with engine.begin() as conn:
        if engine.dialect.name == 'postgresql':
            conn.execute(text('SELECT pg_advisory_xact_lock(4609865, 0)'))
        for modelo in (FWIDiario, FWIHorario, FWIProcessamento):
            modelo.__table__.create(conn, checkfirst=True)


def guardar_horas(db, id_regiao, horas):
    """Chamador detém o lock da região. Preservar válidos; reparar só incompletos."""
    for hora in horas:
        existente = db.query(FWIHorario).filter_by(id_regiao=id_regiao,
            instante_utc=hora.instante_utc, produto=hora.produto).one_or_none()
        if existente is None:
            db.add(FWIHorario(id_regiao=id_regiao, **asdict(hora)))
        elif (existente.latitude_consultada, existente.longitude_consultada) != (hora.latitude_consultada, hora.longitude_consultada):
            raise DadosFWIInvalidos('As coordenadas horárias persistidas diferem das coordenadas consultadas.')
        elif existente.qualidade != 'valido' and hora.qualidade == 'valido':
            for nome, valor in asdict(hora).items():
                setattr(existente, nome, valor)
    db.flush()


def preparar_dia_persistido(db, regiao, data, territorio):
    fim = instante_referencia(data, territorio)
    horas = db.query(FWIHorario).filter(
        FWIHorario.id_regiao == regiao['id_regiao'], FWIHorario.produto == PRODUTO,
        FWIHorario.instante_utc > fim-timedelta(hours=24), FWIHorario.instante_utc <= fim
    ).order_by(FWIHorario.instante_utc).all()
    if any(h.qualidade != 'valido' for h in horas):
        raise DadosFWIInvalidos('A janela FWI contém dados horários incompletos ou inválidos.')
    if any((h.latitude_consultada,h.longitude_consultada) != (regiao['latitude'],regiao['longitude']) for h in horas):
        raise DadosFWIInvalidos('As coordenadas da janela FWI não correspondem à região.')
    return preparar_observacao_diaria(id_regiao=regiao['id_regiao'],data_referencia=data,
        territorio=territorio,latitude=regiao['latitude'],origem=PRODUTO,unidades=UNIDADES_FWI,
        amostras=[AmostraHorariaFWI(data_db_utc(h.instante_utc),h.precipitacao_hora,
                                  h.temperatura,h.humidade,h.vento) for h in horas])


async def obter_dia(db,regiao,data,territorio,agora,recolher):
    try:
        return preparar_dia_persistido(db,regiao,data,territorio)
    except DadosFWIInvalidos:
        pass  # Procurar na fonte; nunca substituir faltas por zero.
    fim = instante_referencia(data,territorio)
    horas = await recolher(regiao['latitude'],regiao['longitude'],fim-timedelta(hours=23),fim,agora=agora)
    with db.begin_nested():
        guardar_horas(db,regiao['id_regiao'],horas)
    # Persistir também a evidência de dados incompletos; bloquear apenas o cálculo.
    return preparar_dia_persistido(db,regiao,data,territorio)


def registar_falha(cursor,erro,agora):
    cursor.ultima_tentativa = agora
    cursor.falhas_consecutivas += 1
    cursor.estado = 'aguardar_dados' if isinstance(erro,(DadosFWIInvalidos,ErroRecolhaFWI)) else 'erro'
    cursor.codigo_erro = getattr(erro,'codigo','dados_incompletos' if isinstance(erro,DadosFWIInvalidos) else 'erro_interno')
    cursor.causa = str(erro) if isinstance(erro,(DadosFWIInvalidos,ErroRecolhaFWI)) else 'Não foi possível concluir a transação FWI.'
    minutos = min(360, 15 * 2 ** min(cursor.falhas_consecutivas-1,5))
    cursor.proxima_tentativa = agora + timedelta(minutes=minutos)
    if cursor.codigo_erro == 'historico_necessario':
        cursor.estado = 'reconstrucao_necessaria'
        cursor.proxima_tentativa = agora+timedelta(hours=6)
    logger.warning('FWI região %s, data %s: %s', cursor.id_regiao,cursor.data_pendente,cursor.codigo_erro)


async def processar_dia(db,regiao,agora,recolher):
    """Uma transação por dia: lock, inputs, cálculo, avanço e commit pelo chamador."""
    if db.get_bind().dialect.name == 'postgresql':
        bloqueado = db.execute(text('SELECT pg_try_advisory_xact_lock(4609865, :id)'),
                              {'id':regiao['id_regiao']}).scalar()
        if not bloqueado:
            return 'ocupada'
    cursor = db.query(FWIProcessamento).filter_by(id_regiao=regiao['id_regiao'],versao=VERSAO_FWI).one_or_none()
    if cursor is None:
        cursor = FWIProcessamento(id_regiao=regiao['id_regiao'],versao=VERSAO_FWI,
            estado='pendente',tentativas=0,falhas_consecutivas=0)
        db.add(cursor)
        db.flush()
    ultimo = db.query(FWIDiario).filter_by(id_regiao=regiao['id_regiao'],versao=VERSAO_FWI,
        estado='valido').order_by(FWIDiario.data_referencia.desc()).first()
    if cursor.proxima_tentativa and data_db_utc(cursor.proxima_tentativa) > agora:
        # Um estado estabelecido inserido explicitamente pode desbloquear inicialização.
        if not (ultimo is not None and cursor.estado == 'inicializacao_necessaria'):
            return cursor.estado
    tentativa_iniciada = False
    try:
        territorio = TERRITORIOS.get(normalizar(regiao['distrito']))
        if territorio is None:
            raise DadosFWIInvalidos('O território FWI da região não está identificado.')
        if ultimo is None:
            data = agora.date()
            if instante_referencia(data,territorio) >= agora:
                data -= timedelta(days=1)
            cursor.data_pendente = None  # Não inventar o início de uma sequência.
        else:
            data = ultimo.data_referencia+timedelta(days=1)
            if cursor.data_pendente and cursor.data_pendente < data:
                # Uma data pendente sem resultado não pode ser saltada por um registo externo posterior.
                preenchidos = db.query(FWIDiario).filter(
                    FWIDiario.id_regiao == regiao['id_regiao'], FWIDiario.versao == VERSAO_FWI,
                    FWIDiario.estado == 'valido', FWIDiario.data_referencia >= cursor.data_pendente,
                    FWIDiario.data_referencia <= ultimo.data_referencia).count()
                if preenchidos != (ultimo.data_referencia-cursor.data_pendente).days+1:
                    raise DadosFWIInvalidos('Existe uma lacuna anterior ao último FWI; é necessária revisão da sequência.')
            cursor.data_pendente = data
            referencia = instante_referencia(data,territorio)
            if referencia >= agora:
                cursor.estado = 'aguardar_referencia'
                cursor.proxima_tentativa = referencia+INTERVALO_RETRY
                cursor.codigo_erro = cursor.causa = None
                return cursor.estado
        cursor.tentativas += 1
        tentativa_iniciada = True
        cursor.ultima_tentativa = agora
        obs = await obter_dia(db,regiao,data,territorio,agora,recolher)
        if ultimo is None:
            cursor.estado = 'inicializacao_necessaria'
            cursor.codigo_erro = 'sem_estado_estabelecido'
            cursor.causa = 'É necessária inicialização ou reconstrução histórica de um estado FWI estabelecido.'
            cursor.proxima_tentativa = agora+timedelta(hours=6)
            return cursor.estado
        with db.begin_nested():
            resultado = calcular_fwi_diario(obs,restaurar_estado(ultimo))
            guardar_resultado_fwi(db,resultado)
        cursor.data_pendente = data+timedelta(days=1)
        cursor.estado = 'pendente'
        cursor.falhas_consecutivas = 0
        cursor.codigo_erro = cursor.causa = cursor.proxima_tentativa = None
        return 'calculado'
    except Exception as erro:
        if not tentativa_iniciada:
            cursor.tentativas += 1
        registar_falha(cursor,erro,agora)
        if not isinstance(erro,(DadosFWIInvalidos,ErroRecolhaFWI)):
            logger.exception('Falha no processamento diário FWI da região %s',regiao['id_regiao'])
        return cursor.estado


async def processar_regiao(factory,regiao,*,agora=None,recolher=recolher_horas_fwi,limite_dias=MAX_DIAS_POR_REGIAO):
    agora = utc(agora or datetime.now(timezone.utc))
    if not 1 <= limite_dias <= MAX_DIAS_POR_REGIAO:
        raise ValueError('Limite de recuperação FWI inválido.')
    calculados = 0
    for _ in range(limite_dias):
        with factory() as db:
            with db.begin():
                estado = await processar_dia(db,regiao,agora,recolher)
        if estado != 'calculado':
            break
        calculados += 1
    return {'id_regiao':regiao['id_regiao'],'estado':estado,'calculados':calculados}


async def executar_ciclo_fwi(factory,*,agora=None,recolher=recolher_horas_fwi,regioes=None):
    agora = utc(agora or datetime.now(timezone.utc))
    resultados = []
    if regioes is None:
        regioes = []
        with factory() as db:
            registos = existentes(db)
            for entrada in REGIOES_RECOLHA:
                try:
                    regiao = encontrar(entrada,registos)
                    if regiao is None:
                        raise ValueError('Região necessária não preparada.')
                    regioes.append({'id_regiao':regiao.id_regiao,'distrito':entrada['distrito'],
                                    'latitude':regiao.latitude,'longitude':regiao.longitude})
                except ValueError:
                    logger.exception('Região FWI não resolvida: %s',entrada['nome'])
                    resultados.append({'nome':entrada['nome'],'estado':'regiao_nao_preparada','calculados':0})
    for regiao in regioes:
        try:
            from services.reconstrucao_fwi import atual, reconstruir
            with factory() as db:
                r = atual(db, regiao['id_regiao'])
                estabelecido = db.query(FWIDiario.id_fwi).filter_by(
                    id_regiao=regiao['id_regiao'], versao=VERSAO_FWI, estado='valido').first()
                tecnica = r is not None and r.concluido_em is not None and not r.substituida and (
                    r.estado in ('reconstruido', 'falha_reconstrucao')) and estabelecido is None
                if tecnica and (r.configuracao['latitude'], r.configuracao['longitude']) != (
                        regiao['latitude'], regiao['longitude']):
                    raise DadosFWIInvalidos('As coordenadas da região diferem da sequência reconstruída.')
            if tecnica:
                # Mantém a série histórica e o produto Archive; nunca publica em fwi_diario.
                resultado = await reconstruir(factory, regiao['id_regiao'], agora=agora,
                    limite_dias=MAX_DIAS_POR_REGIAO, continuar=True)
                resultados.append({'id_regiao': regiao['id_regiao'], **resultado})
                continue
            resultados.append(await processar_regiao(factory,regiao,agora=agora,recolher=recolher))
        except Exception:
            # Inclui falha de commit: nunca anunciar avanço que não foi confirmado.
            logger.exception('Transação FWI revertida na região %s',regiao['id_regiao'])
            resultados.append({'id_regiao':regiao['id_regiao'],'estado':'erro_transacao','calculados':0})
    return resultados
