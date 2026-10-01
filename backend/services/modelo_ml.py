import numpy as np
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from services.disponibilidade import valor_observado, data_utc

logger = logging.getLogger(__name__)

from services.artefactos_ml import carregar_artefactos

# Falhar antes de disponibilizar a API se o conjunto obrigatorio nao for valido.
modelo, scaler, modelo_anpc, scaler_anpc, encoder_distrito = carregar_artefactos()

FEATURES_METEO = ['temp', 'RH', 'wind', 'rain',
                  'FFMC', 'DMC', 'DC', 'ISI', 'month_num', 'day_num']
FEATURES_ANPC = ['mes', 'hora', 'dia_semana',
                 'ano', 'distrito_cod', 'lat', 'lon']


def prever_risco(dados: dict) -> dict:
    resultados, disponibilidade = {}, {}
    data = dados.get('data_hora')
    # O treino extrai hora/dia de datas civis continentais sem fuso explícito.
    observacao = data_utc(data).astimezone(ZoneInfo('Europe/Lisbon')) if isinstance(data, datetime) else None
    campos_meteo = ('temperatura', 'humidade', 'velocidade_vento', 'precipitacao', 'ffmc', 'dmc', 'dc', 'isi')
    pesos = {'prob_meteorologico': 0.4, 'prob_historico_portugal': 0.6}

    def executar(chave, estimador, normalizador, valores, faltam):
        if faltam:
            disponibilidade[chave] = {'estado': 'indisponivel', 'motivo': 'Dados obrigatórios ausentes ou inválidos.', 'campos': faltam}
            return
        if estimador is None or normalizador is None:
            disponibilidade[chave] = {'estado': 'indisponivel', 'motivo': 'Artefactos do modelo indisponíveis.'}
            return
        try:
            probabilidade = float(estimador.predict_proba(normalizador.transform(np.array([valores])))[0][1])
            if not np.isfinite(probabilidade) or not 0 <= probabilidade <= 1:
                raise ValueError('Probabilidade inválida')
            resultados[chave] = probabilidade
            disponibilidade[chave] = {'estado': 'ok'}
        except Exception:
            logger.exception('Falha na inferência do modelo %s', chave)
            disponibilidade[chave] = {'estado': 'indisponivel', 'motivo': 'Falha na inferência do modelo.'}

    faltam = [campo for campo in campos_meteo if valor_observado(dados.get(campo)) is None]
    for campo in campos_meteo[1:]:
        if campo not in faltam and (dados[campo] < 0 or (campo == 'humidade' and dados[campo] > 100)):
            faltam.append(campo)
    if observacao is None:
        faltam.append('data_hora')
    valores = [dados.get(campo) for campo in campos_meteo]
    if observacao is not None:
        valores += [observacao.month, observacao.weekday() + 1]
    executar('prob_meteorologico', modelo, scaler, valores, faltam)

    faltam = [campo for campo in ('latitude', 'longitude') if valor_observado(dados.get(campo)) is None]
    if 'latitude' not in faltam and not -90 <= dados['latitude'] <= 90:
        faltam.append('latitude')
    if 'longitude' not in faltam and not -180 <= dados['longitude'] <= 180:
        faltam.append('longitude')
    if observacao is None:
        faltam.append('data_hora')
    distrito = dados.get('distrito')
    distrito = distrito.strip().upper() if isinstance(distrito, str) else None
    if encoder_distrito is None:
        disponibilidade['prob_historico_portugal'] = {'estado': 'indisponivel', 'motivo': 'Artefactos do modelo indisponíveis.'}
    elif distrito not in encoder_distrito.classes_:
        disponibilidade['prob_historico_portugal'] = {'estado': 'indisponivel', 'motivo': 'Distrito ausente ou não reconhecido pelo modelo ANPC.', 'campos': ['distrito', *faltam]}
    else:
        try:
            codigo = int(encoder_distrito.transform([distrito])[0])
        except Exception:
            logger.exception('Falha na codificação do distrito ANPC')
            disponibilidade['prob_historico_portugal'] = {'estado': 'indisponivel', 'motivo': 'Falha na codificação do distrito ANPC.'}
        else:
            valores = [observacao.month, observacao.hour, observacao.weekday(), observacao.year,
                       codigo, dados.get('latitude'), dados.get('longitude')] if observacao is not None else []
            executar('prob_historico_portugal', modelo_anpc, scaler_anpc, valores, faltam)

    if not resultados:
        return {'estado': 'indisponivel', 'mensagem': 'Previsão ML indisponível: nenhum modelo tem uma avaliação válida.',
                'probabilidade_incendio': None, 'nivel_risco_ml': None, 'modelos': {}, 'disponibilidade': disponibilidade}
    soma_pesos = sum(pesos[chave] for chave in resultados)
    prob_final = sum(prob * pesos[chave] for chave, prob in resultados.items()) / soma_pesos
    if prob_final < 0.3:
        nivel = 'Baixo'
    elif prob_final < 0.5:
        nivel = 'Medio'
    elif prob_final < 0.7:
        nivel = 'Alto'
    else:
        nivel = 'Muito Alto'
    parcial = len(resultados) == 1
    return {'probabilidade_incendio': round(prob_final, 3), 'nivel_risco_ml': nivel,
            'modelos': {chave: round(prob, 3) for chave, prob in resultados.items()},
            'estado': 'parcial' if parcial else 'ok',
            'mensagem': 'Previsão ML parcial: apenas um modelo disponível.' if parcial else 'Previsão ML com os dois modelos disponíveis.',
            'disponibilidade': disponibilidade,
            'pesos_aplicados': {chave: pesos[chave] / soma_pesos for chave in resultados}}
