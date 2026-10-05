"""Seleção objetiva de episódios e comparação de amostra, sem limites artificiais."""
import csv
import json
import sys
from pathlib import Path
import numpy as np

OUT = Path('/evidencias')
INDICES = ('ffmc', 'dmc', 'dc', 'isi', 'bui', 'fwi')
ATOL, RTOL = 1e-8, 1e-10  # Tolerâncias da prova, sem alterações.


def guardar(nome, valor):
    (OUT/nome).write_text(json.dumps(valor, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def preparar(nome):
    dias = json.loads((OUT/f'{nome}_dias.json').read_text())
    r = json.loads((OUT/f'{nome}_recolha.json').read_text())['regiao']
    def valor(i,k): return dias[i]['observacao'][k]
    maior_chuva = max(range(len(dias)), key=lambda i: valor(i,'precipitacao_24h'))
    maior_vento = max(range(len(dias)), key=lambda i: valor(i,'vento'))
    maior_humidade = max(range(len(dias)), key=lambda i: valor(i,'humidade'))
    sequencias, inicio = [], None
    for i in range(len(dias)+1):
        seco = i < len(dias) and valor(i,'precipitacao_24h') == 0
        if seco and inicio is None: inicio = i
        if not seco and inicio is not None:
            sequencias.append((inicio, i-1))
            inicio = None
    seco = max(sequencias, key=lambda p:p[1]-p[0]) if sequencias else None
    indices = {0,len(dias)-1,maior_chuva,maior_vento,maior_humidade}
    saltos = {}
    for k in INDICES:
        v = np.array([d[k] for d in dias])
        idx = int(np.argmax(np.abs(np.diff(v))))+1
        saltos[k] = {'data':dias[idx]['data_referencia'], 'anterior':float(v[idx-1]),
            'atual':float(v[idx]), 'diferenca':float(v[idx]-v[idx-1]),
            'meteorologia_anterior':dias[idx-1]['observacao'], 'meteorologia':dias[idx]['observacao']}
        indices.update((idx-1,idx,int(v.argmax()),int(v.argmin())))
    periodos = {'chuva_forte':(max(0,maior_chuva-3),min(len(dias)-1,maior_chuva+4)),
        'vento_elevado':(max(0,maior_vento-1),min(len(dias)-1,maior_vento+1)),
        'humidade_elevada':(max(0,maior_humidade-1),min(len(dias)-1,maior_humidade+1))}
    if seco:
        periodos['seca_e_transicoes']=(max(0,seco[0]-2),min(len(dias)-1,seco[1]+2))
        indices.update((seco[0],seco[1]))
    def resumir(d): return dict(data=d['data_referencia'], **d['observacao'], **{k:d[k] for k in INDICES})
    guardar(f'{nome}_episodios.json', {'periodos':{k:[resumir(d) for d in dias[a:b+1]] for k,(a,b) in periodos.items()},
        'maiores_saltos':saltos, 'seca_sem_chuva_dias':seco[1]-seco[0]+1 if seco else 0})
    with (OUT/f'{nome}_amostra_inputs.csv').open('w',newline='') as f:
        campos=['indice','yr','mon','day','lat','long','temp','rh','ws','prec','ffmc0','dmc0','dc0']
        writer=csv.DictWriter(f,fieldnames=campos); writer.writeheader()
        for i in sorted(indices):
            d=dias[i]; o=d['observacao']; ant=d['estado_anterior']
            y,m,day=map(int,d['data_referencia'].split('-'))
            writer.writerow(dict(indice=i,yr=y,mon=m,day=day,lat=r['latitude'],long=r['longitude'],
                temp=o['temperatura'],rh=o['humidade'],ws=o['vento'],prec=o['precipitacao_24h'],
                ffmc0=ant['ffmc'],dmc0=ant['dmc'],dc0=ant['dc']))
    print(nome, 'amostra:',len(indices), 'dias; seca:',seco)


def comparar(nome):
    dias=json.loads((OUT/f'{nome}_dias.json').read_text())
    linhas=[]
    with (OUT/f'{nome}_referencia.csv').open() as f:
        for row in csv.DictReader(f):
            d=dias[int(row['indice'])]
            for k in INDICES:
                ref=float(row[k.upper()]); x=d[k]; erro=abs(x-ref)
                linhas.append(dict(data=d['data_referencia'], indice=k, xclim=x, referencia=ref,
                    diferenca_absoluta=erro, diferenca_relativa=erro/abs(ref) if ref else (0 if x==0 else None),
                    passou=bool(np.isclose(x,ref,atol=ATOL,rtol=RTOL))))
    guardar(f'{nome}_comparacao.json',dict(atol=ATOL,rtol=RTOL,
        referencia='cffdrs 1.8.17; lat.adjust=TRUE; estado anterior persistido explícito por dia',
        passou=all(l['passou'] for l in linhas),comparacoes=linhas))
    assert all(l['passou'] for l in linhas), 'Divergência científica: bloquear avanço'
    print(nome,len(linhas),'comparações passaram; maior erro absoluto:',max(l['diferenca_absoluta'] for l in linhas))


if __name__ == '__main__':
    (preparar if sys.argv[1]=='preparar' else comparar)(sys.argv[2])
