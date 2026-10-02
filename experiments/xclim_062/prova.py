"""Prova isolada: não importa nem utiliza a heurística FWI do VIGA."""
import csv
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

PASTA = Path(__file__).resolve().parent
SAIDA = PASTA / 'resultados'
SAIDA.mkdir(exist_ok=True)


def memoria():
    campos = dict(linha.split(':', 1) for linha in Path('/proc/self/status').read_text().splitlines() if ':' in linha)
    return {k: int(campos[k].split()[0]) * 1024 for k in ('VmRSS', 'VmHWM')}


mem_antes = memoria()
inicio = time.perf_counter()
import xclim
tempo_importacao = time.perf_counter() - inicio
mem_importacao = memoria()
import numpy as np
import pandas as pd
import xarray as xr
from xclim.indices.fire import cffwis_indices

# Tolerâncias fixadas antes de executar a comparação com R, em float64.
ATOL, RTOL = 1e-8, 1e-10
NOMES = ('DC', 'DMC', 'FFMC', 'ISI', 'BUI', 'FWI')
ESTADO = {'FFMC': 85.0, 'DMC': 6.0, 'DC': 15.0}


def calcular(dados, latitude=40.0, estado=None, instantes=None):
    estado = ESTADO if estado is None else estado
    if instantes is None:
        instantes = pd.to_datetime(dict(year=dados.YR, month=dados.MON, day=dados.DAY)) + pd.Timedelta(hours=12)
    def serie(coluna, unidade):
        return xr.DataArray(dados[coluna].to_numpy(dtype=float), dims='time',
                            coords={'time': instantes}, attrs={'units': unidade})
    # PREC é uma acumulação em mm ao longo de exatamente 24 h.
    # A API pública espera taxa diária: total_mm / 1 dia, numericamente igual.
    return cffwis_indices(tas=serie('TEMP', 'degC'), hurs=serie('RH', '%'),
                         sfcWind=serie('WS', 'km/h'), pr=serie('PREC', 'mm/day'),
                         lat=xr.DataArray(latitude, attrs={'units': 'degrees_north'}),
                         **{k.lower()+'0': xr.DataArray(v, attrs={'units': ''}) for k, v in estado.items()},
                         initial_start_up=False, season_method=None, overwintering=False, dry_start=None)


def matriz(resultado):
    return np.column_stack([a.values for a in resultado])


def comparar(dados, latitude, nome):
    calculado = matriz(calcular(dados, latitude))
    esperado = dados[list(NOMES)].to_numpy()
    absoluto = np.abs(calculado - esperado)
    relativo = np.divide(absoluto, np.abs(esperado), out=np.zeros_like(absoluto), where=esperado != 0)
    linhas = []
    for i, row in dados.iterrows():
        for j, indice in enumerate(NOMES):
            linhas.append({'dia': i+1, 'indice': indice, 'latitude': latitude,
                           **{k: row[k] for k in ('YR', 'MON', 'DAY', 'TEMP', 'RH', 'WS', 'PREC')},
                           'xclim': calculado[i,j], 'referencia': esperado[i,j],
                           'diferenca_absoluta': absoluto[i,j], 'diferenca_relativa': relativo[i,j]})
    pd.DataFrame(linhas).to_csv(SAIDA / f'comparacao_{nome}.csv', index=False)
    passou = bool(np.allclose(calculado, esperado, atol=ATOL, rtol=RTOL))
    return {'passou': passou, 'dias': len(dados), 'max_abs': dict(zip(NOMES, absoluto.max(axis=0))),
            'max_rel': dict(zip(NOMES, relativo.max(axis=0)))}, calculado


def ml():
    sys.path.insert(0, '/app')
    from services.artefactos_ml import carregar_artefactos
    from services.modelo_ml import prever_risco
    import shap
    artefactos = carregar_artefactos()
    dados = dict(temperatura=20., humidade=50., velocidade_vento=10., precipitacao=0.,
                 ffmc=85., dmc=6., dc=15., isi=5., distrito='Lisboa', latitude=38.7223,
                 longitude=-9.1393, data_hora=datetime(2024,7,1,12,tzinfo=timezone.utc))
    previsao = prever_risco(dados)
    assert previsao['estado'] == 'ok', previsao
    # Exercita também a extensão SHAP/XGBoost com inputs técnicos, não apenas o import.
    kaggle, escala, _, _, _ = artefactos
    x = escala.transform(np.array([[20,50,10,0,85,6,15,5,7,1]], dtype=float))
    valores = shap.TreeExplainer(kaggle).shap_values(x)
    assert np.isfinite(valores).all()
    return {'artefactos': len(artefactos), 'previsao_tecnica': previsao,
            'shap_shape': list(np.asarray(valores).shape), 'shap_finito': True}


if '--ml' in sys.argv:
    print(json.dumps(ml(), ensure_ascii=False))
    sys.exit(0)

dados = pd.read_csv(SAIDA / 'cffdrs_completo.csv')
if '--retomar' in sys.argv:
    estado = json.loads((SAIDA / 'estado_dia_n.json').read_text())
    np.save(SAIDA / 'retoma.npy', matriz(calcular(dados.iloc[1:], estado=estado)))
    sys.exit(0)
inicio = time.perf_counter()
referencia, completo = comparar(dados, 40., 'calibracao')
primeira_chamada = time.perf_counter() - inicio
# Registar a reprovação científica sem impedir os restantes testes independentes.
classico, _ = comparar(pd.read_csv(SAIDA / 'cffdrs_classico_40.csv'), 40., 'classico')

# Estado serializado em disco e restaurado noutro processo Python.
primeiro = calcular(dados.iloc[:1])
estado_n = {k: float(getattr(primeiro, k).values[-1]) for k in ESTADO}
(SAIDA / 'estado_dia_n.json').write_text(json.dumps(estado_n), encoding='utf-8')
subprocess.run([sys.executable, __file__, '--retomar'], check=True)
retoma = np.load(SAIDA / 'retoma.npy')
assert np.array_equal(completo[1:], retoma)
continuidade = {'igualdade_exata': True, 'max_abs': float(np.max(np.abs(completo[1:] - retoma))),
                'estado_dia_n': estado_n, 'indices_dia_n_mais_1': dict(zip(NOMES, retoma[0]))}

territorios = {}
for nome, latitude, zona, hora_utc in [('Continente',38.7223,'Europe/Lisbon',12),
                                    ('Madeira',32.6669,'Atlantic/Madeira',12),
                                    ('Açores',37.7412,'Atlantic/Azores',13)]:
    ref = pd.read_csv(SAIDA / f'cffdrs_{latitude}.csv')
    comp, _ = comparar(ref, latitude, nome)
    comp_classico, _ = comparar(pd.read_csv(SAIDA / f'cffdrs_classico_{latitude}.csv'), latitude, nome+'_classico')
    datas_testadas = []
    for data in ('2024-02-28','2024-03-30','2024-10-26'):
        instantes = pd.date_range(data, periods=3, freq='D') + pd.Timedelta(hours=hora_utc)
        arr = matriz(calcular(dados.iloc[:3], latitude, instantes=instantes))
        assert np.isfinite(arr).all()
        assert (np.diff(instantes.values) == np.timedelta64(24, 'h')).all()
        for t in instantes:
            utc = t.to_pydatetime().replace(tzinfo=timezone.utc)
            civil = utc.astimezone(ZoneInfo(zona))
            padrao = utc.astimezone(timezone(timedelta(hours=12-hora_utc)))
            assert padrao.hour == 12 and padrao.date() == utc.date()
            datas_testadas.append({'utc': utc.isoformat(), 'civil': civil.isoformat(),
                                  'padrao': padrao.isoformat()})
    territorios[nome] = {'latitude': latitude, 'referencia': comp, 'referencia_classica':comp_classico, 'instantes': datas_testadas}

# Equivalência explícita das unidades: °C/K; km/h/m/s; %/fração; mm/d/mm/s.
tempo = pd.date_range('1985-04-13T12:00', periods=len(dados), freq='D')
def arr(v,u):
    return xr.DataArray(v, dims='time',coords={'time':tempo},attrs={'units':u})
convertido = cffwis_indices(tas=arr(dados.TEMP.to_numpy()+273.15,'K'),
    pr=arr(dados.PREC.to_numpy()/86400.,'mm/s'),
    sfcWind=arr(dados.WS.to_numpy()/3.6,'m/s'), hurs=arr(dados.RH.to_numpy()/100.,'1'),
    lat=xr.DataArray(40.,attrs={'units':'degrees_north'}),
    **{k.lower()+'0':xr.DataArray(v,attrs={'units':''}) for k,v in ESTADO.items()}, initial_start_up=False)
assert np.allclose(matriz(convertido), completo, atol=ATOL, rtol=RTOL)

# Falta de um dia: nunca preencher com zero. Apenas caracteriza a propagação de NaN.
incompleto = dados.copy()
incompleto.loc[3,'TEMP'] = np.nan
lacuna = matriz(calcular(incompleto))
lacunas = {'dia_sem_temperatura': dict(zip(NOMES, np.isnan(lacuna[3]).tolist())),
           'dia_seguinte': dict(zip(NOMES, np.isnan(lacuna[4]).tolist()))}

def benchmark(n):
    t = pd.date_range('2023-01-01T12:00', periods=365, freq='D')
    coords = {'regiao':np.arange(n),'time':t}
    def serie(v,u):
        return xr.DataArray(np.full((n,365),v,dtype=float),dims=('regiao','time'),coords=coords,attrs={'units':u})
    kw = dict(tas=serie(20,'degC'),hurs=serie(50,'%'),sfcWind=serie(10,'km/h'),pr=serie(0,'mm/day'),
              lat=xr.DataArray(np.linspace(32.6,41.3,n),dims='regiao',attrs={'units':'degrees_north'}),
              initial_start_up=False,
              **{k.lower()+'0':xr.DataArray(np.full(n,v),dims='regiao',attrs={'units':''}) for k,v in ESTADO.items()})
    tempos=[]
    for _ in range(5):
        inicio=time.perf_counter()
        saida=cffwis_indices(**kw)
        assert all(np.isfinite(v.values).all() for v in saida)
        tempos.append(time.perf_counter()-inicio)
    return {'segundos':tempos,'mediana_s':float(np.median(tempos)), 'dias':365,'regioes':n}

bench = {'importacao_xclim_s':tempo_importacao, 'primeira_comparacao_48_dias_s':primeira_chamada,
         'rss_antes':mem_antes,'rss_importacao':mem_importacao,
         'uma_regiao':benchmark(1),'vinte_oito_regioes':benchmark(28),'rss_depois_calculo':memoria(),
         'python':sys.version,'plataforma':platform.platform(),'cpus_visiveis':os.cpu_count(),
         'cpu': next((s for s in Path('/proc/cpuinfo').read_text().splitlines() if s.startswith('model name')),None)}
resultado_ml = ml()
relatorio = {'xclim':xclim.__version__,'atol':ATOL,'rtol':RTOL,'referencia':referencia,'referencia_classica':classico,
             'continuidade':continuidade,'territorios':territorios,'unidades_equivalentes':True,
             'lacunas':lacunas,'benchmark':bench,'ml':resultado_ml}
(SAIDA / 'prova.json').write_text(json.dumps(relatorio, indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'referencia_1_9_2':referencia,'referencia_1_8_17':classico,'continuidade':continuidade,
                  'benchmark':bench,'ml':resultado_ml},ensure_ascii=False))
# Uma diferença de variante não é transformada num teste aprovado.
sys.exit(0 if referencia['passou'] and classico['passou'] else 1)
