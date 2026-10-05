"""Triagem exploratória; limiares não são classes de risco nem tetos físicos."""
import csv
import json
import sys
from pathlib import Path
import numpy as np

OUT=Path('/evidencias')
FASE6=Path('/workspace/experiments/fwi_fase6/evidencias')
INDICES=('ffmc','dmc','dc','isi','bui','fwi')
# Fixados antes de observar os resultados da Fase 7. Apenas geram alertas.
SALTOS=dict(ffmc=40,dmc=100,dc=150,isi=15,bui=100,fwi=25)
EXTREMO_FWI=50


def ler(p): return json.loads(p.read_text())
def guardar(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def amostrar(pasta,nome,dias,selecionados):
    r=ler(pasta/f'{nome}_recolha.json')['regiao']
    ficheiro=pasta/f'{nome}_amostra_inputs.csv'
    with ficheiro.open() as f: existentes=list(csv.DictReader(f))
    indices={int(r['indice']) for r in existentes}|selecionados
    with ficheiro.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['indice','yr','mon','day','lat','long','temp','rh','ws','prec','ffmc0','dmc0','dc0']);w.writeheader()
        for i in sorted(indices):
            d=dias[i]; o=d['observacao']; a=d['estado_anterior']; y,m,dia=map(int,d['data_referencia'].split('-'))
            w.writerow(dict(indice=i,yr=y,mon=m,day=dia,lat=r['latitude'],long=r['longitude'],temp=o['temperatura'],rh=o['humidade'],
                ws=o['vento'],prec=o['precipitacao_24h'],ffmc0=a['ffmc'],dmc0=a['dmc'],dc0=a['dc']))


def analisar(janela):
    pasta=OUT/str(janela)
    alertas=[]; series={}; selecoes={}
    for p in sorted(pasta.glob('*_dias.json')):
        nome=p.name.removesuffix('_dias.json'); dias=ler(p); series[nome]=dias;selecoes[nome]=set()
        assert len(dias)==janela
        assert len(set(d['data_referencia'] for d in dias))==janela
        for i,d in enumerate(dias):
            for k in INDICES:
                assert np.isfinite(d[k]) and d[k]>=0, (nome,d['data_referencia'],k)
                tipo=None
                if i and abs(d[k]-dias[i-1][k])>SALTOS[k]: tipo='salto'
                if k=='fwi' and d[k]>EXTREMO_FWI: tipo='fwi_extremo' if tipo is None else 'salto_e_extremo'
                if tipo:
                    selecoes[nome].add(i)
                    alertas.append(dict(regiao=nome,data=d['data_referencia'],indice=k,tipo=tipo,valor=d[k],
                        anterior=dias[i-1][k] if i else d['estado_anterior'].get(k),
                        inputs=d['observacao'],inputs_anteriores=dias[i-1]['observacao'] if i else None,
                        estado_anterior=d['estado_anterior']))
    # Comparar apenas séries com a mesma duração, data final e semente.
    for k in INDICES:
        maximos={n:max(d[k] for d in ds) for n,ds in series.items()}
        q1,q3=np.percentile(list(maximos.values()),[25,75]);limite=float(q3+3*(q3-q1))
        for n,v in maximos.items():
            if v>limite:
                i=max(range(janela),key=lambda i:series[n][i][k]);d=series[n][i];selecoes[n].add(i)
                alertas.append(dict(regiao=n,data=d['data_referencia'],indice=k,tipo='discrepancia_regional',valor=v,
                    limite_exploratorio=limite,inputs=d['observacao'],estado_anterior=d['estado_anterior']))
    for n,indices in selecoes.items(): amostrar(pasta,n,series[n],indices)
    guardar(pasta/'alertas.json',dict(limiares_salto=SALTOS,limiar_fwi=EXTREMO_FWI,
        regra_regional='máximo regional > Q3 + 3 IQR dos máximos; apenas mesma janela',alertas=alertas))
    if janela==60: guardar(OUT/'ampliar.json',sorted(set(a['regiao'] for a in alertas)))
    print('Janela',janela,'alertas',len(alertas),'regiões',sorted(set(a['regiao'] for a in alertas)),flush=True)


def tabelas():
    linhas=[]
    for pasta,fase in [(FASE6,'6'),(OUT/'60','7'),(OUT/'365','7')]:
        for p in sorted(pasta.glob('*_resultado.json')):
            n=p.name.removesuffix('_resultado.json');r=ler(p)
            for k in INDICES:
                e=r['estatisticas'][k]
                linhas.append(dict(regiao=n,fase=fase,dias=r['dias'],indice=k,**{s:e[s] for s in ('min','mediana','p95','max')}))
    with (OUT/'estatisticas_nacionais.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(linhas[0]));w.writeheader();w.writerows(linhas)
    texto=['# Comparação dos pontos do catálogo','',
        'Estatísticas descritivas, não um índice nacional agregado. Janelas e sementes indicadas; não confundir séries de 60/365 dias.','',
        '| Região | Fase | Dias | Índice | Mínimo | Mediana | P95 | Máximo |','|---|---:|---:|---|---:|---:|---:|---:|']
    for l in linhas: texto.append(f"| {l['regiao']} | {l['fase']} | {l['dias']} | {l['indice'].upper()} | "+' | '.join(f'{l[s]:.6g}' for s in ('min','mediana','p95','max'))+' |')
    (OUT/'estatisticas_nacionais.md').write_text('\n'.join(texto)+'\n',encoding='utf-8')


if __name__=='__main__':
    if sys.argv[1]=='tabelas': tabelas()
    else: analisar(int(sys.argv[1]))
