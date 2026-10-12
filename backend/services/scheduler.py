import asyncio
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from config.database import SessionLocal
from services.open_meteo import obter_dados_meteorologicos, data_observacao
from fastapi import HTTPException
from services.nasa_firms import guardar_focos_incendio
from models.dado_meteorologico import DadoMeteorologico
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
    atualizadas, falhas = [], []
    try:
        for regiao in resolver_regioes(db):
            try:
                dados = await obter_dados_meteorologicos(regiao["latitude"], regiao["longitude"])
                data = data_observacao(dados)
            except HTTPException as erro:
                falhas.append({"id_regiao": regiao["id_regiao"], "nome": regiao["nome"],
                               "http_status": erro.status_code, "causa": erro.detail})
                logger.warning("Falha na recolha da região %s: HTTP %s", regiao["nome"], erro.status_code)
                continue
            current = dados["current"]
            db.add(DadoMeteorologico(
                id_regiao=regiao["id_regiao"], data_hora=data.replace(tzinfo=None),
                temperatura=current["temperature_2m"], humidade=current["relative_humidity_2m"],
                velocidade_vento=current["wind_speed_10m"], precipitacao=current["precipitation"],
                fonte="Open-Meteo",
            ))
            atualizadas.append({"id_regiao": regiao["id_regiao"], "nome": regiao["nome"],
                                "data_hora": data.isoformat()})
        if not atualizadas:
            codigo = 504 if falhas and all(f["http_status"] == 504 for f in falhas) else 503
            raise HTTPException(status_code=codigo, detail={
                "status": "falha", "mensagem": "Não foi possível atualizar nenhuma região.",
                "atualizadas": [], "falhas": falhas,
            })
        db.commit()
        resultado = {"status": "parcial" if falhas else "ok",
                     "mensagem": "Atualização parcial: algumas regiões não foram atualizadas." if falhas else "Dados atualizados com sucesso",
                     "atualizadas": atualizadas, "falhas": falhas}
        logger.log(logging.WARNING if falhas else logging.INFO,
                   "Recolha meteorológica: %s regiões atualizadas, %s falhas", len(atualizadas), len(falhas))
        return resultado
    except Exception:
        db.rollback()
        logger.exception("Falha na atualização meteorológica")
        raise
    finally:
        db.close()


async def atualizar_dados_meteorologicos():
    return await _atualizar_dados()


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
    except Exception:
        logger.error("Falha na recolha de focos; transação revertida.")
        raise
    finally:
        db.close()


def iniciar_scheduler():
    if scheduler.running:
        return
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
    from datetime import datetime, timezone
    scheduler.add_job(atualizar_fwi_diario_sync, 'interval', minutes=15,
                      id='fwi_diario', replace_existing=True, max_instances=1,
                      coalesce=True, misfire_grace_time=900,
                      next_run_time=datetime.now(timezone.utc))
    scheduler.start()
    logger.info("Scheduler BackgroundScheduler iniciado!")


def atualizar_fwi_diario_sync():
    from services.processamento_fwi import executar_ciclo_fwi
    resultados = asyncio.run(executar_ciclo_fwi(SessionLocal))
    logger.info('FWI diário: %s', resultados)
    return resultados
