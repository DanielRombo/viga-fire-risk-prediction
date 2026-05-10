import httpx
import logging

logger = logging.getLogger(__name__)

IPMA_URL = "https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/hp-daily-forecast-day0.json"


async def obter_previsao_ipma():
    async with httpx.AsyncClient(timeout=30) as client:
        resposta = await client.get(IPMA_URL)
        dados = resposta.json()

        previsoes = []
        for item in dados["data"]:
            previsao = {
                "globalIdLocal": item["globalIdLocal"],
                "latitude": float(item["latitude"]),
                "longitude": float(item["longitude"]),
                "tMin": item.get("tMin"),
                "tMax": item.get("tMax"),
                "precipitaProb": float(item.get("precipitaProb", 0)),
                "classWindSpeed": item.get("classWindSpeed"),
                "predWindDir": item.get("predWindDir"),
                "idWeatherType": item.get("idWeatherType"),
            }
            previsoes.append(previsao)

        logger.info(f"Previsoes IPMA obtidas: {len(previsoes)}")
        return previsoes
