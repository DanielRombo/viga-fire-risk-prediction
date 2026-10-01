from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from config.database import get_db
from routes.auth import get_administrador_atual
from services.nasa_firms import obter_focos_incendio, guardar_focos_incendio

router = APIRouter()


@router.get("/incendios/focos")
async def get_focos_incendio(dias: int = 1):
    focos = await obter_focos_incendio(dias)
    return {"total": len(focos), "focos": focos}


@router.post("/incendios/guardar", dependencies=[Depends(get_administrador_atual)])
async def guardar_focos(id_regiao: int | None = None, db: Session = Depends(get_db)):
    if id_regiao is not None:
        raise HTTPException(status_code=422, detail="A região é determinada pelas coordenadas do foco; não indique id_regiao.")
    resultado = await guardar_focos_incendio(db)
    return resultado
