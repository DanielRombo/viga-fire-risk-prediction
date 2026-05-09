import httpx
from datetime import datetime
from models.dado_meteorologico import DadoMeteorologico

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


async def obter_dados_meteorologicos(latitude: float, longitude: float):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
        "timezone": "Europe/Lisbon"
    }

    async with httpx.AsyncClient() as client:
        resposta = await client.get(OPEN_METEO_URL, params=params)
        dados = resposta.json()
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
