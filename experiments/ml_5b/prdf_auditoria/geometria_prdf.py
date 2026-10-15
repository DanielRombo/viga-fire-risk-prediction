"""Geometria em streaming; apenas subconjuntos 2025 em índices espaciais."""
import csv
import hashlib
import json
import math
import struct
from collections import Counter
from datetime import datetime,timezone
import numpy as np
from scipy.spatial import cKDTree
from shapely import wkb
from shapely.geometry import Point,shape
from shapely.strtree import STRtree
from auditar_prdf import OUT,ML,DATA,ro,guardar,dt,rural,municipio,frp_timestamp

def geom(blob):
    if blob is None:return None
    if bytes(blob[:2])!=b'GP':raise ValueError('Não é GeoPackage')
    envelope=(blob[3]>>1)&7;n={0:0,1:4,2:6,3:6,4:8}[envelope]
    return wkb.loads(bytes(blob[8+8*n:]))

def hav(lat,lon,la,lo):
    a=np.radians(la-lat);b=np.radians(lo-lon)
    return 6371000*2*np.arcsin(np.minimum(1,np.sqrt(np.sin(a/2)**2+np.cos(np.radians(lat))*np.cos(np.radians(la))*np.sin(b/2)**2)))

def main():
    stats={};polys=[];ids=[];dups=Counter()
    for filename,table in [('fogos.gpkg','Fogos'),('PBA.gpkg','PBA')]:
        c=ro(filename);counts=Counter();gtypes=Counter()
        for fid,ano,blob in c.execute(f'SELECT fid,Ano,geom FROM {table}'):
            counts['total']+=1
            try:g=geom(blob)
            except Exception:counts['erro_wkb']+=1;continue
            if g is None:counts['null']+=1;continue
            counts['vazia']+=g.is_empty;counts['invalida']+=not g.is_valid;gtypes[g.geom_type]+=1
            if table=='PBA':
                dups[hashlib.sha256(blob).hexdigest()]+=1
                if ano==2025 and g.is_valid and not g.is_empty:polys.append(g);ids.append(fid)
        stats[table]=dict(contagens=dict(counts),tipos=dict(gtypes));c.close()
    stats['PBA']['geometrias_identicas_grupos']=sum(v>1 for v in dups.values())
    tree=STRtree(polys);over=Counter();examples=[]
    for i,g in enumerate(polys):
        for j in tree.query(g,predicate='intersects'):
            j=int(j)
            if j<=i:continue
            area=g.intersection(polys[j]).area
            if area>0:
                over['pares_area_sobreposta']+=1
                if area/min(g.area,polys[j].area)>.1:
                    over['sobreposicao_maior_10pct_menor']+=1
                    if len(examples)<10:examples.append(dict(fid1=ids[i],fid2=ids[j],area_m2=area))
    stats['PBA']['sobreposicao2025']=dict(over);stats['PBA']['amostras']=examples
    c=ro('fogos.gpkg');c.row_factory=__import__('sqlite3').Row
    fires=[dict(r) for r in c.execute('SELECT Codigo,DHInicio,Tipo,TipoCausa,CodCausa,Reacendimento_IncendioPai,INE,Lat_4326,Lon_4326,Concelho,x_3763,y_3763 FROM Fogos WHERE Ano=2025')];c.close()
    ps={}
    for cod in ('1106','0805','1714'):
        ps[cod]=shape(json.loads((ML/f'fontes_5b2/dgt_{cod}.bin').read_text())['geometry'])
    territory=[]
    for f in fires:
        point=Point(f['Lon_4326'],f['Lat_4326']);inside=[cod for cod,p in ps.items() if p.covers(point)];code=municipio(f['INE'])
        if code in ps or inside:
            territory.append(dict(codigo=f['Codigo'],municipio=code,municipios_poligono='|'.join(inside),coerente=code in inside))
    from auditar_prdf import csvout
    csvout('territorio_2025_amostra.csv',territory)
    stats['territorio2025']=dict(coerentes=sum(r['coerente'] for r in territory),conflitos=sum(not r['coerente'] for r in territory),nota='DGT CAOP2025 apenas três municípios; não associação exata nacional.')
    # FRP apenas 2025; não é necessária a matriz completa de distâncias.
    detections=[]
    with (DATA/'FRP.csv').open(encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if r['ano']!='2025':continue
            t=frp_timestamp(r)
            if t:detections.append((float(r['lat']),float(r['lon']),t.replace(tzinfo=timezone.utc).timestamp()))
    a=np.asarray(detections);tree=cKDTree(np.c_[a[:,1]*85000,a[:,0]*111000]);results=[]
    for radius,hours in [(2000,24),(5000,48)]:
        ct=Counter();sample=[]
        for f in fires:
            if rural(f)!='potencial_nova_ocorrencia':continue
            ct['potenciais_fogos']+=1;lat=f['Lat_4326'];lon=f['Lon_4326']
            nearby=tree.query_ball_point([lon*85000,lat*111000],radius*1.15)
            t=dt(f['DHInicio']).replace(tzinfo=timezone.utc).timestamp()
            idx=np.asarray(nearby,dtype=int)
            if len(idx):
                matches=(hav(lat,lon,a[idx,0],a[idx,1])<=radius)&(np.abs(a[idx,2]-t)<=hours*3600)
                n=int(matches.sum())
            else:n=0
            ct['com_frp']+=n>0;ct['sem_frp']+=n==0;ct['multiplos_frp']+=n>1;ct['pares']+=n
            if n and len(sample)<10:sample.append(dict(codigo=f['Codigo'],deteccoes=n))
        results.append(dict(raio_m=radius,janela_horas_simetrica=hours,contagens=dict(ct),amostras=sample))
    guardar('geometria.json',stats);guardar('frp_cruzamento.json',dict(deteccoes2025=len(a),resultados=results,
        nota='Distância haversine; relógios comparados sem prova independente de fuso; associação auxiliar não confirma identidade/ignição, ausência nunca negativo.'))
    print(stats['territorio2025']);print(results)

if __name__=='__main__':main()
