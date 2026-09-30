import httpx
from datetime import datetime
from models.dado_meteorologico import DadoMeteorologico
from services.fontes import validar_fonte, erro_fonte, numero

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


async def obter_dados_meteorologicos(latitude: float, longitude: float):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
        "timezone": "Europe/Lisbon"
    }

    with validar_fonte("Open-Meteo"):
        async with httpx.AsyncClient() as client:
            resposta = await client.get(OPEN_METEO_URL, params=params)
            resposta.raise_for_status()
            dados = resposta.json()
            current = dados["current"]
            if current is None or current == {}:
                raise erro_fonte("Open-Meteo", "sem_dados", 503)
            for campo in ("temperature_2m", "relative_humidity_2m", "wind_speed_10m", "precipitation"):
                current[campo] = numero(current[campo])
            return dados


async def guardar_dados_meteorologicos(latitude: float, longitude: float, id_regiao: int, db):
    dados = await obter_dados_meteorologicos(latitude, longitude)

    current = dados["current"]

    novo_registo = DadoMeteorologico(
        id_regiao=id_regiao,
        data_hora=datetime.utcnow(),
        temperatura=current["temperature_2m"],
        humidade=current["relative_humidity_2m"],
        velocidade_vento=current["wind_speed_10m"],
        precipitacao=current["precipitation"],
        fonte="Open-Meteo"
    )

    db.add(novo_registo)
    db.commit()
    db.refresh(novo_registo)

    return novo_registo
