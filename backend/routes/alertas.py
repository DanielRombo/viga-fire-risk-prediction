from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from config.database import get_db
from models.dado_meteorologico import DadoMeteorologico
from models.regiao import Regiao
from services.fwi import calcular_fwi
from sqlalchemy import select, func, and_
from services.disponibilidade import estado_observacao, MAX_IDADE_DADOS, data_utc

router = APIRouter()


def gerar_alertas(dados, regiao_nome):
    alertas = []
    agora = data_utc(dados.data_hora)

    if dados.velocidade_vento is not None and dados.velocidade_vento > 30:
        alertas.append({
            "id": f"vento_{regiao_nome}",
            "texto": f"Vento forte — {regiao_nome}",
            "meta": f"{agora.strftime('%H:%M')} · Severidade alta",
            "cor": "#E24B4A",
            "severidade": "alta"
        })

    if dados.humidade is not None and dados.humidade < 25:
        alertas.append({
            "id": f"humidade_{regiao_nome}",
            "texto": f"Humidade crítica — {regiao_nome}",
            "meta": f"{agora.strftime('%H:%M')} · Severidade alta",
            "cor": "#E24B4A",
            "severidade": "alta"
        })

    if dados.temperatura is not None and dados.temperatura > 35:
        alertas.append({
            "id": f"temp_{regiao_nome}",
            "texto": f"Temperatura extrema — {regiao_nome}",
            "meta": f"{agora.strftime('%H:%M')} · Severidade média",
            "cor": "#BA7517",
            "severidade": "media"
        })

    fwi = calcular_fwi(
        dados.temperatura,
        dados.humidade,
        dados.velocidade_vento,
        dados.precipitacao
    )

    if fwi["fwi"] is not None and fwi["fwi"] > 20:
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
    ultimos = select(
        DadoMeteorologico.id_dado, DadoMeteorologico.id_regiao,
        func.row_number().over(
            partition_by=DadoMeteorologico.id_regiao,
            order_by=(DadoMeteorologico.data_hora.desc(), DadoMeteorologico.id_dado.desc()),
        ).label("ordem"),
    ).subquery()
    resultados = db.query(Regiao.id_regiao, Regiao.nome, DadoMeteorologico).outerjoin(
        ultimos, and_(ultimos.c.id_regiao == Regiao.id_regiao, ultimos.c.ordem == 1)
    ).outerjoin(
        DadoMeteorologico, DadoMeteorologico.id_dado == ultimos.c.id_dado
    ).all()

    todos_alertas = []
    contagens = {"ok": 0, "sem_dados": 0, "dados_incompletos": 0, "desatualizado": 0}
    for _id_regiao, nome, dado in resultados:
        estado = estado_observacao(dado)
        contagens[estado] += 1
        if estado == "ok":
            todos_alertas.extend(gerar_alertas(dado, nome))

    total_regioes = len(resultados)
    if not total_regioes or contagens["sem_dados"] == total_regioes:
        estado = "sem_dados"
    elif contagens["ok"] == total_regioes:
        estado = "ok"
    elif contagens["desatualizado"] == total_regioes:
        estado = "desatualizado"
    elif contagens["dados_incompletos"] == total_regioes:
        estado = "dados_incompletos"
    else:
        estado = "cobertura_parcial"
    mensagens = {
        "sem_dados": "Sem dados meteorológicos para avaliar alertas.",
        "dados_incompletos": "Dados meteorológicos incompletos; não é possível avaliar alertas.",
        "desatualizado": "Dados meteorológicos desatualizados; alertas atuais indisponíveis.",
        "cobertura_parcial": "Cobertura parcial: alertas apenas das regiões com dados completos e recentes.",
        "ok": "Alertas avaliados nas regiões registadas." if todos_alertas else "Sem alertas nas regiões avaliadas.",
    }
    return {
        "total": len(todos_alertas), "alertas": todos_alertas,
        "estado": estado, "mensagem": mensagens[estado],
        "cobertura": {"regioes_registadas": total_regioes, "regioes_avaliadas": contagens["ok"],
                      "sem_dados": contagens["sem_dados"], "dados_incompletos": contagens["dados_incompletos"],
                      "desatualizadas": contagens["desatualizado"],
                      "max_idade_horas": MAX_IDADE_DADOS.total_seconds() / 3600},
    }
