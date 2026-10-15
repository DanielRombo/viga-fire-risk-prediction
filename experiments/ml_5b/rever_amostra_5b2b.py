"""Contraprova local da amostra no export original, sem rede ou BD."""
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from auditar_5b2b import ler
from obter_5b2b import ROOT, sha


def main():
    amostra = json.loads((ROOT / 'amostra_revisao.json').read_text(encoding='utf-8'))
    mapa = defaultdict(set)
    for _, r in ler(ROOT.parent / 'fontes_5b2/sgif_administracao.bin'):
        mapa[r['INE'].zfill(6)].add(r['DTCC'])
    eliminados = {r['Codigo'] for _, r in ler(ROOT / 'Data2001_noweliminados.csv')}
    eventos = defaultdict(list)
    sado_ano = Counter()
    identidades = Counter()
    causas = Counter()
    for _, r in ler(ROOT / 'Data2001_now.csv'):
        if r['CodigoSado']:
            sado_ano[r['Ano'], r['CodigoSado']] += 1
        identidades[r['DHInicio'], r['INE'], r['Lat_4326'], r['Lon_4326'], r['Tipo']] += 1
        reac = bool(r['Reacendimento_IncendioPai']) or r['Reacendimentos'] not in ('', '0')
        if r['CodCausa'] == '711':
            causas['711_com_marcador' if reac else '711_sem_marcador'] += 1
        codigos = mapa.get(r['INE'].zfill(6), set())
        if len(codigos) != 1:
            continue
        c = next(iter(codigos))
        if c not in ('1106', '0805', '1714') or r['Ano'] != '2023':
            continue
        if r['Codigo'] in eliminados or reac or r['CodCausa']=='711' or r['Tipo'] not in ('Florestal', 'Agrícola'):
            continue
        eventos[c].append({k: r[k] for k in ('Codigo', 'DHInicio', 'Tipo', 'INE', 'Lat_4326', 'Lon_4326')})
    resultado = []
    for a in amostra:
        t = datetime.fromisoformat(a['data_T'])
        fim = t + timedelta(days=1)
        selecoes = {}
        for nome, fuso in [('local', ZoneInfo('Europe/Lisbon')), ('utc', timezone.utc)]:
            ordenados = sorted((datetime.fromisoformat(r['DHInicio']).replace(tzinfo=fuso).astimezone(timezone.utc), r['Codigo'], r) for r in eventos[a['municipio']])
            dentro = [r for d, _, r in ordenados if t < d <= fim]
            assert bool(dentro) == bool(a['target_24h']), (a, nome, dentro)
            antes = [r for d, _, r in ordenados if d <= t]
            depois = [r for d, _, r in ordenados if d > fim]
            selecoes[nome] = dict(dentro=dentro, anterior=antes[-1] if antes else None, seguinte=depois[0] if depois else None)
        resultado.append(dict(municipio=a['municipio'], T=a['data_T'], target=a['target_24h'], coverage_status=a['coverage_status'], verificacao=selecoes))
    (ROOT / 'amostra_contraprova.json').write_text(json.dumps(resultado, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    resumo = dict(amostras=len(resultado), positivos=sum(r['target']==1 for r in resultado), negativos=sum(r['target']==0 for r in resultado),
                  grupos_sado_ano_repetidos=sum(n>1 for n in sado_ano.values()), grupos_mesmo_instante_codigo_ine_coordenada_tipo=sum(n>1 for n in identidades.values()), causas=dict(causas))
    # Contagens para o plano, não execução do dataset completo.
    plano = defaultdict(Counter)
    with (ROOT/'labels.csv').open(encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['municipio'] in eventos and '2022' <= r['data_T'][:4] <= '2024':
                plano[r['municipio'],r['data_T'][:4]][r['target_24h'] or 'null'] += 1
    resumo['plano_2022_2024'] = [dict(municipio=c,ano=y,**dict(v)) for (c,y),v in sorted(plano.items())]
    (ROOT/'revisao_resumo.json').write_text(json.dumps(resumo,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(resumo,ensure_ascii=True))
    for r in resultado:
        print(r['municipio'], r['T'][:10], r['target'], [(v['Codigo'],v['DHInicio']) for v in r['verificacao']['local']['dentro']])
    ficheiros = sorted(p for p in ROOT.iterdir() if p.is_file() and p.name != 'integridade_final.json')
    manifest = [dict(nome=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in ficheiros]
    (ROOT/'integridade_final.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')


if __name__ == '__main__':
    main()
