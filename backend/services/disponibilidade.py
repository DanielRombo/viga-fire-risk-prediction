from datetime import datetime, timedelta, timezone
from math import isfinite

# Duas janelas da recolha horária; mede a idade do timestamp armazenado.
MAX_IDADE_DADOS = timedelta(hours=2)
CAMPOS_METEO = ("temperatura", "humidade", "velocidade_vento", "precipitacao")


def valor_observado(valor):
    return valor if isinstance(valor, (float, int)) and not isinstance(valor, bool) and isfinite(valor) else None


def estado_observacao(dado, agora=None):
    if dado is None:
        return "sem_dados"
    valores = [getattr(dado, campo, None) for campo in CAMPOS_METEO]
    if any(valor_observado(v) is None for v in valores):
        return "dados_incompletos"
    data = dado.data_hora
    if not isinstance(data, datetime):
        return "dados_incompletos"
    data = data.replace(tzinfo=timezone.utc) if data.tzinfo is None else data
    agora = agora or datetime.now(timezone.utc)
    if data > agora:
        return "dados_incompletos"
    return "desatualizado" if agora - data > MAX_IDADE_DADOS else "ok"
