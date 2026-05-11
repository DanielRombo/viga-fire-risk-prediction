from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from config.database import get_db
from models.dado_meteorologico import DadoMeteorologico
from models.regiao import Regiao
from services.fwi import calcular_fwi
from datetime import datetime

router = APIRouter()


def gerar_alertas(dados, regiao_nome):
    alertas = []
    agora = datetime.utcnow()

    if dados.velocidade_vento and dados.velocidade_vento > 30:
        alertas.append({
            "id": f"vento_{regiao_nome}",
            "texto": f"Vento forte — {regiao_nome}",
            "meta": f"{agora.strftime('%H:%M')} · Severidade alta",
            "cor": "#E24B4A",
            "severidade": "alta"
        })

    if dados.humidade and dados.humidade < 25:
        alertas.append({
            "id": f"humidade_{regiao_nome}",
            "texto": f"Humidade crítica — {regiao_nome}",
            "meta": f"{agora.strftime('%H:%M')} · Severidade alta",
            "cor": "#E24B4A",
            "severidade": "alta"
        })

    if dados.temperatura and dados.temperatura > 35:
        alertas.append({
            "id": f"temp_{regiao_nome}",
            "texto": f"Temperatura extrema — {regiao_nome}",
            "meta": f"{agora.strftime('%H:%M')} · Severidade média",
            "cor": "#BA7517",
            "severidade": "media"
        })

    fwi = calcular_fwi(
        dados.temperatura or 20,
        dados.humidade or 50,
        dados.velocidade_vento or 0,
        dados.precipitacao or 0
    )

    if fwi["fwi"] > 20:
        alertas.append({
            "id": f"fwi_{regiao_nome}",
            "texto": f"Risco FWI elevado — {regiao_nome}",
            "meta": f"{agora.strftime('%H:%M')} · FWI {fwi['fwi']}",
            "cor": "#BA7517",
            "severidade": "media"
        })

    return alertas


@router.get("/alertas")
def get_alertas(db: Session = Depends(get_db)):
    resultados = db.query(DadoMeteorologico, Regiao)\
        .join(Regiao, DadoMeteorologico.id_regiao == Regiao.id_regiao)\
        .order_by(DadoMeteorologico.data_hora.desc())\
        .limit(10)\
        .all()

    todos_alertas = []
    regioes_vistas = set()

    for dado, regiao in resultados:
        if regiao.id_regiao not in regioes_vistas:
            regioes_vistas.add(regiao.id_regiao)
            alertas = gerar_alertas(dado, regiao.nome)
            todos_alertas.extend(alertas)

    if not todos_alertas:
        todos_alertas.append({
            "id": "ok_nacional",
            "texto": "Condições normais em todo o território",
            "meta": f"{datetime.utcnow().strftime('%H:%M')} · Informativo",
            "cor": "#639922",
            "severidade": "info"
        })

    return {"total": len(todos_alertas), "alertas": todos_alertas}
