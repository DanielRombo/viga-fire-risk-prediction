from services.http_externo import get_com_retry
import httpx
from datetime import datetime, timezone
from services.disponibilidade import data_utc, MAX_IDADE_DADOS
from models.dado_meteorologico import DadoMeteorologico
from services.fontes import validar_fonte, erro_fonte, numero

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def data_observacao(dados):
    # A consulta pede UTC; datas ISO sem offset nesta resposta são UTC.
    with validar_fonte("Open-Meteo"):
        data = data_utc(datetime.fromisoformat(dados["current"]["time"].replace("Z", "+00:00")))
        agora = datetime.now(timezone.utc)
        if data > agora:
            raise ValueError("Data da observação no futuro")
        if agora - data > MAX_IDADE_DADOS:
            raise erro_fonte("Open-Meteo", "desatualizado", 503)
        return data


async def obter_dados_meteorologicos(latitude: float, longitude: float):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
        "timezone": "UTC"
    }

    with validar_fonte("Open-Meteo"):
        async with httpx.AsyncClient(timeout=httpx.Timeout(20, connect=5)) as client:
            resposta = await get_com_retry(client, OPEN_METEO_URL, params=params)
            resposta.raise_for_status()
            dados = resposta.json()
            current = dados["current"]
            if current is None or current == {}:
                raise erro_fonte("Open-Meteo", "sem_dados", 503)
            for campo in ("temperature_2m", "relative_humidity_2m", "wind_speed_10m", "precipitation"):
                current[campo] = numero(current[campo])
            data_observacao(dados)
            return dados


async def guardar_dados_meteorologicos(latitude: float, longitude: float, id_regiao: int, db):
    dados = await obter_dados_meteorologicos(latitude, longitude)

    current = dados["current"]

    novo_registo = DadoMeteorologico(
        id_regiao=id_regiao,
        data_hora=data_observacao(dados).replace(tzinfo=None),
        temperatura=current["temperature_2m"],
        humidade=current["relative_humidity_2m"],
        velocidade_vento=current["wind_speed_10m"],
        precipitacao=current["precipitation"],
        fonte="Open-Meteo"
    )

    try:
        db.add(novo_registo)
        db.commit()
        db.refresh(novo_registo)
    except Exception:
        db.rollback()
        raise

    return novo_registo
