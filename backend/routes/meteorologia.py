from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from config.database import get_db
from services.open_meteo import obter_dados_meteorologicos, guardar_dados_meteorologicos

router = APIRouter()


@router.get("/meteorologia")
async def get_meteorologia(latitude: float, longitude: float):
    dados = await obter_dados_meteorologicos(latitude, longitude)
    return dados


@router.post("/meteorologia/guardar")
async def guardar_meteorologia(latitude: float, longitude: float, id_regiao: int, db: Session = Depends(get_db)):
    registo = await guardar_dados_meteorologicos(latitude, longitude, id_regiao, db)
    return {"mensagem": "Dados guardados com sucesso!", "id": registo.id_dado}
