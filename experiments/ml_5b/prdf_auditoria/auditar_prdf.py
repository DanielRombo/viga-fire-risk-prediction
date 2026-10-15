"""Auditoria streaming/read-only. Não importa módulos do VIGA ou modelos ML."""
import argparse
import csv
import hashlib
import json
import math
import os
import platform
import shutil
import sqlite3
import tempfile
import time
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone,date
from pathlib import Path
from zoneinfo import ZoneInfo

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2];DATA=ROOT/'data/prdf';ML=OUT.parent
NULLS={'','NA','NULL','NaN','nan','None'}

def guardar(n,o):
    (OUT/n).write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def csvout(n,rows):
    rows=list(rows)
    if not rows:return
    with (OUT/n).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def ro(name):
    c=sqlite3.connect((DATA/name).resolve().as_uri()+'?mode=ro',uri=True)
    c.execute('PRAGMA query_only=ON');c.execute('PRAGMA temp_store=FILE');return c

def dt(s):
    if s is None or s in NULLS:return None
    try:return datetime.fromisoformat(s.replace('Z','+00:00')).replace(tzinfo=None)
    except (ValueError,TypeError):return None

def epoch(s):
    d=dt(s);return d.replace(tzinfo=timezone.utc).timestamp() if d else None

def rural(r):
    if r['Tipo'] not in ('Florestal','Agrícola'):return 'tipo_nao_rural'
    if r.get('Reacendimento_IncendioPai') or r.get('TipoCausa')=='Reacendimento' or r.get('CodCausa')==711:
        return 'reacendimento'
    if not dt(r.get('DHInicio')):return 'timestamp_invalido'
    return 'potencial_nova_ocorrencia'

def municipio(ine):
    try:
        s=str(int(float(ine))).zfill(6)
        return s[:4] if len(s)==6 else ''
    except (ValueError,TypeError):return ''

def fogos():
    c=ro('fogos.gpkg');c.row_factory=sqlite3.Row
    columns=[dict(r) for r in c.execute('PRAGMA table_info(Fogos)')]
    types=Counter();causes=Counter();years=Counter();months=Counter();mun=Counter();dist=Counter();nulls=Counter();temporal=Counter();geo=Counter();tax=Counter();days=set();events=[];near=Counter();same=Counter();last={}
    fields=['Codigo','CodigoSado','Ano','Tipo','DHInicio','DH1Intervencao','DHResolucao','DHConclusao','DHFim','Concelho','Distrito','INE','Lat_4326','Lon_4326','CodCausa','TipoCausa','Reacendimento_IncendioPai']
    minimo=maximo=None;count=0
    for raw in c.execute('SELECT '+','.join(fields)+' FROM Fogos ORDER BY DHInicio'):
        r=dict(raw);count+=1
        for k,v in r.items():nulls[k]+=v is None or v==''
        t=dt(r['DHInicio']);y=int(r['Ano']) if r['Ano'] is not None else None
        if t:
            years[str(t.year)]+=1;months[t.year,t.month]+=1
            minimo=t if minimo is None else min(minimo,t);maximo=t if maximo is None else max(maximo,t)
            temporal['ano_diverge']+=y!=t.year
            temporal['inicio_com_Z']+=str(r['DHInicio']).endswith('Z')
            for k in ('DH1Intervencao','DHResolucao','DHConclusao','DHFim'):
                other=dt(r[k]);temporal[k+'_parse_invalido']+=bool(r[k]) and other is None
                if other:
                    if k=='DH1Intervencao':temporal['intervencao_so_data']+=len(r[k])==10
                    temporal[k+'_anterior_inicio']+=other<t
                    temporal[k+'_dia_anterior_inicio']+=other.date()<t.date()
            cod=municipio(r['INE']);lat=r['Lat_4326'];lon=r['Lon_4326']
            validcoord=lat is not None and lon is not None and math.isfinite(lat) and math.isfinite(lon) and 36.8<=lat<=42.2 and -9.6<=lon<=-6
            geo['coordenadas_invalidas_ou_fora_envelope']+=not validcoord
            geo['codigo_municipal_ausente']+=not cod
            if y==2025:
                days.add(t.date());types[r['Tipo'] or 'null']+=1;causes[r['TipoCausa'] or 'null']+=1;tax[rural(r)]+=1
                mun[cod,r['Concelho'] or '',t.month]+=1;dist[r['Distrito'] or 'null']+=1
                events.append(dict(**r,municipio=cod,classe=rural(r)))
                same[cod,str(t),lat,lon]+=1
                if validcoord:
                    key=(round(lat,2),round(lon,2));prev=last.get(key)
                    if prev and (t-prev).total_seconds()<=600:near['pares_mesma_celula_10min']+=1
                    last[key]=t
        else:temporal['inicio_invalido']+=1
        if count%200000==0:print('Fogos',count,flush=True)
    duplicate={}
    for k in ('Codigo','CodigoSado'):
        q=f'SELECT COUNT(*),COALESCE(SUM(n-1),0) FROM (SELECT COUNT(*) n FROM Fogos WHERE "{k}" IS NOT NULL AND "{k}"<>\'\' GROUP BY "{k}" HAVING COUNT(*)>1)'
        duplicate[k]=list(c.execute(q).fetchone())
    csvout('fogos_anuais_mensais.csv',[dict(ano=y,mes=m,n=n) for (y,m),n in sorted(months.items())])
    csvout('fogos_2025_municipais.csv',[dict(municipio=cod,nome=nome,mes=m,n=n) for (cod,nome,m),n in sorted(mun.items())])
    # Apenas agregados ficam em disco; lista de 8252 eventos é usada no processo e não copiada.
    out=dict(n=count,periodo=[str(minimo),str(maximo)],schemas=columns,anos=dict(years),nulls=dict(nulls),temporal=dict(temporal),territorio=dict(geo),duplicados=duplicate,
        ano2025=dict(n=len(events),min=min(e['DHInicio'] for e in events),max=max(e['DHInicio'] for e in events),meses={str(m):months[2025,m] for m in range(1,13)},
            tipos=dict(types),causas=dict(causes),taxonomia=dict(tax),distritos=dict(dist),municipios=len({e['municipio'] for e in events}),
            dias_sem_registo=[str(date(2025,1,1)+timedelta(days=i)) for i in range(365) if date(2025,1,1)+timedelta(days=i) not in days],
            grupos_espaco_tempo_duplicados=sum(v>1 for v in same.values()),near=dict(near)))
    guardar('fogos.json',out);c.close()

def firemap():
    c=ro('fogos.gpkg');codes={};dups=set()
    for code,begin,end,ine,y in c.execute('SELECT Codigo,DHInicio,DHFim,INE,Ano FROM Fogos'):
        if code in codes:dups.add(code)
        codes[code]=(epoch(begin),epoch(end),municipio(ine),int(y) if y else None)
    c.close();return codes,dups

def meteo():
    codes,dups=firemap();counts=Counter();nulls=Counter();years=Counter();delta=Counter();firestats={};globalmin=globalmax=None;match=Counter();mins=[];n=0
    assert shutil.disk_usage(tempfile.gettempdir()).free>3_000_000_000
    fd,path=tempfile.mkstemp(prefix='viga_prdf_meteo_',suffix='.sqlite');os.close(fd)
    conn=sqlite3.connect(path);conn.execute('PRAGMA journal_mode=OFF');conn.execute('PRAGMA synchronous=OFF');conn.execute('CREATE TABLE keys(id TEXT,code TEXT,t TEXT)')
    try:
        with (DATA/'METEO.csv').open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f);schema=reader.fieldnames;batch=[]
            for r in reader:
                n+=1;code=r['codigo'];counts[code]+=1;t=epoch(r['DHMeteo']);batch.append((r['ID'],code,r['DHMeteo']))
                for k,v in r.items():nulls[k]+=v in NULLS
                if t is not None:
                    years[r['DHMeteo'][:4]]+=1;globalmin=t if globalmin is None else min(globalmin,t);globalmax=t if globalmax is None else max(globalmax,t)
                else:match['timestamp_invalido']+=1
                event=codes.get(code)
                if event and t is not None and event[0] is not None:
                    match['linhas_com_fogo']+=1;dif=(t-event[0])/3600
                    bucket='antes' if dif<0 else 'no_alerta' if dif==0 else 'depois'
                    delta[bucket]+=1;delta['depois_24h']+=dif>24;delta['depois_48h']+=dif>48
                    if event[1] is not None:delta['apos_extincao']+=t>event[1]
                    if not mins:mins=[dif,dif]
                    else:mins=[min(mins[0],dif),max(mins[1],dif)]
                    if event[3]==2025:
                        stat=firestats.setdefault(code,[0,t,t,0,0,0,0])
                        stat[0]+=1;stat[1]=min(stat[1],t);stat[2]=max(stat[2],t);stat[3]+=dif<0;stat[4]+=dif==0;stat[5]+=dif>0;stat[6]+=any(r[k] in NULLS for k in ('T','HR','V','Prec','FFMC','DMC','DC','ISI','BUI','FWI'))
                else:match['linhas_sem_fogo_ou_inicio']+=1
                if len(batch)==25000:
                    conn.executemany('INSERT INTO keys VALUES (?,?,?)',batch);batch=[]
                if n%500000==0:print('METEO',n,flush=True)
            if batch:conn.executemany('INSERT INTO keys VALUES (?,?,?)',batch)
        conn.commit();duplicates={}
        for key in ('id','code,t'):
            duplicates[key]=list(conn.execute(f'SELECT COUNT(*),COALESCE(SUM(n-1),0) FROM (SELECT COUNT(*) n FROM keys GROUP BY {key} HAVING COUNT(*)>1)').fetchone())
        e2025={k:v for k,v in codes.items() if v[3]==2025}
        aggregates=defaultdict(Counter)
        for code,e in e2025.items():
            month=datetime.fromtimestamp(e[0],timezone.utc).month if e[0] else 0;key=(e[2],month);a=aggregates[key];a['fogos']+=1
            if code in firestats:
                s=firestats[code];a['com_meteo']+=1;a['linhas']+=s[0];a['antes']+=s[3];a['no_alerta']+=s[4];a['depois']+=s[5];a['linhas_incompletas']+=s[6]
            else:a['sem_meteo']+=1
        csvout('meteo_2025_cobertura.csv',[dict(municipio=c,mes=m,**{k:a[k] for k in ('fogos','com_meteo','sem_meteo','linhas','antes','no_alerta','depois','linhas_incompletas')}) for (c,m),a in sorted(aggregates.items())])
        lengths=[s[0] for s in firestats.values()];durations=[(s[2]-s[1])/3600 for s in firestats.values()]
        guardar('meteo.json',dict(n=n,schema=schema,tipos='CSV textual; timestamps ISO e medidas numéricas conforme inspeção',nulls=dict(nulls),anos=dict(years),
            periodo=[str(datetime.fromtimestamp(x,timezone.utc)) for x in (globalmin,globalmax)],
            codigos=len(counts),fogos_com_meteo=len(set(codes)&set(counts)),fogos_sem_meteo=len(set(codes)-set(counts)),codigos_meteo_sem_fogo=len(set(counts)-set(codes)),
            chaves_fogo_ambiguas=len(dups),match=dict(match),duplicados=duplicates,delta_horas=dict(contagens=dict(delta),minmax=mins),
            ano2025=dict(fogos=len(e2025),com_meteo=len(firestats),sem_meteo=len(e2025)-len(firestats),linhas=sum(lengths),
              linhas_por_fogo_minmax=[min(lengths),max(lengths)] if lengths else None,duracao_horas_minmax=[min(durations),max(durations)] if durations else None),
            leitura='csv.DictReader incremental; lotes SQLite temporários 25000; comparação de relógios sem inferir fuso'))
    finally:
        conn.close();Path(path).unlink()

def frp_timestamp(r):
    try:
        sec=0 if r.get('segundo') in NULLS or r.get('segundo') is None else int(float(r['segundo']))
        return datetime(*(int(float(r[k])) for k in ('ano','mes','dia','hora','minuto')),sec)
    except (ValueError,TypeError):return None

def frp():
    counts=Counter();years=Counter();nulls=Counter();ids=Counter();bad=0;minimo=maximo=None
    with (DATA/'FRP.csv').open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);schema=reader.fieldnames
        for r in reader:
            counts['n']+=1;ids[r['ID']]+=1
            for k,v in r.items():nulls[k]+=v in NULLS
            t=frp_timestamp(r)
            if not t:counts['componentes_invalidos']+=1;continue
            years[t.year]+=1;minimo=t if minimo is None else min(minimo,t);maximo=t if maximo is None else max(maximo,t)
            counts['segundo_assumido_zero']+=r.get('segundo') in NULLS
            old=dt(r['ACQTIME']);counts['acqtime_data_diverge']+=not old or old.date()!=t.date()
            try:
                lat=float(r['lat']);lon=float(r['lon']);v=float(r['FRP'])
                counts['coordenada_invalida']+=not(math.isfinite(lat) and math.isfinite(lon) and -90<=lat<=90 and -180<=lon<=180)
                counts['frp_negativo_ou_nao_finito']+=not math.isfinite(v) or v<0
            except ValueError:bad+=1
    guardar('frp.json',dict(schema=schema,contagens=dict(counts),nulls=dict(nulls),anos=dict(years),periodo=[str(minimo),str(maximo)],
        ids_duplicados=sum(v>1 for v in ids.values()),numeros_invalidos=bad,
        cruzamento_2025='Não há deteções 2025; a ausência é falta de cobertura da fonte, nunca negativo.' if not years[2025] else 'Requer cruzamento espacial',
        tolerancias=[dict(metros=2000,horas=24),dict(metros=5000,horas=48)]))

def pba():
    c=ro('PBA.gpkg');c.row_factory=sqlite3.Row;codes,_=firemap();stats=Counter();years=Counter();sources=Counter();nulls=Counter();states=Counter();matched=set();n=0;exact=Counter();errors=Counter()
    fields=['fid','Ano','Cod_SGIF','Cod_ANEPC','DH_Inicio','DH_Fim','PI_DICOFRE','PI_Conc','AreaHaPoly','Estado','Poly_Fonte','BEST_Codigo','CODIGOSGIF_ESTIMADO']
    for raw in c.execute('SELECT '+','.join(fields)+' FROM PBA'):
        r=dict(raw);n+=1;years[r['Ano']]+=1;states[r['Estado'] or 'null']+=1;sources[r['Poly_Fonte'] or 'null']+=1
        for k,v in r.items():nulls[k]+=v is None or v==''
        code=r['Cod_SGIF'];event=codes.get(code)
        if event:
            stats['perimetros_match_sgif']+=1;matched.add(code);exact[code]+=1
            start=epoch(r['DH_Inicio'])
            if start is not None and event[0] is not None:errors['inicio_diverge']+=start!=event[0]
            if r['PI_DICOFRE']:errors['municipio_diverge']+=str(r['PI_DICOFRE']).zfill(6)[:4]!=event[2]
            if event[3]==2025:stats['perimetros_match_fogos2025']+=1
        else:stats['perimetros_sem_match_sgif']+=1
        if r['DH_Inicio'] and r['DH_Fim'] and epoch(r['DH_Inicio']) is not None and epoch(r['DH_Fim']) is not None:errors['fim_antes_inicio']+=epoch(r['DH_Fim'])<epoch(r['DH_Inicio'])
        if r['AreaHaPoly'] is not None:errors['area_negativa']+=r['AreaHaPoly']<0
    guardar('pba.json',dict(n=n,anos=dict(years),schema=[dict(r) for r in c.execute('PRAGMA table_info(PBA)')],
        estados=dict(states),fontes=dict(sources),nulls=dict(nulls),cruzamento=dict(stats),conflitos=dict(errors),
        fogos_match_exato=len(matched),fogos_sem_perimetro=len(set(codes)-matched),ids_com_varios_perimetros=sum(v>1 for v in exact.values()),
        fogos2025_com_perimetro=sum(codes[k][3]==2025 for k in matched),
        nota='Cod_SGIF primário; BEST_Codigo/estimados não promovidos a matches exatos. Ausência de perímetro não exclui fogo.'))

def main():
    p=argparse.ArgumentParser();p.add_argument('fase',choices=['fogos','meteo','frp','pba']);a=p.parse_args();start=time.perf_counter()
    globals()[a.fase]()
    guardar(a.fase+'_execucao.json',dict(segundos=time.perf_counter()-start,python=platform.python_version(),sqlite=sqlite3.sqlite_version,modo='read-only originais',comando=f'python -B experiments/ml_5b/prdf_auditoria/auditar_prdf.py {a.fase}'))

if __name__=='__main__':main()
