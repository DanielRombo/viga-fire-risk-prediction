"""Prova retrospetiva isolada: reutiliza horas reais da Fase 8, sem downloads/BD."""
import csv
import hashlib
import json
import sys
import time
from collections import Counter
from dataclasses import asdict
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
import numpy as np

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'backend'))
sys.path.insert(0,str(REPO/'experiments/fwi_fase8'))
from convergencia import calcular
from services.meteorologia_fwi import AmostraHorariaFWI,TerritorioFWI,UNIDADES_FWI,preparar_observacao_diaria
from obter_5b2b import ROOT,sha

def main():
    inicio=time.perf_counter();fontes=REPO/'experiments/fwi_fase8/evidencias'
    labels={}
    with (ROOT/'labels.csv').open(encoding='utf-8') as f:
        for r in csv.DictReader(f):labels[r['municipio'],r['data_T'][:10]]=r
    resultado=[];manifesto=[]
    for cod,nome in [('1106','Lisboa'),('0805','Faro'),('1714','Vila Real')]:
        meta=json.loads((fontes/f'{nome}_recolha.json').read_text(encoding='utf-8'))
        bruto=fontes/f'{nome}_extensao_resposta.json'
        assert sha(bruto)==meta['sha256']
        raw=json.loads(bruto.read_text(encoding='utf-8'));assert raw['utc_offset_seconds']==0
        assert raw['hourly_units']=={'time':'iso8601','temperature_2m':'°C','relative_humidity_2m':'%',
                                     'wind_speed_10m':'km/h','precipitation':'mm'}
        params=meta['parametros'];assert params['models']=='ecmwf_ifs'
        horas=json.loads((fontes/f'{nome}_horas.json').read_text(encoding='utf-8'))
        hraw=raw['hourly'];lookup={t:i for i,t in enumerate(hraw['time'])};assert len(lookup)==len(hraw['time'])
        obs=[]
        for k in range(730):
            d=date(2021,10,1)+timedelta(days=k);hs=horas[24*k:24*(k+1)]
            assert len(hs)==24
            for h in hs:
                t=datetime.fromisoformat(h['instante_utc']);i=lookup[t.strftime('%Y-%m-%dT%H:%M')]
                assert (h['latitude_consultada'],h['longitude_consultada'])==(params['latitude'],params['longitude'])
                for hk,rk in [('temperatura','temperature_2m'),('humidade','relative_humidity_2m'),('vento','wind_speed_10m'),('precipitacao_hora','precipitation')]:
                    assert h[hk]==hraw[rk][i] and np.isfinite(h[hk])
            o=preparar_observacao_diaria(id_regiao=meta['regiao']['id_regiao'],data_referencia=d,
                territorio=TerritorioFWI.CONTINENTE,latitude=params['latitude'],
                amostras=[AmostraHorariaFWI(datetime.fromisoformat(h['instante_utc']),h['precipitacao_hora'],h['temperatura'],h['humidade'],h['vento']) for h in hs],
                unidades=UNIDADES_FWI,origem='open-meteo-archive-ecmwf-ifs-horario-v1')
            row=asdict(o);row['data_referencia']=d.isoformat();row['instante_referencia_utc']=o.instante_referencia_utc.isoformat();obs.append(row)
        # Prefixo causal: nenhuma observação posterior a setembro de 2023 entra no cálculo.
        v=calcular(obs,[(85.,6.,15.)])[:,0,:];assert np.isfinite(v).all() and (v>=0).all()
        antigo=np.load(fontes/f'{nome}_5anos.npz');idx=np.flatnonzero(np.all(antigo['sementes']==[85,6,15],axis=1)).item()
        assert np.allclose(v,antigo['valores'][:730,idx,:],atol=1e-8,rtol=1e-10)
        for k,o in enumerate(obs):
            if o['data_referencia']<'2023-04-01':continue
            lab=labels[cod,o['data_referencia']];t=datetime.fromisoformat(lab['data_T'])
            assert datetime.fromisoformat(o['instante_referencia_utc'])<t
            row={**lab,**{campo:o[campo] for campo in ('temperatura','humidade','vento','precipitacao_24h')},
                 **dict(zip(('ffmc','dmc','dc','isi','bui','fwi'),map(float,v[k]))),
                 'mes':t.month,'dia_do_ano':t.timetuple().tm_yday,'instante_referencia_utc':o['instante_referencia_utc'],
                 'available_at_historico':'','tipo_estudo':'retrospetivo','estado_fwi':'reconstruido',
                 'semente':'85/6/15 em 2021-09-30','weather_sha256':meta['sha256']}
            resultado.append(row)
        manifesto.append(dict(municipio=cod,nome=nome,source_sha256=sha(bruto),horas_sha256=sha(fontes/f'{nome}_horas.json'),
           horas_validadas=730*24,dias_calculados=730,erro_vs_fase8=float(np.max(abs(v-antigo['valores'][:730,idx,:]))),
           latitude=params['latitude'],longitude=params['longitude']))
    with (ROOT/'dataset_piloto.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(resultado[0]));w.writeheader();w.writerows(resultado)
    c=Counter(r['target_24h'] or 'null' for r in resultado)
    resumo=dict(linhas=len(resultado),contagens=dict(c),prevalencia=c['1']/(c['1']+c['0']),
                municipios=manifesto,segundos=time.perf_counter()-inicio,chamadas_externas=0,
                nota='Sem leakage por valid_time; disponibilidade operacional em T não demonstrada.')
    (ROOT/'prova_resumo.json').write_text(json.dumps(resumo,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(resumo,ensure_ascii=True))

if __name__=='__main__':main()
