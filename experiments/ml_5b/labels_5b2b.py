"""Labels experimentais de ocorrências registadas, com sensibilidade UTC/hora civil."""
import bisect
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from obter_5b2b import ROOT
from reconciliar_5b2b import gravar

UTC=timezone.utc;LIS=ZoneInfo('Europe/Lisbon')

def variantes(s):
    t=datetime.fromisoformat(s)
    return (t.replace(tzinfo=LIS,fold=0).astimezone(UTC),t.replace(tzinfo=UTC))

def contar(xs,t,fim):return bisect.bisect_right(xs,fim)-bisect.bisect_right(xs,t)

def decidir(nlocal,nutc,coberto,bloqueado=False):
    if nlocal>0 and nutc>0:return 1,'positivo_estavel_convencoes'
    if bool(nlocal)!=bool(nutc):return None,'sensibilidade_fuso'
    if bloqueado:return None,'incerteza_temporal_territorial'
    if not coberto:return None,'cobertura_nao_aprovada'
    return 0,'zero_cobertura_empirica_aceitavel'

def main():
    cat=json.loads((ROOT.parent/'auditoria_5b2/municipios_catalogo.json').read_text(encoding='utf-8'))
    nomes={r['codigos_candidatos'][0]:r['nome'] for r in cat if len(r['codigos_candidatos'])==1}
    cobertura={}
    with (ROOT/'matriz_mensal.csv').open(encoding='utf-8') as f:
        for r in csv.DictReader(f):cobertura[r['municipio'],int(r['ano']),int(r['mes'])]=r['coverage_status']
    conflitos={};bloq=defaultdict(list);eventos=defaultdict(lambda:([],[]));ids=defaultdict(list)
    with (ROOT/'territorio_piloto.csv').open(encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['coerente']=='False':
                conflitos[r['Codigo']]=set(filter(None,[r['municipio'],*r['municipios_geometria'].split('|')]))
    with (ROOT/'consolidado.csv').open(encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if not '2017'<=r['DHInicio'][:4]<='2025':continue
            c=r['municipio'];a,b=variantes(r['DHInicio'])
            naive=datetime.fromisoformat(r['DHInicio'])
            dst=naive.replace(tzinfo=LIS,fold=0).utcoffset()!=naive.replace(tzinfo=LIS,fold=1).utcoffset()
            if r['Codigo'] in conflitos or dst or r['motivo']=='territorio_incerto':
                for cod in conflitos.get(r['Codigo'],{c}):bloq[cod].extend((a,b))
                continue
            if r['motivo']!='candidato':continue
            eventos[c][0].append(a);eventos[c][1].append(b)
            ids[c].append((a,r['Codigo'],r['DHInicio']))
    for arr in eventos.values():arr[0].sort();arr[1].sort()
    for arr in bloq.values():arr.sort()
    resultado=[];res=Counter();por=defaultdict(Counter);amostra=[]
    for c,nome in nomes.items():
        t=datetime(2018,1,1,15,tzinfo=UTC)
        while t.year<=2024:
            fim=t+timedelta(days=1)
            chaves={(c,d.year,d.month) for d in (t,fim,t.astimezone(LIS),fim.astimezone(LIS))}
            estados={cobertura.get(k,'sem evidencia') for k in chaves}
            coberto=estados<={'aceitavel','forte'}
            nl,nu=(contar(arr,t,fim) for arr in eventos[c])
            bl=contar(bloq[c],t-timedelta(hours=2),fim+timedelta(hours=2))>0
            y,motivo=decidir(nl,nu,coberto,bl)
            status='aceitavel' if coberto else 'duvidosa' if 'duvidosa' in estados else 'sem evidencia'
            label='null' if y is None else str(y)
            res[label]+=1;por[c,t.year,t.month][label]+=1
            row=dict(municipio=c,nome=nome,data_T=t.isoformat(),target_24h='' if y is None else y,
                     coverage_status=status,territory_confidence='media',motivo=motivo,
                     n_local=nl,n_utc=nu,source_version='SGIF_20260324_INE_20260530',
                     validacao_poligonal=c in ('1106','0805','1714','0303','0603'))
            resultado.append(row)
            if c in ('1106','0805','1714') and '2023-04-01'<=t.date().isoformat()<='2023-09-30' and y is not None:
                encontrados=[dict(id=i,DHInicio=s) for instante,i,s in ids[c] if t<instante<=fim]
                amostra.append(dict(**row,ids_local=encontrados))
            t=fim
    gravar('labels.csv',resultado)
    gravar('labels_mensais.csv',[dict(municipio=c,ano=y,mes=m,positivos=n['1'],negativos=n['0'],null=n['null'],
                  prevalencia=n['1']/(n['1']+n['0']) if n['1']+n['0'] else None) for (c,y,m),n in sorted(por.items())])
    (ROOT/'labels_resumo.json').write_text(json.dumps(dict(contagens=dict(res),total=len(resultado),
          prevalencia=res['1']/(res['1']+res['0']),convencao='Europe/Lisbon; sensibilidade UTC; T=15UTC',
          natureza='labels experimentais; não certificação absoluta de todas as ignições'),indent=2)+'\n',encoding='utf-8')
    # Seleção determinística por município/data, sem selecionar features ou alterar labels.
    selecao=[]
    for c,np,nn in [('1106',4,7),('0805',3,7),('1714',3,6)]:
        for y,n in [(1,np),(0,nn)]:
            pool=[r for r in amostra if r['municipio']==c and r['target_24h']==y]
            assert len(pool)>=n
            selecao.extend(pool[round(i*(len(pool)-1)/(n-1))] for i in range(n))
    (ROOT/'amostra_revisao.json').write_text(json.dumps(selecao,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(dict(res));print('amostra',Counter(r['target_24h'] for r in selecao))

if __name__=='__main__':main()
