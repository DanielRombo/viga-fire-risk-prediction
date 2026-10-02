"""FWI clássico xclim 0.62.0, validado contra cffdrs 1.8.17.

Não é equivalente à variante cffdrs 1.9.2. Não altera constantes científicas.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from services.meteorologia_fwi import DadosFWIInvalidos, ObservacaoDiariaFWI, numero, utc

VERSAO_FWI = 'xclim-0.62.0-cffdrs-1.8.17-classico-v1'


class QualidadeEstado(str, Enum):
    ESTABELECIDO = 'estabelecido'
    RECONSTRUCAO_HISTORICA = 'reconstrucao_historica'
    CONVENCIONAL = 'inicializacao_convencional'
    EM_INICIALIZACAO = 'em_inicializacao'


@dataclass(frozen=True)
class EstadoFWI:
    id_regiao: int
    data_referencia: date
    ffmc: float
    dmc: float
    dc: float
    qualidade: QualidadeEstado
    origem: str
    versao: str = VERSAO_FWI
    id_fwi: int | None = None

    def __post_init__(self):
        if type(self.id_regiao) is not int or self.id_regiao <= 0 or type(self.data_referencia) is not date:
            raise DadosFWIInvalidos('Região ou data do estado anterior inválida.')
        if not isinstance(self.qualidade, QualidadeEstado) or not isinstance(self.origem, str) or not self.origem.strip():
            raise DadosFWIInvalidos('A qualidade e a origem do estado são obrigatórias.')
        if self.versao != VERSAO_FWI:
            raise DadosFWIInvalidos('Versão do estado anterior incompatível.')
        if self.id_fwi is not None and (type(self.id_fwi) is not int or self.id_fwi <= 0):
            raise DadosFWIInvalidos('Referência persistente ao estado anterior inválida.')
        for campo in ('ffmc', 'dmc', 'dc'):
            object.__setattr__(self, campo, numero(getattr(self, campo), campo, 0, 101 if campo == 'ffmc' else None))


@dataclass(frozen=True)
class ResultadoFWI:
    observacao: ObservacaoDiariaFWI
    anterior: EstadoFWI
    ffmc: float
    dmc: float
    dc: float
    isi: float
    bui: float
    fwi: float
    calculado_em: datetime
    versao: str = VERSAO_FWI

    def __post_init__(self):
        validar_sequencia(self.observacao, self.anterior)
        if self.versao != VERSAO_FWI:
            raise DadosFWIInvalidos('Versão do resultado FWI incompatível.')
        object.__setattr__(self, 'calculado_em', utc(self.calculado_em))
        for campo in ('ffmc', 'dmc', 'dc', 'isi', 'bui', 'fwi'):
            object.__setattr__(self, campo, numero(getattr(self, campo), campo, 0, 101 if campo == 'ffmc' else None))

    @property
    def estado(self):
        return 'valido' if self.anterior.qualidade == QualidadeEstado.ESTABELECIDO else 'em_inicializacao'

    def proximo_estado(self, id_fwi=None):
        # Nunca promover automaticamente uma sequência inicial para estabelecida.
        return EstadoFWI(self.observacao.id_regiao, self.observacao.data_referencia,
                         self.ffmc, self.dmc, self.dc, self.anterior.qualidade,
                         self.anterior.origem, self.versao, id_fwi)


def validar_sequencia(observacao, anterior):
    if not isinstance(observacao, ObservacaoDiariaFWI) or not isinstance(anterior, EstadoFWI):
        raise DadosFWIInvalidos('Observação diária e estado anterior explícito são obrigatórios.')
    if anterior.id_regiao != observacao.id_regiao:
        raise DadosFWIInvalidos('O estado anterior pertence a outra região.')
    if anterior.data_referencia != observacao.data_referencia - timedelta(days=1):
        raise DadosFWIInvalidos('O estado anterior deve corresponder ao dia imediatamente anterior.')


def calcular_fwi_diario(observacao: ObservacaoDiariaFWI, anterior: EstadoFWI) -> ResultadoFWI:
    validar_sequencia(observacao, anterior)
    import xclim
    import xarray as xr
    import numpy as np
    from xclim.indices.fire import cffwis_indices
    if xclim.__version__ != '0.62.0':
        raise RuntimeError('A implementação FWI requer xclim 0.62.0.')
    instante = np.datetime64(observacao.instante_referencia_utc.replace(tzinfo=None), 'ns')
    def serie(valor, unidade):
        return xr.DataArray([valor], dims='time', coords={'time': [instante]}, attrs={'units': unidade})
    saida = cffwis_indices(
        tas=serie(observacao.temperatura, 'degC'), hurs=serie(observacao.humidade, '%'),
        sfcWind=serie(observacao.vento, 'km/h'),
        # Acumulação de exatamente 24 h / 1 dia: valor numérico idêntico.
        pr=serie(observacao.precipitacao_24h, 'mm/day'),
        lat=xr.DataArray(observacao.latitude, attrs={'units': 'degrees_north'}),
        ffmc0=xr.DataArray(anterior.ffmc, attrs={'units': ''}),
        dmc0=xr.DataArray(anterior.dmc, attrs={'units': ''}),
        dc0=xr.DataArray(anterior.dc, attrs={'units': ''}),
        initial_start_up=False, season_method=None, overwintering=False, dry_start=None)
    valores = {campo: numero(getattr(saida, campo.upper()).item(), campo, 0,
                            101 if campo == 'ffmc' else None)
               for campo in ('ffmc', 'dmc', 'dc', 'isi', 'bui', 'fwi')}
    return ResultadoFWI(observacao, anterior, **valores, calculado_em=datetime.now(timezone.utc))
