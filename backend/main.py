import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.database import engine, Base
from routes import meteorologia, incendios, regioes, risco, alertas, ipma

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
app.include_router(alertas.router, prefix="/api")
app.include_router(ipma.router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    from services.scheduler import iniciar_scheduler, atualizar_dados_meteorologicos
    iniciar_scheduler()
    asyncio.create_task(atualizar_dados_meteorologicos())


@app.get("/")
def root():
    return {"status": "VIGA API online"}
