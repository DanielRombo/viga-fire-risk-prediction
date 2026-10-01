from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from config.database import get_db
from services.fwi import calcular_risco_regiao
from services.modelo_ml import prever_risco
from models.dado_meteorologico import DadoMeteorologico
from services.disponibilidade import estado_observacao, valor_observado, data_utc

router = APIRouter()


@router.get("/risco/{id_regiao}")
def get_risco_regiao(id_regiao: int, db: Session = Depends(get_db)):
    ultimo_dado = db.query(DadoMeteorologico)\
        .filter(DadoMeteorologico.id_regiao == id_regiao)\
        .order_by(DadoMeteorologico.data_hora.desc())\
        .first()

    if not ultimo_dado:
        return {"erro": "Sem dados meteorologicos para esta regiao", "estado": "sem_dados"}

    dados = {
        "temperatura": valor_observado(ultimo_dado.temperatura),
        "humidade": valor_observado(ultimo_dado.humidade),
        "velocidade_vento": valor_observado(ultimo_dado.velocidade_vento),
        "precipitacao": valor_observado(ultimo_dado.precipitacao)
    }

    estado = estado_observacao(ultimo_dado)
    if estado != "ok":
        return {
            "id_regiao": id_regiao, "data_hora": data_utc(ultimo_dado.data_hora),
            "dados_meteorologicos": dados, "estado": estado,
            "fwi": None, "ml": None,
        }

    resultado_fwi = calcular_risco_regiao(dados)

    resultado_ml = prever_risco(dados)

    return {
        "id_regiao": id_regiao,
        "data_hora": data_utc(ultimo_dado.data_hora),
        "dados_meteorologicos": dados,
        "estado": estado,
        "fwi": resultado_fwi,
        "ml": resultado_ml
    }
