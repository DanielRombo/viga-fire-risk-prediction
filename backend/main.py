from contextlib import asynccontextmanager
from fastapi import FastAPI
from config.database import engine, Base
from models import Regiao, Ocorrencia, DadoMeteorologico
from routes.meteorologia import router as meteorologia_router
from routes.incendios import router as incendios_router
from routes.regioes import router as regioes_router
from routes.ipma import router as ipma_router
from services.scheduler import iniciar_scheduler


@asynccontextmanager
async def lifespan(app):
    iniciar_scheduler()
    yield


app = FastAPI(title="VIGA API", lifespan=lifespan)

Base.metadata.create_all(bind=engine)

app.include_router(meteorologia_router, prefix="/api")
app.include_router(incendios_router, prefix="/api")
app.include_router(regioes_router, prefix="/api")
app.include_router(ipma_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok", "service": "VIGA"}
