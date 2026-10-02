"""Preparação diária, sem rede: valores à referência e chuva das 24 h anteriores."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from math import fsum, isfinite
from numbers import Real


class DadosFWIInvalidos(ValueError):
    """Dados ausentes, incompatíveis ou insuficientes para o cálculo diário."""


class TerritorioFWI(str, Enum):
    CONTINENTE = 'continente'
    MADEIRA = 'madeira'
    ACORES = 'acores'


@dataclass(frozen=True)
class UnidadesFWI:
    temperatura: str
    humidade: str
    vento: str
    precipitacao: str
    latitude: str
    altura_vento_m: int


UNIDADES_FWI = UnidadesFWI('degC', '%', 'km/h', 'mm', 'degrees_north', 10)


def numero(valor, campo, minimo=None, maximo=None):
    if isinstance(valor, bool) or not isinstance(valor, Real) or not isfinite(valor):
        raise DadosFWIInvalidos(f'{campo}: valor ausente ou não finito.')
    if (minimo is not None and valor < minimo) or (maximo is not None and valor > maximo):
        raise DadosFWIInvalidos(f'{campo}: valor fora dos limites permitidos.')
    return float(valor)


def utc(instante):
    if not isinstance(instante, datetime) or instante.utcoffset() is None:
        raise DadosFWIInvalidos('O instante deve incluir um fuso horário explícito.')
    return instante.astimezone(timezone.utc)


def instante_referencia(data, territorio):
    if type(data) is not date or not isinstance(territorio, TerritorioFWI):
        raise DadosFWIInvalidos('Data de referência ou território inválido.')
    hora = 13 if territorio == TerritorioFWI.ACORES else 12
    return datetime.combine(data, time(hora), tzinfo=timezone.utc)


@dataclass(frozen=True)
class ObservacaoDiariaFWI:
    id_regiao: int
    data_referencia: date
    instante_referencia_utc: datetime
    territorio: TerritorioFWI
    temperatura: float
    humidade: float
    vento: float
    precipitacao_24h: float
    latitude: float
    origem: str
    unidades: UnidadesFWI

    def __post_init__(self):
        if type(self.id_regiao) is not int or self.id_regiao <= 0:
            raise DadosFWIInvalidos('Região inválida.')
        referencia = instante_referencia(self.data_referencia, self.territorio)
        if utc(self.instante_referencia_utc) != referencia:
            raise DadosFWIInvalidos('O instante não corresponde à referência diária em hora padrão.')
        object.__setattr__(self, 'instante_referencia_utc', referencia)
        if self.unidades != UNIDADES_FWI:
            raise DadosFWIInvalidos('Unidades incompatíveis: são necessários °C, %, km/h a 10 m, mm e graus de latitude.')
        for campo, baixo, alto in [('temperatura', -273.15, None), ('humidade', 0, 100),
                                  ('vento', 0, None), ('precipitacao_24h', 0, None), ('latitude', -90, 90)]:
            object.__setattr__(self, campo, numero(getattr(self, campo), campo, baixo, alto))
        if not isinstance(self.origem, str) or not self.origem.strip():
            raise DadosFWIInvalidos('A origem dos dados é obrigatória.')


@dataclass(frozen=True)
class AmostraHorariaFWI:
    instante: datetime
    precipitacao_hora: float
    temperatura: float | None = None
    humidade: float | None = None
    vento: float | None = None


def preparar_observacao_diaria(*, id_regiao, data_referencia, territorio, latitude,
                               amostras, unidades, origem):
    """A precipitação representa a hora TERMINADA no instante da amostra.

    Para t, exige t-23h, ..., t: os 24 intervalos (t-24h, t].
    Não utiliza precipitação current nem um dia civil de 23/25 horas.
    """
    referencia = instante_referencia(data_referencia, territorio)
    esperados = {referencia - timedelta(hours=h) for h in range(24)}
    selecionados = {}
    for amostra in amostras:
        instante = utc(amostra.instante)
        if referencia - timedelta(hours=24) < instante <= referencia:
            if instante not in esperados or instante in selecionados:
                raise DadosFWIInvalidos('A série horária contém instantes duplicados ou desalinhados.')
            selecionados[instante] = amostra
    if set(selecionados) != esperados:
        raise DadosFWIInvalidos('São necessárias 24 observações horárias consecutivas de precipitação.')
    chuva = fsum(numero(a.precipitacao_hora, 'precipitação horária', 0) for a in selecionados.values())
    atual = selecionados[referencia]
    return ObservacaoDiariaFWI(id_regiao, data_referencia, referencia, territorio,
                              atual.temperatura, atual.humidade, atual.vento, chuva,
                              latitude, origem, unidades)
