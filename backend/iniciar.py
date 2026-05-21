from services.scheduler import atualizar_dados_meteorologicos
import asyncio
import logging
logging.basicConfig(level=logging.INFO)


asyncio.run(atualizar_dados_meteorologicos())
