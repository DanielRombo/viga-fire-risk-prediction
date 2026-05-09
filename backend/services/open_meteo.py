import httpx

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
