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


@router.get("/regioes/pesquisa")
@router.get("/regioes/pesquisa")
def pesquisar_regioes(q: str, db: Session = Depends(get_db)):
    from models.regiao import Regiao
    from sqlalchemy import case

    resultados = db.query(Regiao)\
        .filter(Regiao.nome.ilike(f"%{q}%"))\
        .order_by(
            case(
                (Regiao.nome.ilike(q), 0),
                (Regiao.nome.ilike(f"{q}%"), 1),
                else_=2
            ),
            Regiao.nome
    )\
        .limit(10)\
        .all()

    return {
        "resultados": [
            {
                "id_regiao": r.id_regiao,
                "nome": r.nome,
                "distrito": r.distrito,
                "latitude": r.latitude,
                "longitude": r.longitude
            }
            for r in resultados
        ]
    }


@router.get("/regioes/distritos")
def get_distritos(db: Session = Depends(get_db)):
    from models.regiao import Regiao
    from sqlalchemy import distinct
    distritos = db.query(distinct(Regiao.distrito))\
        .filter(Regiao.distrito != None)\
        .filter(Regiao.distrito != 'Desconhecido')\
        .order_by(Regiao.distrito)\
        .all()
    return {"distritos": [d[0] for d in distritos]}
