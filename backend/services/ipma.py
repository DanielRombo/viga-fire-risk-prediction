import httpx
import logging
from services.fontes import validar_fonte, numero

logger = logging.getLogger(__name__)

IPMA_URL = "https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/hp-daily-forecast-day0.json"


async def obter_previsao_ipma():
    with validar_fonte("IPMA"):
        async with httpx.AsyncClient(timeout=30) as client:
            resposta = await client.get(IPMA_URL)
            resposta.raise_for_status()
            dados = resposta.json()

            if not isinstance(dados["data"], list):
                raise ValueError("Lista de previsões inválida")
            previsoes = []
            for item in dados["data"]:
                for campo in ("tMin", "tMax", "precipitaProb"):
                    numero(item[campo])
                previsao = {
                    "globalIdLocal": item["globalIdLocal"],
                    "latitude": numero(item["latitude"]),
                    "longitude": numero(item["longitude"]),
                    "tMin": item.get("tMin"),
                    "tMax": item.get("tMax"),
                    "precipitaProb": numero(item["precipitaProb"]),
                    "classWindSpeed": item.get("classWindSpeed"),
                    "predWindDir": item.get("predWindDir"),
                    "idWeatherType": item.get("idWeatherType"),
                }
                previsoes.append(previsao)

            logger.info(f"Previsoes IPMA obtidas: {len(previsoes)}")
            return previsoes
