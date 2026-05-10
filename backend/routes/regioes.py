from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from config.database import get_db
from services.openstreetmap import obter_concelhos_portugal, popular_regioes

router = APIRouter()


@router.get("/regioes/concelhos")
async def get_concelhos():
    concelhos = await obter_concelhos_portugal()
    return {"total": len(concelhos), "concelhos": concelhos}


@router.post("/regioes/popular")
async def popular_bd(db: Session = Depends(get_db)):
    resultado = await popular_regioes(db)
    return resultado
