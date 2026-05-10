from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from config.database import get_db
from services.fwi import calcular_risco_regiao
from services.modelo_ml import prever_risco
from models.dado_meteorologico import DadoMeteorologico

router = APIRouter()


@router.get("/risco/{id_regiao}")
def get_risco_regiao(id_regiao: int, db: Session = Depends(get_db)):
    ultimo_dado = db.query(DadoMeteorologico)\
        .filter(DadoMeteorologico.id_regiao == id_regiao)\
        .order_by(DadoMeteorologico.data_hora.desc())\
        .first()

    if not ultimo_dado:
        return {"erro": "Sem dados meteorologicos para esta regiao"}

    dados = {
        "temperatura": ultimo_dado.temperatura,
        "humidade": ultimo_dado.humidade,
        "velocidade_vento": ultimo_dado.velocidade_vento,
        "precipitacao": ultimo_dado.precipitacao
    }

    resultado_fwi = calcular_risco_regiao(dados)

    resultado_ml = prever_risco(dados)

    return {
        "id_regiao": id_regiao,
        "data_hora": ultimo_dado.data_hora,
        "dados_meteorologicos": dados,
        "fwi": resultado_fwi,
        "ml": resultado_ml
    }
