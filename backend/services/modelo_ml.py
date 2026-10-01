import numpy as np
import logging
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)

from services.artefactos_ml import carregar_artefactos

# Falhar antes de disponibilizar a API se o conjunto obrigatorio nao for valido.
modelo, scaler, modelo_anpc, scaler_anpc, encoder_distrito = carregar_artefactos()

FEATURES_METEO = ['temp', 'RH', 'wind', 'rain',
                  'FFMC', 'DMC', 'DC', 'ISI', 'month_num', 'day_num']
FEATURES_ANPC = ['mes', 'hora', 'dia_semana',
                 'ano', 'distrito_cod', 'lat', 'lon']


def prever_risco(dados: dict) -> dict:
    agora = datetime.utcnow()
    resultados = {}

    # Modelo meteorologico (Kaggle)
    if modelo and scaler:
        try:
            X_meteo = np.array([[
                dados.get("temperatura", 20),
                dados.get("humidade", 50),
                dados.get("velocidade_vento", 0),
                dados.get("precipitacao", 0),
                dados.get("ffmc", 85),
                dados.get("dmc", 100),
                dados.get("dc", 500),
                dados.get("isi", 8),
                agora.month,
                agora.weekday() + 1
            ]])
            X_meteo_s = scaler.transform(X_meteo)
            prob_meteo = float(modelo.predict_proba(X_meteo_s)[0][1])
            resultados['prob_meteorologico'] = round(prob_meteo, 3)
        except Exception as e:
            logger.error(f"Erro modelo meteorologico: {e}")
            logger.error(traceback.format_exc())

    # Modelo ANPC (historico Portugal)
    if modelo_anpc and scaler_anpc and encoder_distrito:
        try:
            distrito = dados.get("distrito", "Desconhecido")
            try:
                distrito_cod = encoder_distrito.transform([distrito])[0]
            except:
                distrito_cod = 0

            X_anpc = np.array([[
                agora.month,
                agora.hour,
                agora.weekday(),
                agora.year,
                distrito_cod,
                dados.get("latitude", 39.5),
                dados.get("longitude", -8.0)
            ]])
            X_anpc_s = scaler_anpc.transform(X_anpc)
            prob_anpc = float(modelo_anpc.predict_proba(X_anpc_s)[0][1])
            resultados['prob_historico_portugal'] = round(prob_anpc, 3)
        except Exception as e:
            logger.error(f"Erro modelo ANPC: {e}")
            logger.error(traceback.format_exc())

    # Ensemble — media ponderada
    probs = []
    if 'prob_meteorologico' in resultados:
        probs.append(resultados['prob_meteorologico'] * 0.4)
    if 'prob_historico_portugal' in resultados:
        probs.append(resultados['prob_historico_portugal'] * 0.6)

    if probs:
        prob_final = sum(probs) / len(probs) * (10 / 5)
        prob_final = min(prob_final, 1.0)
    else:
        return {"erro": "Modelos nao disponiveis"}

    # Classificar risco
    if prob_final < 0.3:
        nivel = "Baixo"
    elif prob_final < 0.5:
        nivel = "Medio"
    elif prob_final < 0.7:
        nivel = "Alto"
    else:
        nivel = "Muito Alto"

    return {
        "probabilidade_incendio": round(prob_final, 3),
        "nivel_risco_ml": nivel,
        "modelos": resultados
    }
