from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from config.database import get_db
from services.nasa_firms import obter_focos_incendio, guardar_focos_incendio

router = APIRouter()


@router.get("/incendios/focos")
async def get_focos_incendio(dias: int = 1):
    focos = await obter_focos_incendio(dias)
    return {"total": len(focos), "focos": focos}


@router.post("/incendios/guardar")
async def guardar_focos(id_regiao: int = 1, db: Session = Depends(get_db)):
    resultado = await guardar_focos_incendio(db, id_regiao)
    return resultado
