"""Persistência idempotente; o chamador controla commit/rollback da transação."""
import hashlib
import json
from dataclasses import asdict
from sqlalchemy.exc import IntegrityError
from models.fwi_diario import FWIDiario
from services.fwi_diario import EstadoFWI, QualidadeEstado, ResultadoFWI, VERSAO_FWI
from services.meteorologia_fwi import DadosFWIInvalidos, numero, utc


def preparar_tabela_fwi(engine):
    """Criação explícita e aditiva. Não é chamada pelo startup nem pelo scheduler."""
    FWIDiario.__table__.create(engine, checkfirst=True)


def restaurar_estado(registo: FWIDiario) -> EstadoFWI:
    qualidade = QualidadeEstado(registo.qualidade_estado)
    esperado = 'valido' if qualidade == QualidadeEstado.ESTABELECIDO else 'em_inicializacao'
    if registo.estado != esperado:
        raise DadosFWIInvalidos('A validade do estado persistido é inconsistente.')
    return EstadoFWI(registo.id_regiao, registo.data_referencia, registo.ffmc, registo.dmc,
                     registo.dc, qualidade, registo.origem_estado, registo.versao, registo.id_fwi)


def guardar_resultado_fwi(db, resultado: ResultadoFWI) -> FWIDiario:
    if not isinstance(resultado, ResultadoFWI) or resultado.versao != VERSAO_FWI:
        raise DadosFWIInvalidos('Resultado FWI ou versão inválido.')
    observacao, anterior = resultado.observacao, resultado.anterior
    # Validar a ligação persistente, incluindo snapshot, região, data e qualidade.
    if anterior.id_fwi is not None:
        guardado = db.get(FWIDiario, anterior.id_fwi)
        if guardado is None or restaurar_estado(guardado) != anterior:
            raise DadosFWIInvalidos('O estado anterior não corresponde ao registo persistido.')
    snapshot = asdict(anterior)
    snapshot['data_referencia'] = anterior.data_referencia.isoformat()
    snapshot['qualidade'] = anterior.qualidade.value
    entradas = asdict(observacao)
    entradas['data_referencia'] = observacao.data_referencia.isoformat()
    entradas['instante_referencia_utc'] = observacao.instante_referencia_utc.isoformat()
    entradas['territorio'] = observacao.territorio.value
    assinatura = hashlib.sha256(json.dumps(
        {'observacao': entradas, 'anterior': snapshot, 'versao': resultado.versao},
        sort_keys=True, allow_nan=False, separators=(',', ':')).encode()).hexdigest()
    indices = {k: numero(getattr(resultado, k), k, 0, 101 if k == 'ffmc' else None)
               for k in ('ffmc', 'dmc', 'dc', 'isi', 'bui', 'fwi')}
    registo = FWIDiario(
        **{k: getattr(observacao, k) for k in ('id_regiao', 'data_referencia', 'instante_referencia_utc',
                                             'latitude', 'temperatura', 'humidade', 'vento', 'precipitacao_24h')},
        territorio=observacao.territorio.value, **indices, id_anterior=anterior.id_fwi,
        estado_anterior=snapshot, versao=resultado.versao, estado=resultado.estado,
        qualidade_estado=anterior.qualidade.value, origem_dados=observacao.origem,
        origem_estado=anterior.origem, unidades=asdict(observacao.unidades), assinatura=assinatura,
        calculado_em=utc(resultado.calculado_em))
    try:
        # A restrição única também protege duas transações concorrentes.
        with db.begin_nested():
            db.add(registo)
            db.flush()
        return registo
    except IntegrityError:
        existente = db.query(FWIDiario).filter_by(
            id_regiao=observacao.id_regiao, data_referencia=observacao.data_referencia,
            versao=resultado.versao).one_or_none()
        if existente is None:
            raise
        if existente.assinatura != assinatura or any(getattr(existente, k) != v for k, v in indices.items()):
            raise DadosFWIInvalidos('Já existe FWI para esta região, data e versão com inputs ou resultados diferentes.')
        return existente
