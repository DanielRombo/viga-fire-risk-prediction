import os
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from config.database import SessionLocal
from services.open_meteo import guardar_dados_meteorologicos
from services.nasa_firms import guardar_focos_incendio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REGIOES = [
    {"id": 1,    "nome": "Lisboa",         "latitude": 38.7169, "longitude": -9.1399},
    {"id": 3265, "nome": "Aveiro",         "latitude": 40.6405, "longitude": -8.6538},
    {"id": 3262, "nome": "Braga",          "latitude": 41.5503, "longitude": -8.42},
    {"id": 3270, "nome": "Castelo Branco",
        "latitude": 39.8194, "longitude": -7.4906},
    {"id": 3263, "nome": "Coimbra",        "latitude": 40.2033, "longitude": -8.4103},
    {"id": 3269, "nome": "Evora",          "latitude": 38.5714, "longitude": -7.9101},
    {"id": 3264, "nome": "Faro",           "latitude": 37.0194, "longitude": -9.3322},
    {"id": 3268, "nome": "Leiria",         "latitude": 39.7436, "longitude": -8.8071},
    {"id": 3261, "nome": "Porto",          "latitude": 41.1579, "longitude": -8.6291},
    {"id": 3280, "nome": "Sintra",         "latitude": 38.8029, "longitude": -9.3817},
    {"id": 3267, "nome": "Viseu",          "latitude": 40.6566, "longitude": -7.9122},
]

scheduler = AsyncIOScheduler()


async def tarefa_meteorologia():
    db = SessionLocal()
    try:
        for regiao in REGIOES:
            await guardar_dados_meteorologicos(
                regiao["latitude"],
                regiao["longitude"],
                regiao["id"],
                db
            )
            logger.info(f"Meteorologia atualizada: {regiao['nome']}")
    finally:
        db.close()


async def tarefa_incendios():
    db = SessionLocal()
    try:
        resultado = await guardar_focos_incendio(db)
        logger.info(f"Focos atualizados: {resultado}")
    finally:
        db.close()


def iniciar_scheduler():
    scheduler.add_job(
        tarefa_meteorologia,
        trigger=IntervalTrigger(hours=1),
        id="meteorologia",
        name="Atualizar dados meteorologicos",
        replace_existing=True
    )
    scheduler.add_job(
        tarefa_incendios,
        trigger=IntervalTrigger(hours=6),
        id="incendios",
        name="Atualizar focos de incendio",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler iniciado!")
