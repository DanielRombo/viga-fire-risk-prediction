"""Archive API, produto IFS explícito; sem fallback para outros produtos."""
from dataclasses import replace
from datetime import date, datetime, timezone
import httpx
from services.meteorologia_fwi import numero, utc
from services.open_meteo_fwi import CAMPOS, ErroRecolhaFWI, interpretar_resposta

URL = 'https://archive-api.open-meteo.com/v1/archive'
MODELO = 'ecmwf_ifs'
PRODUTO = 'open-meteo-archive-ecmwf-ifs-horario-v1'


async def recolher_historico_fwi(latitude, longitude, inicio, fim, *, agora=None, cliente=None):
    agora = utc(agora or datetime.now(timezone.utc))
    inicio, fim = utc(inicio), utc(fim)
    latitude = numero(latitude, 'latitude', -90, 90)
    longitude = numero(longitude, 'longitude', -180, 180)
    if (inicio > fim or fim >= agora or
            any(t.minute or t.second or t.microsecond for t in (inicio, fim))):
        raise ErroRecolhaFWI('janela_invalida', 'A janela histórica deve estar concluída e alinhada à hora UTC.')
    if inicio.date() < date(2017, 1, 1):
        raise ErroRecolhaFWI('historico_indisponivel', 'O produto histórico IFS selecionado não cobre datas anteriores a 2017.')
    params = {'latitude': latitude, 'longitude': longitude, 'hourly': ','.join(CAMPOS),
              'temperature_unit': 'celsius', 'wind_speed_unit': 'kmh', 'precipitation_unit': 'mm',
              'timezone': 'GMT', 'timeformat': 'iso8601', 'models': MODELO,
              'start_date': inicio.date().isoformat(), 'end_date': fim.date().isoformat()}
    try:
        if cliente is None:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=5)) as sessao:
                resposta = await sessao.get(URL, params=params)
        else:
            resposta = await cliente.get(URL, params=params)
        resposta.raise_for_status()
        dados = resposta.json()
    except httpx.TimeoutException as erro:
        raise ErroRecolhaFWI('timeout', 'A fonte histórica excedeu o tempo de resposta.') from erro
    except (httpx.RequestError, httpx.HTTPStatusError) as erro:
        raise ErroRecolhaFWI('erro_fonte', 'Não foi possível recolher a meteorologia histórica FWI.') from erro
    except ValueError as erro:
        raise ErroRecolhaFWI('resposta_invalida', 'A fonte devolveu uma resposta histórica inválida.') from erro
    return [replace(h, produto=PRODUTO) for h in
            interpretar_resposta(dados, latitude, longitude, inicio, fim, agora)]
