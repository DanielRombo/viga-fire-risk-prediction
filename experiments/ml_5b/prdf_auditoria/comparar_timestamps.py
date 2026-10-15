"""Comparação dirigida 2022–2024, sem labels 2025 nem acesso a modelos."""
import csv
import hashlib
import json
import sqlite3
import statistics
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2];ML=OUT.parent
UTC=timezone.utc;LIS=ZoneInfo('Europe/Lisbon')

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def quantile(xs,q):
    a=sorted(xs);i=(len(a)-1)*q;lo=int(i);return a[lo]+(a[min(lo+1,len(a)-1)]-a[lo])*(i-lo)

def stats(xs):
    if not xs:return {'n':0}
    return dict(n=len(xs),unidade='minutos',media=statistics.mean(xs),mediana=statistics.median(xs),
        p25=quantile(xs,.25),p75=quantile(xs,.75),p90=quantile(xs,.9),p95=quantile(xs,.95),min=min(xs),max=max(xs),
        percentagem_abs_ate={str(m):100*sum(abs(x)<=m for x in xs)/len(xs) for m in (5,15,30,60)})

def janela(t):
    # Na fronteira das 15:00 o evento pertence ao horizonte iniciado no dia anterior.
    anchor=t.replace(hour=15,minute=0,second=0,microsecond=0)
    return (anchor-timedelta(days=1) if t<=anchor else anchor).isoformat()

def main():
    original=ML/'cobertura_5b2b/Data2001_now.csv'
    m=json.loads(original.with_suffix('.manifesto.json').read_text())
    assert sha(original)==m['sha256']
    sgif={};duplicates=Counter()
    with original.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            if r['DHInicio'][:4] not in ('2022','2023','2024'):continue
            duplicates[r['Codigo']]+=1
            sgif[r['Codigo']]={k:r[k] for k in ('Codigo','DHInicio','Concelho','Distrito','INE','Tipo')}
    prdf=ROOT/'data/prdf/fogos.gpkg';before=prdf.stat();pmap=defaultdict(list)
    with sqlite3.connect(prdf.resolve().as_uri()+'?mode=ro',uri=True) as c:
        c.execute('PRAGMA query_only=ON')
        cols=[r[1] for r in c.execute('PRAGMA table_info(Fogos)')]
        for row in c.execute('SELECT Codigo,DHInicio,DH1Intervencao,DHResolucao,DHFim FROM Fogos WHERE Ano IN (2022,2023,2024)'):
            pmap[row[0]].append(row)
    wall=defaultdict(list);literal=defaultdict(list);extremos=[];changed=Counter();matched={};invalid=[];z=Counter()
    for code,r in sgif.items():
        if duplicates[code]!=1 or len(pmap.get(code,[]))!=1:continue
        value=pmap[code][0][1]
        try:
            s=datetime.fromisoformat(r['DHInicio']);p=datetime.fromisoformat(value.replace('Z','+00:00'))
            w=(p.replace(tzinfo=None)-s).total_seconds()/60
            assert p.tzinfo is not None
            delta=(p-s.replace(tzinfo=LIS,fold=0).astimezone(UTC)).total_seconds()/60
        except (ValueError,TypeError,AssertionError):invalid.append(code);continue
        yr=r['DHInicio'][:4];wall[yr].append(w);literal[yr].append(delta);z[str(p.utcoffset())]+=1
        j1=janela(s.replace(tzinfo=LIS,fold=0).astimezone(UTC));j2=janela(p.astimezone(UTC))
        changed[yr]+=j1!=j2;matched[code]=dict(prdf=value,sgif=r['DHInicio'],delta_wall=w)
        extremos.append(dict(codigo=code,concelho=r['Concelho'],sgif=r['DHInicio'],prdf=value,
            diferenca_relogio_min=w,diferenca_literal_vs_lisboa_min=delta,muda_janela=j1!=j2))
    # Verificar rastreio do consolidado usado pelos labels e a população candidata dos três municípios.
    lineage=Counter();candidatos=Counter();alteracoes_candidatos=Counter()
    with (ML/'cobertura_5b2b/consolidado.csv').open(encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['DHInicio'][:4] not in ('2022','2023','2024'):continue
            assert r['DHInicio']==sgif[r['Codigo']]['DHInicio'];lineage['timestamps_inalterados']+=1
            if r['municipio'] not in ('1106','0805','1714') or r['motivo']!='candidato':continue
            key=r['municipio']+'/'+r['DHInicio'][:4];candidatos[key]+=1
            if r['Codigo'] not in matched:lineage['candidato_sem_match']+=1;continue
            s=datetime.fromisoformat(r['DHInicio']).replace(tzinfo=LIS,fold=0).astimezone(UTC)
            p=datetime.fromisoformat(matched[r['Codigo']]['prdf'].replace('Z','+00:00')).astimezone(UTC)
            alteracoes_candidatos[key]+=janela(s)!=janela(p)
    # Não gera labels novos: mede presença já guardada nas duas convenções em 5B.3.
    windows=defaultdict(Counter);amostras=[]
    with (ML/'dataset_5b3/dataset_completo.csv').open(encoding='utf-8') as f:
        for r in csv.DictReader(f):
            key=r['municipio']+'/'+r['ano'];windows[key]['janelas']+=1
            diff=bool(int(r['n_local']))!=bool(int(r['n_utc']))
            if diff:
                windows[key]['presenca_diferente_local_vs_utc']+=1
                windows[key]['ja_null']+=r['target_24h']==''
                windows[key]['classificado']+=r['target_24h']!=''
                amostras.append({k:r[k] for k in ('municipio','data_T','target_24h','motivo','n_local','n_utc')})
    allwall=sum(wall.values(),[]);allliteral=sum(literal.values(),[])
    result=dict(periodo='2022–2024; 2025 excluído',sgif_registos=sum(duplicates.values()),prdf_registos=sum(map(len,pmap.values())),
        ids_sgif_duplicados=sum(n>1 for n in duplicates.values()),ids_prdf_duplicados=sum(len(v)>1 for v in pmap.values()),
        comuns=len(matched),sgif_sem_prdf=len(set(sgif)-set(pmap)),prdf_sem_sgif=len(set(pmap)-set(sgif)),invalidos=invalid,
        relogio=dict(global_=stats(allwall),por_ano={k:stats(v) for k,v in wall.items()}),
        utc_literal_vs_convencao_lisboa=dict(global_=stats(allliteral),por_ano={k:stats(v) for k,v in literal.items()}),
        offsets_prdf=dict(z),eventos_mudam_janela_literal=dict(changed),rastreio=dict(lineage),
        candidatos_por_municipio_ano=dict(candidatos),candidatos_mudam_janela_literal=dict(alteracoes_candidatos),
        janelas_por_municipio_ano={k:dict(v) for k,v in windows.items()},
        timestamp_columns=[k for k in cols if k.lower().startswith('dh')],
        campos_alerta_explicito=[k for k in cols if k.lower() in ('dhalerta','dhprimeiraintervencao')],
        fontes={str(p.relative_to(ROOT)):sha(p) for p in (original,prdf,ROOT/'data/prdf/fogos-metadata.csv',ML/'labels_5b2b.py',ML/'dataset_5b3/dataset_completo.csv')})
    assert (before.st_size,before.st_mtime_ns)==(prdf.stat().st_size,prdf.stat().st_mtime_ns)
    (OUT/'comparacao_temporal.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    chosen=sorted(extremos,key=lambda r:abs(r['diferenca_literal_vs_lisboa_min']),reverse=True)[:15]
    chosen+= [r for r in extremos if r['muda_janela']][:15]
    (OUT/'amostras_temporais.json').write_text(json.dumps(dict(eventos=chosen,janelas=amostras),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='fontes'},ensure_ascii=True,indent=2))

if __name__=='__main__':main()
