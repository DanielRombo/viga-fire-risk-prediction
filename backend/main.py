import asyncio
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.database import engine, Base
from routes import meteorologia, incendios, regioes, risco, alertas, ipma, fwi_diario
from routes.auth import router as auth_router
from models import utilizador

# Modo temporário de instalação: também impede DDL e preparação de dados.
_modo_temporario = os.getenv("DISABLE_AUTOMATIC_TASKS", "false").strip().lower()
if _modo_temporario not in ("true", "false"):
    raise ValueError("DISABLE_AUTOMATIC_TASKS deve ser true ou false.")
DISABLE_AUTOMATIC_TASKS = _modo_temporario == "true"

if not DISABLE_AUTOMATIC_TASKS:
    Base.metadata.create_all(bind=engine)

app = FastAPI(title="VIGA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meteorologia.router, prefix="/api")
app.include_router(incendios.router, prefix="/api")
app.include_router(regioes.router, prefix="/api")
app.include_router(risco.router, prefix="/api")
app.include_router(fwi_diario.router, prefix="/api")
app.include_router(alertas.router, prefix="/api")
app.include_router(ipma.router, prefix="/api")
app.include_router(auth_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    if DISABLE_AUTOMATIC_TASKS:
        logging.getLogger(__name__).warning(
            "Modo temporário: preparação da BD e tarefas automáticas desativadas.")
        return
    from services.esquema_ocorrencias import preparar_ocorrencias
    from services.regioes_iniciais import preparar_regioes
    from services.scheduler import iniciar_scheduler, atualizar_dados_meteorologicos
    preparar_ocorrencias(engine)
    preparar_regioes()
    from services.processamento_fwi import preparar_estrutura_fwi
    preparar_estrutura_fwi(engine)
    iniciar_scheduler()
    asyncio.create_task(atualizar_dados_meteorologicos())


@app.get("/")
def root():
    return {"status": "VIGA API online"}
