from fastapi import FastAPI
from config.database import engine, Base
from models import Regiao, Ocorrencia, DadoMeteorologico

app = FastAPI(title="VIGA API")

Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok", "service": "VIGA"}
