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


@router.get("/regioes/{id_regiao}/detalhes")
async def get_detalhes_regiao(id_regiao: int, db: Session = Depends(get_db)):
    from models.regiao import Regiao
    from models.dado_meteorologico import DadoMeteorologico
    from services.fwi import calcular_fwi
    from services.open_meteo import obter_dados_meteorologicos

    regiao = db.query(Regiao).filter(Regiao.id_regiao == id_regiao).first()
    if not regiao:
        return {"erro": "Região não encontrada"}

    historico = db.query(DadoMeteorologico)\
        .filter(DadoMeteorologico.id_regiao == id_regiao)\
        .order_by(DadoMeteorologico.data_hora.desc())\
        .limit(30)\
        .all()

    dados_fwi = []
    for d in historico:
        if d.temperatura and d.humidade:
            fwi = calcular_fwi(
                d.temperatura, d.humidade,
                d.velocidade_vento or 0, d.precipitacao or 0
            )
            dados_fwi.append({
                "data_hora": d.data_hora.isoformat(),
                "temperatura": d.temperatura,
                "humidade": d.humidade,
                "velocidade_vento": d.velocidade_vento,
                "precipitacao": d.precipitacao,
                "fwi": fwi["fwi"],
                "nivel_risco": fwi["nivel_risco"]
            })

    # Se nao há histórico, vai buscar dados em tempo real à Open-Meteo
    if not dados_fwi and regiao.latitude and regiao.longitude:
        try:
            dados_rt = await obter_dados_meteorologicos(regiao.latitude, regiao.longitude)
            current = dados_rt.get("current", {})
            if current:
                from datetime import datetime
                fwi = calcular_fwi(
                    current.get("temperature_2m", 20),
                    current.get("relative_humidity_2m", 50),
                    current.get("wind_speed_10m", 0),
                    current.get("precipitation", 0)
                )
                dados_fwi.append({
                    "data_hora": datetime.utcnow().isoformat(),
                    "temperatura": current.get("temperature_2m"),
                    "humidade": current.get("relative_humidity_2m"),
                    "velocidade_vento": current.get("wind_speed_10m"),
                    "precipitacao": current.get("precipitation"),
                    "fwi": fwi["fwi"],
                    "nivel_risco": fwi["nivel_risco"],
                    "fonte": "Open-Meteo (tempo real)"
                })
        except Exception as e:
            pass

    ultimo = dados_fwi[0] if dados_fwi else None
    tendencia = None
    if len(dados_fwi) >= 2:
        if dados_fwi[0]["fwi"] > dados_fwi[1]["fwi"]:
            tendencia = "a aumentar"
        elif dados_fwi[0]["fwi"] < dados_fwi[1]["fwi"]:
            tendencia = "a diminuir"
        else:
            tendencia = "estável"

    return {
        "regiao": {
            "id_regiao": regiao.id_regiao,
            "nome": regiao.nome,
            "distrito": regiao.distrito,
            "latitude": regiao.latitude,
            "longitude": regiao.longitude
        },
        "atual": ultimo,
        "tendencia": tendencia,
        "historico": dados_fwi
    }
