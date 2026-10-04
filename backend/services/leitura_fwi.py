"""Leitura do FWI adotado. Não calcula, recolhe, promove ou altera dados."""
from datetime import date, datetime, timedelta, timezone
from dataclasses import asdict
from fastapi import HTTPException
from models.regiao import Regiao
from models.fwi_diario import FWIDiario
from models.fwi_processamento import FWIProcessamento
from models.fwi_reconstrucao import FWIReconstrucao, FWIHistoricoDia
from services.fwi_diario import VERSAO_FWI
from services.meteorologia_fwi import TerritorioFWI, instante_referencia, UNIDADES_FWI
from services.disponibilidade import valor_observado, data_utc
from services.processamento_fwi import TERRITORIOS
from services.regioes_iniciais import normalizar

ATRASO_PERMITIDO_MINUTOS = 60
INDICES = ('ffmc', 'dmc', 'dc', 'isi', 'bui', 'fwi')
MENSAGENS = {
    'ok': 'FWI diário estabelecido e atual.',
    'desatualizado': 'O FWI diário não corresponde à data esperada ou pertence a uma revisão desatualizada.',
    'indisponivel': 'Não existe um resultado FWI diário disponível para esta seleção.',
    'em_inicializacao': 'A sequência FWI ainda não está estabelecida; os valores apresentados são apenas técnicos.',
    'em_reconstrucao': 'A sequência FWI está em reconstrução; os valores apresentados não são operacionais.',
    'dados_incompletos': 'Os dados necessários ao FWI diário estão incompletos ou inválidos.',
    'erro_fonte': 'A atualização do FWI diário está bloqueada por uma falha da fonte meteorológica.',
    'estado_anterior_ausente': 'Não existe um estado anterior estabelecido para continuar o FWI diário.',
}


def agora_utc():
    return datetime.now(timezone.utc)


def timestamp(valor):
    if isinstance(valor, str):
        try:
            valor = datetime.fromisoformat(valor.replace('Z', '+00:00'))
        except ValueError:
            return None
    return data_utc(valor) if isinstance(valor, datetime) else None


def calendario(territorio, agora):
    if territorio is None:
        return {'data_referencia_esperada': None, 'prazo_calculo_utc': None,
                'atraso_permitido_minutos': ATRASO_PERMITIDO_MINUTOS}
    prazo = instante_referencia(agora.date(), territorio)+timedelta(minutes=ATRASO_PERMITIDO_MINUTOS)
    esperada = agora.date() if agora >= prazo else agora.date()-timedelta(days=1)
    return {'data_referencia_esperada': esperada, 'prazo_calculo_utc': prazo,
            'atraso_permitido_minutos': ATRASO_PERMITIDO_MINUTOS}


def selecionar(db, id_regiao, serie, revisao):
    regiao = db.query(Regiao.id_regiao, Regiao.distrito).filter(Regiao.id_regiao == id_regiao).first()
    if regiao is None:
        raise HTTPException(404, 'Região não encontrada.')
    territorio = TERRITORIOS.get(normalizar(regiao.distrito))
    op = db.query(FWIDiario).filter_by(id_regiao=id_regiao, versao=VERSAO_FWI)
    if revisao is not None:
        if serie == 'operacional':
            raise HTTPException(422, 'A seleção de revisão aplica-se apenas à série de reconstrução.')
        serie = 'reconstrucao'
    if serie == 'auto':
        serie = 'operacional' if op.first() is not None else 'reconstrucao'
    ultima = db.query(FWIReconstrucao).filter_by(id_regiao=id_regiao, versao=VERSAO_FWI).order_by(
        FWIReconstrucao.revisao.desc()).first()
    if serie == 'operacional':
        cursor = db.query(FWIProcessamento).filter_by(id_regiao=id_regiao, versao=VERSAO_FWI).one_or_none()
        return territorio, serie, None, True, op, FWIDiario, cursor
    r = ultima
    if revisao is not None:
        r = db.query(FWIReconstrucao).filter_by(id_regiao=id_regiao, versao=VERSAO_FWI, revisao=revisao).one_or_none()
        if r is None:
            raise HTTPException(404, 'Revisão FWI não encontrada para esta região.')
    ativa = bool(r is not None and ultima is not None and r.id_reconstrucao == ultima.id_reconstrucao and not r.substituida)
    query = db.query(FWIHistoricoDia).filter(FWIHistoricoDia.id_reconstrucao == (r.id_reconstrucao if r else -1))
    cursor = r
    if r is None:
        cursor = db.query(FWIProcessamento).filter_by(id_regiao=id_regiao, versao=VERSAO_FWI).one_or_none()
    return territorio, serie, r, ativa, query, FWIHistoricoDia, cursor


def falha_processamento(cursor, esperada):
    if cursor is None:
        return None
    pendente = cursor.data_pendente
    if pendente is not None and esperada is not None and pendente > esperada:
        return None
    codigo = cursor.codigo_erro
    if codigo in ('erro_fonte', 'timeout'):
        return 'erro_fonte'
    if codigo in ('dados_incompletos', 'dados_invalidos', 'resposta_invalida', 'sem_dados', 'janela_invalida'):
        return 'dados_incompletos'
    if codigo == 'sem_estado_estabelecido':
        return 'estado_anterior_ausente'
    if codigo in ('historico_necessario', 'historico_indisponivel'):
        return 'em_reconstrucao'
    if codigo == 'erro_interno':
        return 'indisponivel'
    return None


def representar(id_regiao, registo, territorio, serie, reconstrucao, ativa, cursor, agora, *, incluir_falha=True):
    r = reconstrucao
    calendario_diario = calendario(territorio, agora)
    inicializacao = r.estado if r is not None else 'sem_estado'
    qualidade = None
    if registo is not None and serie == 'operacional':
        qualidade = registo.qualidade_estado
        inicializacao = {'estabelecido': 'estabelecido', 'reconstrucao_historica': 'reconstruido',
                        'inicializacao_convencional': 'inicializado_convencionalmente',
                        'em_inicializacao': 'em_inicializacao'}.get(qualidade, 'sem_estado')
    elif r is not None:
        qualidade = (r.configuracao.get('semente') or {}).get('qualidade')
    elif cursor is not None and cursor.estado in ('inicializacao_necessaria', 'reconstrucao_necessaria'):
        inicializacao = 'sem_estado'
    obs = (registo.observacao or {}) if registo is not None and serie == 'reconstrucao' else {}
    data = registo.data_referencia if registo is not None else None
    instante = timestamp(registo.instante_referencia_utc if registo is not None and serie == 'operacional' else obs.get('instante_referencia_utc'))
    calculado = timestamp(registo.calculado_em) if registo is not None else None
    origem = registo.origem_dados if registo is not None and serie == 'operacional' else obs.get('origem')
    validade = (registo.estado if serie == 'operacional' else registo.validade) if registo is not None else 'indisponivel'
    indices = {k: valor_observado(getattr(registo, k, None)) for k in INDICES}
    for k, v in indices.items():
        if v is not None and (v < 0 or (k == 'ffmc' and v > 101)):
            indices[k] = None
    estabelecido = bool(registo is not None and qualidade == 'estabelecido' and
        ((serie == 'operacional' and validade == 'valido') or
         (serie == 'reconstrucao' and inicializacao == 'estabelecido' and validade == 'calculado' and ativa)))
    idade = 'indisponivel'
    dados_invalidos = False
    if registo is not None:
        unidades = registo.unidades if serie == 'operacional' else obs.get('unidades')
        local = registo.territorio if serie == 'operacional' else obs.get('territorio')
        dados_invalidos = (territorio is None or any(v is None for v in indices.values()) or
            instante is None or calculado is None or not origem or unidades != asdict(UNIDADES_FWI))
        if not dados_invalidos:
            dados_invalidos = (instante != instante_referencia(data, territorio) or local != territorio.value or
                               instante > agora or calculado > agora or calculado < instante)
        if not dados_invalidos:
            idade = 'desatualizado' if data < calendario_diario['data_referencia_esperada'] else 'atual'
    if dados_invalidos:
        estado = 'dados_incompletos'
        estabelecido = False
    elif not ativa and serie == 'reconstrucao' and r is not None:
        estado = 'desatualizado'
    elif validade == 'desatualizado':
        estado = 'desatualizado'
    elif inicializacao in ('em_reconstrucao', 'falha_reconstrucao'):
        estado = 'em_reconstrucao'
    elif inicializacao in ('inicializado_convencionalmente', 'reconstruido', 'em_inicializacao'):
        estado = 'em_inicializacao'
    elif registo is None:
        estado = 'indisponivel'
    elif not estabelecido:
        estado = 'em_inicializacao'
    else:
        estado = 'ok' if idade == 'atual' else 'desatualizado'
    falha = falha_processamento(cursor, calendario_diario['data_referencia_esperada']) if incluir_falha else None
    if falha and not dados_invalidos and (ativa or r is None):
        estado = falha
    return {'id_regiao': id_regiao, 'tipo': 'fwi_diario_classico', 'estado': estado,
        'mensagem': MENSAGENS[estado], 'data_referencia': data,
        'instante_referencia_utc': instante, 'calculado_em': calculado, **indices,
        'origem': origem, 'metodo': 'Canadian Fire Weather Index diário — variante clássica adotada',
        'versao': VERSAO_FWI, 'versao_xclim': '0.62.0', 'variante': 'classica_cffdrs_1.8.17',
        'qualidade': qualidade, 'validade': validade, 'estado_inicializacao': inicializacao,
        'estabelecido': estabelecido, 'operacional': estado == 'ok' and estabelecido,
        'atualidade': idade, **calendario_diario, 'serie': serie,
        'revisao': r.revisao if r else None, 'revisao_ativa': ativa if r else None,
        'proveniencia': {'id_registo': (registo.id_fwi if serie == 'operacional' else registo.id_dia) if registo else None,
                        'id_reconstrucao': r.id_reconstrucao if r else None,
                        'assinatura': registo.assinatura if registo else None},
        'processamento': {'codigo_erro': cursor.codigo_erro, 'data_pendente': cursor.data_pendente,
                         'proxima_tentativa': timestamp(cursor.proxima_tentativa)} if cursor else None}


def ler_fwi(db, id_regiao, *, serie='auto', revisao=None, agora=None,
            historico=False, inicio=None, fim=None, limite=100, offset=0):
    agora = data_utc(agora or agora_utc())
    territorio, serie, r, ativa, query, modelo, cursor = selecionar(db, id_regiao, serie, revisao)
    if not historico:
        registo = query.order_by(modelo.data_referencia.desc()).first()
        return representar(id_regiao, registo, territorio, serie, r, ativa, cursor, agora)
    if inicio is not None and fim is not None and inicio > fim:
        raise HTTPException(422, 'A data inicial não pode ser posterior à data final.')
    if inicio is not None:
        query = query.filter(modelo.data_referencia >= inicio)
    if fim is not None:
        query = query.filter(modelo.data_referencia <= fim)
    registos = query.order_by(modelo.data_referencia).offset(offset).limit(limite+1).all()
    return {'id_regiao': id_regiao, 'serie': serie, 'versao': VERSAO_FWI,
        'revisao': r.revisao if r else None, 'revisao_ativa': ativa if r else None,
        'limite': limite, 'offset': offset, 'tem_mais': len(registos) > limite,
        'resultados': [representar(id_regiao, linha, territorio, serie, r, ativa, cursor, agora,
                                   incluir_falha=False) for linha in registos[:limite]]}
