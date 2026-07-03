from services.scheduler import atualizar_dados_meteorologicos, iniciar_scheduler
import asyncio
import logging
logging.basicConfig(level=logging.INFO)


print("A recolher dados iniciais...")
asyncio.run(atualizar_dados_meteorologicos())
print("Concluido!")
