"""Verifica evidências existentes sem recolher dados nem recalcular o FWI."""
import csv
import hashlib
import itertools
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

OUT = Path('/evidencias')
ROOT = Path('/workspace')
INDICES = ('ffmc', 'dmc', 'dc', 'isi', 'bui', 'fwi')
ATOL, RTOL = 1e-8, 1e-10


def ler(p):
    return json.loads(p.read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def guardar(nome, valor):
    (OUT / nome).write_text(json.dumps(valor, ensure_ascii=False, indent=2,
                                    allow_nan=False), encoding='utf-8')


linhas = []
regioes = []
for ficheiro in sorted(OUT.glob('*_recolha.json')):
    nome = ficheiro.name.removesuffix('_recolha.json')
    meta = ler(ficheiro)
    assert meta['estado'] == 'validado'
    bruto = OUT / f'{nome}_extensao_resposta.json'
    assert sha(bruto) == meta['sha256']
    anterior = ROOT / meta['origem_reutilizada']
    assert sha(anterior / f'{nome}_resposta.json') == meta['sha256_resposta_reutilizada']
    horas = ler(OUT / f'{nome}_horas.json')
    antigos = ler(anterior / f'{nome}_dias.json')
    assert horas[-meta['horas_reutilizadas']:] == [h for d in antigos for h in d['horas']]
    resposta = ler(bruto)
    assert resposta['hourly_units'] == {
        'time': 'iso8601', 'temperature_2m': '°C', 'relative_humidity_2m': '%',
        'wind_speed_10m': 'km/h', 'precipitation': 'mm'}
    bruto_por_hora = {t: i for i, t in enumerate(resposta['hourly']['time'])}
    assert len(bruto_por_hora) == len(resposta['hourly']['time'])
    obs = ler(OUT / f'{nome}_observacoes.json')
    assert len(horas) == 43824 and len(obs) == 1826
    inicio = datetime.fromisoformat(horas[0]['instante_utc'])
    for i, h in enumerate(horas):
        instante = datetime.fromisoformat(h['instante_utc'])
        assert instante == inicio + timedelta(hours=i)
        assert h['qualidade'] == 'valido' and not h['problemas']
        assert (h['latitude_consultada'], h['longitude_consultada']) == (
            meta['regiao']['latitude'], meta['regiao']['longitude'])
        assert h['produto'] == 'open-meteo-archive-ecmwf-ifs-horario-v1'
        assert all(np.isfinite(h[k]) for k in ('temperatura', 'humidade', 'vento', 'precipitacao_hora'))
        assert 0 <= h['humidade'] <= 100 and h['vento'] >= 0 and h['precipitacao_hora'] >= 0
        if i < meta['horas_novas']:
            j = bruto_por_hora[instante.strftime('%Y-%m-%dT%H:%M')]
            for campo, original in [('temperatura', 'temperature_2m'), ('humidade', 'relative_humidity_2m'),
                                    ('vento', 'wind_speed_10m'), ('precipitacao_hora', 'precipitation')]:
                assert h[campo] == resposta['hourly'][original][j]
    for i, o in enumerate(obs):
        grupo = horas[i * 24:(i + 1) * 24]
        assert o['data_referencia'] == (date(2021, 10, 1) + timedelta(days=i)).isoformat()
        ref = datetime.fromisoformat(o['instante_referencia_utc'])
        assert ref == datetime.fromisoformat(grupo[-1]['instante_utc'])
        assert ref.hour == (13 if nome == 'Ponta Delgada' else 12)
        for campo in ('temperatura', 'humidade', 'vento'):
            assert o[campo] == grupo[-1][campo]
        assert abs(o['precipitacao_24h'] - sum(h['precipitacao_hora'] for h in grupo)) < 1e-12
    resumo = ler(OUT / f'{nome}_convergencia.json')
    assert resumo['regressao_existente'] and resumo['erro_regressao'] <= ATOL
    for r in resumo['resultados']:
        anos = r['anos']
        with np.load(OUT / f'{nome}_{anos}anos.npz', allow_pickle=False) as z:
            valores, datas = z['valores'], z['datas']
            assert tuple(z['indices']) == INDICES
            assert np.array_equal(z['sementes'], list(itertools.product((60., 85., 95.), (2., 6., 150.), (5., 15., 1000.))))
        assert valores.shape == (r['dias'], 27, 6)
        assert np.isfinite(valores).all() and (valores >= 0).all()
        assert datas[0] == f'{2026 - anos}-10-01' and datas[-1] == '2026-09-30'
        assert len(set(datas)) == len(datas)
        assert all(date.fromisoformat(str(b)) - date.fromisoformat(str(a)) == timedelta(days=1)
                   for a, b in zip(datas[:-1], datas[1:]))
        spread = np.ptp(valores, axis=1)
        escala = np.max(np.abs(valores), axis=1)
        relativo = np.divide(spread, escala, out=np.zeros_like(spread), where=escala != 0)
        for j, k in enumerate(INDICES):
            m = r['metricas'][k]
            assert m['diferenca_final_absoluta'] == spread[-1, j]
            assert m['diferenca_final_relativa'] == relativo[-1, j]
            assert m['max_diferenca_absoluta'] == spread[:, j].max()
            assert m['max_diferenca_relativa'] == relativo[:, j].max()
            for campo, condicao in [('convergencia_numerica', spread[:, j] <= ATOL + RTOL * escala[:, j]),
                                    ('igualdade_exata', spread[:, j] == 0)]:
                falhas = np.flatnonzero(~condicao)
                idx = int(falhas[-1] + 1) if len(falhas) else 0
                if idx == len(valores):
                    assert m[campo] is None
                else:
                    assert m[campo] == dict(dia=idx + 1, data=str(datas[idx]), dias_seguimento=len(valores) - idx - 1)
            linhas.append(dict(regiao=nome, anos=anos, indice=k, **{
                c: m[c] for c in ('diferenca_final_absoluta', 'diferenca_final_relativa',
                                 'max_diferenca_absoluta', 'max_diferenca_relativa')},
                dia_convergencia=(m['convergencia_numerica'] or {}).get('dia'),
                dia_igualdade=(m['igualdade_exata'] or {}).get('dia')))
    regioes.append(dict(regiao=nome, horas=len(horas), dias=len(obs), regressao=resumo['erro_regressao'],
                        segundos=resumo['segundos'], pico_rss_mib=resumo['pico_rss_mib']))

rh = ler(OUT / 'rh100_impacto.json')
assert rh['casos'] == 18 and rh['regioes'] == 12 and len(rh['comparacoes']) == 108
assert rh['atol'] == ATOL and rh['rtol'] == RTOL
for r in rh['comparacoes']:
    assert np.isclose(r['xclim_rh100'], r['cffdrs_interno_rh100'], atol=ATOL, rtol=RTOL)
    assert np.isclose(r['xclim_rh999999'], r['cffdrs_publico'], atol=ATOL, rtol=RTOL)
assert sum(v['comparacoes_publico_fora_tolerancia'] for v in rh['resumo'].values()) == 56
for nome, fonte in ler(OUT / 'fontes/manifesto.json').items():
    assert sha(OUT / 'fontes' / nome) == fonte['sha256']
with (OUT / 'comparacao_sementes.csv').open('w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(linhas[0]), lineterminator='\n')
    w.writeheader()
    w.writerows(linhas)
guardar('integridade.json', dict(estado='aprovado', regioes=regioes, horas=306768,
    dias_unicos=12782, dias_por_semente_e_horizontes=28119, dias_calculados_27_sementes=759213,
    matrizes=28, metricas=168, comparacoes_rh=108, verificacoes_referencia_rh=216,
    divergencias_publicas_preservadas=56, novas_chamadas=0, acesso_bd=False))
ficheiros = {str(p.relative_to(OUT)): sha(p) for p in sorted(OUT.rglob('*'))
             if p.is_file() and p.name != 'checksums_finais.json'}
guardar('checksums_finais.json', ficheiros)
print(json.dumps(ler(OUT / 'integridade.json'), ensure_ascii=False, indent=2))
