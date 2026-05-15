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
    {"id": 1,    "nome": "Lisboa",
        "latitude": 38.7169, "longitude": -9.1399},
    {"id": 3265, "nome": "Aveiro",
        "latitude": 40.6405, "longitude": -8.6538},
    {"id": 3262, "nome": "Braga",            "latitude": 41.5503, "longitude": -8.42},
    {"id": 3270, "nome": "Castelo Branco",
        "latitude": 39.8194, "longitude": -7.4906},
    {"id": 3263, "nome": "Coimbra",
        "latitude": 40.2033, "longitude": -8.4103},
    {"id": 3269, "nome": "Evora",
        "latitude": 38.5714, "longitude": -7.9101},
    {"id": 3264, "nome": "Faro",
        "latitude": 37.0194, "longitude": -9.3322},
    {"id": 3268, "nome": "Leiria",
        "latitude": 39.7436, "longitude": -8.8071},
    {"id": 3261, "nome": "Porto",
        "latitude": 41.1579, "longitude": -8.6291},
    {"id": 3280, "nome": "Sintra",
        "latitude": 38.8029, "longitude": -9.3817},
    {"id": 3267, "nome": "Viseu",
        "latitude": 40.6566, "longitude": -7.9122},
    {"id": 3283, "nome": "Almada",
        "latitude": 38.6766, "longitude": -9.1572},
    {"id": 3284, "nome": "Amadora",
        "latitude": 38.7539, "longitude": -9.2249},
    {"id": 3272, "nome": "Beja",
        "latitude": 38.015,  "longitude": -7.8653},
    {"id": 3275, "nome": "Braganca",
        "latitude": 41.8061, "longitude": -6.7588},
    {"id": 3281, "nome": "Cascais",
        "latitude": 38.6979, "longitude": -9.4215},
    {"id": 3278, "nome": "Funchal",
        "latitude": 32.6669, "longitude": -16.9241},
    {"id": 3271, "nome": "Guarda",           "latitude": 40.5374, "longitude": -7.265},
    {"id": 3288, "nome": "Guimaraes",
        "latitude": 41.4425, "longitude": -8.2919},
    {"id": 3282, "nome": "Loures",
        "latitude": 38.8314, "longitude": -9.1683},
    {"id": 3286, "nome": "Matosinhos",
        "latitude": 41.1833, "longitude": -8.6833},
    {"id": 3279, "nome": "Ponta Delgada",
        "latitude": 37.7412, "longitude": -25.6756},
    {"id": 3273, "nome": "Portalegre",
        "latitude": 39.2967, "longitude": -7.4286},
    {"id": 3274, "nome": "Santarem",
        "latitude": 39.2369, "longitude": -8.6881},
    {"id": 3266, "nome": "Setubal",
        "latitude": 38.5244, "longitude": -8.8882},
    {"id": 3277, "nome": "Viana do Castelo",
        "latitude": 41.6918, "longitude": -8.8341},
    {"id": 3285, "nome": "Vila Nova de Gaia",
        "latitude": 41.1333, "longitude": -8.6167},
    {"id": 3276, "nome": "Vila Real",
        "latitude": 41.1006, "longitude": -7.7457},
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
