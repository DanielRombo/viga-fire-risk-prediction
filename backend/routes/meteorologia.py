from fastapi import APIRouter
from services.open_meteo import obter_dados_meteorologicos

router = APIRouter()


@router.get("/meteorologia")
async def get_meteorologia(latitude: float, longitude: float):
    dados = await obter_dados_meteorologicos(latitude, longitude)
    return dados
