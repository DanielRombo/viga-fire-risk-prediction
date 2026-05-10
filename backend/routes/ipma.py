from fastapi import APIRouter
from services.ipma import obter_previsao_ipma

router = APIRouter()


@router.get("/ipma/previsao")
async def get_previsao_ipma():
    previsoes = await obter_previsao_ipma()
    return {"total": len(previsoes), "previsoes": previsoes}
