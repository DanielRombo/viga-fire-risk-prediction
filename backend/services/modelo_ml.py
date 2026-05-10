import joblib
import numpy as np
import logging
import os

logger = logging.getLogger(__name__)


MODELO_PATH = os.path.join(os.path.dirname(
    __file__), "../ml_models/modelo_risco.joblib")
SCALER_PATH = os.path.join(os.path.dirname(
    __file__), "../ml_models/scaler.joblib")


try:
    modelo = joblib.load(MODELO_PATH)
    scaler = joblib.load(SCALER_PATH)
    logger.info(f"Modelo carregado: {type(modelo)}")
    logger.info(f"Scaler carregado: {type(scaler)}")
except Exception as e:
    logger.error(f"Erro ao carregar modelo: {e}")
    modelo = None
    scaler = None

FEATURES = ['temp', 'RH', 'wind', 'rain', 'FFMC',
            'DMC', 'DC', 'ISI', 'month_num', 'day_num']


def prever_risco(dados: dict) -> dict:
    if modelo is None or scaler is None:
        return {"erro": "Modelo nao disponivel"}

    from datetime import datetime

    agora = datetime.utcnow()
    X = np.array([[
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

    X_scaled = scaler.transform(X)

    probabilidade = modelo.predict_proba(X_scaled)[0][1]
    previsao = modelo.predict(X_scaled)[0]

    if probabilidade < 0.3:
        nivel = "Baixo"
    elif probabilidade < 0.5:
        nivel = "Medio"
    elif probabilidade < 0.7:
        nivel = "Alto"
    else:
        nivel = "Muito Alto"

    return {
        "previsao": int(previsao),
        "probabilidade_incendio": round(float(probabilidade), 3),
        "nivel_risco_ml": nivel
    }
