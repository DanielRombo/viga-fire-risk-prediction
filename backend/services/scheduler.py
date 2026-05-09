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
    {"id": 1, "nome": "Lisboa", "latitude": 38.72, "longitude": -9.14},
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
