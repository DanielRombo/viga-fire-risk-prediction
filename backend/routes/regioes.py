from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from config.database import get_db
from routes.auth import get_administrador_atual
from services.disponibilidade import estado_observacao, valor_observado, data_utc
from services.openstreetmap import obter_concelhos_portugal, popular_regioes

router = APIRouter()


@router.get("/regioes/monitorizadas")
def get_regioes_monitorizadas(db: Session = Depends(get_db)):
    from services.regioes_iniciais import resolver_regioes
    return {"regioes": resolver_regioes(db)}


@router.get("/regioes/concelhos")
async def get_concelhos():
    concelhos = await obter_concelhos_portugal()
    return {"total": len(concelhos), "concelhos": concelhos}


@router.post("/regioes/popular", dependencies=[Depends(get_administrador_atual)])
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
    from services.open_meteo import obter_dados_meteorologicos, data_observacao

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
        estado = estado_observacao(d)
        fwi = calcular_fwi(d.temperatura, d.humidade, d.velocidade_vento, d.precipitacao) if estado in ("ok", "desatualizado") else None
        dados_fwi.append({
            "data_hora": data_utc(d.data_hora).isoformat() if d.data_hora else None,
            "temperatura": valor_observado(d.temperatura), "humidade": valor_observado(d.humidade),
            "velocidade_vento": valor_observado(d.velocidade_vento), "precipitacao": valor_observado(d.precipitacao),
            "fwi": fwi["fwi"] if fwi else None,
            "nivel_risco": fwi["nivel_risco"] if fwi else None,
            "estado": estado,
        })

    # Só consultar a fonte se não há histórico; falhas externas propagam-se.
    if not historico and regiao.latitude is not None and regiao.longitude is not None:
        dados_rt = await obter_dados_meteorologicos(regiao.latitude, regiao.longitude)
        current = dados_rt["current"]
        fwi = calcular_fwi(current["temperature_2m"], current["relative_humidity_2m"],
                           current["wind_speed_10m"], current["precipitation"])
        dados_fwi.append({
            "data_hora": data_observacao(dados_rt).isoformat(),
            "temperatura": current["temperature_2m"], "humidade": current["relative_humidity_2m"],
            "velocidade_vento": current["wind_speed_10m"], "precipitacao": current["precipitation"],
            "fwi": fwi["fwi"], "nivel_risco": fwi["nivel_risco"],
            "fonte": "Open-Meteo (tempo real)", "estado": "ok",
        })

    ultimo = dict(dados_fwi[0]) if dados_fwi else None
    if ultimo and ultimo["estado"] != "ok":
        ultimo.update(fwi=None, nivel_risco=None)
    tendencia = None
    if len(dados_fwi) >= 2 and ultimo["estado"] == "ok" and all(d["fwi"] is not None for d in dados_fwi[:2]):
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
        "estado": ultimo["estado"] if ultimo else "sem_dados",
        "tendencia": tendencia,
        "historico": dados_fwi
    }
