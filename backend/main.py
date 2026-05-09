from fastapi import FastAPI
from config.database import engine, Base
from models import Regiao, Ocorrencia, DadoMeteorologico
from routes.meteorologia import router as meteorologia_router

app = FastAPI(title="VIGA API")

Base.metadata.create_all(bind=engine)
app.include_router(meteorologia_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok", "service": "VIGA"}
