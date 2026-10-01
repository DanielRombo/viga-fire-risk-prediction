import asyncio
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from config.database import SessionLocal
from services.open_meteo import obter_dados_meteorologicos
from services.nasa_firms import guardar_focos_incendio
from models.dado_meteorologico import DadoMeteorologico
from datetime import datetime
from services.regioes_iniciais import REGIOES_RECOLHA, resolver_regioes

logger = logging.getLogger(__name__)


scheduler = BackgroundScheduler()


def atualizar_dados_meteorologicos_sync():
    logger.info(f"Scheduler: A recolher dados para {len(REGIOES_RECOLHA)} regiões...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_atualizar_dados())
    finally:
        loop.close()


async def _atualizar_dados():
    db = SessionLocal()
    try:
        for regiao in resolver_regioes(db):
            try:
                dados = await obter_dados_meteorologicos(regiao["latitude"], regiao["longitude"])
                current = dados.get("current", {})
                if current:
                    dado = DadoMeteorologico(
                        id_regiao=regiao["id_regiao"],
                        data_hora=datetime.utcnow(),
                        temperatura=current.get("temperature_2m"),
                        humidade=current.get("relative_humidity_2m"),
                        velocidade_vento=current.get("wind_speed_10m"),
                        precipitacao=current.get("precipitation", 0),
                    )
                    db.add(dado)
                    logger.info(
                        f"  ✓ {regiao['nome']}: {current.get('temperature_2m')}°C")
            except Exception as e:
                logger.error(f"  ✗ Erro em {regiao['nome']}: {e}")
        db.commit()
        logger.info("Dados meteorológicos guardados!")
    except Exception as e:
        db.rollback()
        logger.error(f"Erro: {e}")
    finally:
        db.close()


async def atualizar_dados_meteorologicos():
    await _atualizar_dados()


def atualizar_focos_sync():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_atualizar_focos())
    finally:
        loop.close()


async def _atualizar_focos():
    db = SessionLocal()
    try:
        resultado = await guardar_focos_incendio(db)
        logger.info(f"  ✓ {resultado['focos_guardados']} focos guardados")
    except Exception as e:
        logger.error(f"Erro focos: {e}")
    finally:
        db.close()


def iniciar_scheduler():
    scheduler.add_job(
        atualizar_dados_meteorologicos_sync,
        'interval',
        hours=1,
        id="meteorologia",
        replace_existing=True
    )
    scheduler.add_job(
        atualizar_focos_sync,
        'interval',
        hours=6,
        id="focos",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler BackgroundScheduler iniciado!")
