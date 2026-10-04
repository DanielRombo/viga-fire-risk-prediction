"""Cliente horário FWI. Não usa nem modifica o fluxo current weather."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import httpx
from services.meteorologia_fwi import numero, utc, DadosFWIInvalidos

URL = 'https://api.open-meteo.com/v1/forecast'
PRODUTO = 'open-meteo-forecast-best-match-horario-v1'
MAX_PASSADO_DIAS = 92
CAMPOS = {'temperature_2m': 'temperatura', 'relative_humidity_2m': 'humidade',
          'wind_speed_10m': 'vento', 'precipitation': 'precipitacao_hora'}
UNIDADES = {'time': 'iso8601', 'temperature_2m': '°C', 'relative_humidity_2m': '%',
            'wind_speed_10m': 'km/h', 'precipitation': 'mm'}


class ErroRecolhaFWI(RuntimeError):
    def __init__(self, codigo, mensagem):
        super().__init__(mensagem)
        self.codigo = codigo


@dataclass(frozen=True)
class HoraRecolhida:
    instante_utc: datetime
    temperatura: float | None
    humidade: float | None
    vento: float | None
    precipitacao_hora: float | None
    latitude_consultada: float
    longitude_consultada: float
    latitude_grelha: float
    longitude_grelha: float
    produto: str
    ingerido_em: datetime
    qualidade: str
    problemas: list


def interpretar_resposta(dados, latitude, longitude, inicio, fim, agora):
    try:
        if dados['utc_offset_seconds'] != 0 or any(dados['hourly_units'].get(k) != v for k,v in UNIDADES.items()):
            raise ValueError('Unidades ou fuso incompatíveis')
        lat = numero(dados['latitude'], 'latitude da grelha', -90, 90)
        lon = numero(dados['longitude'], 'longitude da grelha', -180, 180)
        horas = dados['hourly']
        tempos = horas['time']
        if not isinstance(tempos, list) or any(not isinstance(horas[k], list) or len(horas[k]) != len(tempos) for k in CAMPOS):
            raise ValueError('Séries horárias incompatíveis')
        resultado, vistos = [], set()
        for i, texto in enumerate(tempos):
            t = datetime.fromisoformat(texto.replace('Z', '+00:00'))
            # A resposta foi explicitamente pedida em GMT, confirmado pelo offset.
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            if t.utcoffset() != timedelta(0) or t.minute or t.second or t.microsecond or t in vistos:
                raise ValueError('Timestamp duplicado ou inválido')
            vistos.add(t)
            if not inicio <= t <= fim:
                continue
            valores, problemas = {}, []
            invalido = False
            for externo, interno in CAMPOS.items():
                valor = horas[externo][i]
                if valor is None:
                    valores[interno] = None
                    problemas.append(f'{interno}: ausente')
                    continue
                try:
                    valores[interno] = numero(valor, interno, -273.15 if interno == 'temperatura' else 0,
                                              100 if interno == 'humidade' else None)
                except DadosFWIInvalidos:
                    valores[interno] = None
                    problemas.append(f'{interno}: inválido')
                    invalido = True
            qualidade = 'invalido' if invalido else 'incompleto' if problemas else 'valido'
            resultado.append(HoraRecolhida(t, **valores, latitude_consultada=latitude,
                longitude_consultada=longitude, latitude_grelha=lat, longitude_grelha=lon,
                produto=PRODUTO, ingerido_em=agora, qualidade=qualidade, problemas=problemas))
        if not resultado:
            raise ErroRecolhaFWI('sem_dados', 'A fonte não disponibilizou dados horários para a janela FWI.')
        return sorted(resultado, key=lambda h: h.instante_utc)
    except (KeyError, TypeError, ValueError, AttributeError) as erro:
        raise ErroRecolhaFWI('resposta_invalida', 'A fonte devolveu timestamps, unidades ou estrutura horária inválidos.') from erro


async def recolher_horas_fwi(latitude, longitude, inicio, fim, *, agora=None, cliente=None):
    agora = utc(agora or datetime.now(timezone.utc))
    inicio, fim = utc(inicio), utc(fim)
    latitude = numero(latitude, 'latitude', -90, 90)
    longitude = numero(longitude, 'longitude', -180, 180)
    if inicio > fim or fim >= agora or any(t.minute or t.second or t.microsecond for t in (inicio, fim)):
        raise ErroRecolhaFWI('janela_invalida', 'A janela horária deve estar concluída e alinhada à hora UTC.')
    if inicio.date() < agora.date() - timedelta(days=MAX_PASSADO_DIAS):
        raise ErroRecolhaFWI('historico_necessario', 'A recuperação exige histórico fora da janela recente da Open-Meteo.')
    params = {'latitude': latitude, 'longitude': longitude, 'hourly': ','.join(CAMPOS),
              'temperature_unit': 'celsius', 'wind_speed_unit': 'kmh', 'precipitation_unit': 'mm',
              'timezone': 'GMT', 'timeformat': 'iso8601', 'models': 'best_match',
              'start_hour': inicio.strftime('%Y-%m-%dT%H:%M'), 'end_hour': fim.strftime('%Y-%m-%dT%H:%M')}
    try:
        if cliente is None:
            async with httpx.AsyncClient(timeout=httpx.Timeout(20, connect=5)) as sessao:
                resposta = await sessao.get(URL, params=params)
        else:
            resposta = await cliente.get(URL, params=params)
        resposta.raise_for_status()
        dados = resposta.json()
    except httpx.TimeoutException as erro:
        raise ErroRecolhaFWI('timeout', 'A fonte meteorológica excedeu o tempo de resposta.') from erro
    except (httpx.RequestError, httpx.HTTPStatusError) as erro:
        raise ErroRecolhaFWI('erro_fonte', 'Não foi possível recolher a meteorologia horária FWI.') from erro
    except ValueError as erro:
        raise ErroRecolhaFWI('resposta_invalida', 'A fonte devolveu uma resposta horária inválida.') from erro
    return interpretar_resposta(dados, latitude, longitude, inicio, fim, agora)
