"""Sensibilidade experimental multissemente; não escreve estados na aplicação."""
import csv
import hashlib
import itertools
import json
import resource
import sys
import time
from dataclasses import asdict
from datetime import date,datetime,timedelta
from pathlib import Path
import numpy as np
import xarray as xr
import xclim
from xclim.indices.fire import cffwis_indices
sys.path.insert(0,'/workspace/backend')
from services.meteorologia_fwi import (AmostraHorariaFWI,TerritorioFWI,UNIDADES_FWI,preparar_observacao_diaria)
from dados import REGIOES

OUT=Path('/evidencias');INDICES=('ffmc','dmc','dc','isi','bui','fwi')
SEMENTES=list(itertools.product((60.,85.,95.),(2.,6.,150.),(5.,15.,1000.)))
CONV=SEMENTES.index((85.,6.,15.))
ATOL,RTOL=1e-8,1e-10
assert xclim.__version__=='0.62.0'

def guardar(nome,v):
 (OUT/nome).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False,default=str),encoding='utf-8')

def calcular(observacoes,sementes):
 tempos=np.array([np.datetime64(datetime.fromisoformat(o['instante_referencia_utc']).replace(tzinfo=None),'ns') for o in observacoes])
 def serie(k,unidade):
  valores=np.broadcast_to(np.array([o[k] for o in observacoes],dtype=float),(len(sementes),len(observacoes))).copy()
  return xr.DataArray(valores,dims=('semente','time'),coords={'time':tempos},attrs={'units':unidade})
 seeds={k+'0':xr.DataArray([s[i] for s in sementes],dims='semente',attrs={'units':''}) for i,k in enumerate(('ffmc','dmc','dc'))}
 resultado=cffwis_indices(tas=serie('temperatura','degC'),hurs=serie('humidade','%'),sfcWind=serie('vento','km/h'),
  pr=serie('precipitacao_24h','mm/day'),lat=xr.DataArray(observacoes[0]['latitude'],attrs={'units':'degrees_north'}),
  **seeds,initial_start_up=False,season_method=None,overwintering=False,dry_start=None)
 return np.stack([getattr(resultado,k.upper()).transpose('time','semente').values for k in INDICES],axis=-1)

def primeira_estavel(condicao):
 falhas=np.flatnonzero(~condicao)
 i=int(falhas[-1]+1) if len(falhas) else 0
 return i if i<len(condicao) else None

def executar(nome):
 t=time.perf_counter();meta=json.loads((OUT/f'{nome}_recolha.json').read_text());assert meta['estado']=='validado'
 horas=json.loads((OUT/f'{nome}_horas.json').read_text());obs=[]
 for i in range(1826):
  grupo=horas[i*24:(i+1)*24]
  amostras=[AmostraHorariaFWI(datetime.fromisoformat(h['instante_utc']),h['precipitacao_hora'],h['temperatura'],h['humidade'],h['vento']) for h in grupo]
  o=preparar_observacao_diaria(id_regiao=meta['regiao']['id_regiao'],data_referencia=date(2021,10,1)+timedelta(days=i),
   territorio=TerritorioFWI(meta['territorio']),latitude=meta['regiao']['latitude'],amostras=amostras,unidades=UNIDADES_FWI,
   origem='open-meteo-archive-ecmwf-ifs-horario-v1')
  o=asdict(o);o['data_referencia']=o['data_referencia'].isoformat();o['instante_referencia_utc']=o['instante_referencia_utc'].isoformat()
  obs.append(o)
 guardar(f'{nome}_observacoes.json',obs)
 res=[];calculados={}
 for anos in (1,2,3,5):
  selecionadas=[o for o in obs if o['data_referencia']>=f'{2026-anos}-10-01']
  v=calcular(selecionadas,SEMENTES);assert np.isfinite(v).all() and (v>=0).all()
  calculados[anos]=v
  np.savez_compressed(OUT/f'{nome}_{anos}anos.npz',indices=np.array(INDICES),sementes=SEMENTES,
    datas=[o['data_referencia'] for o in selecionadas],valores=v)
  spread=np.ptp(v,axis=1);escala=np.max(np.abs(v),axis=1)
  relativo=np.divide(spread,escala,out=np.zeros_like(spread),where=escala!=0)
  ok=spread<=ATOL+RTOL*escala
  exact=spread==0
  metricas={}
  for j,k in enumerate(INDICES):
   def instante(mask):
    idx=primeira_estavel(mask)
    return None if idx is None else dict(dia=idx+1,data=selecionadas[idx]['data_referencia'],dias_seguimento=len(v)-idx-1)
   metricas[k]=dict(max_diferenca_absoluta=float(spread[:,j].max()),max_diferenca_relativa=float(relativo[:,j].max()),
    diferenca_final_absoluta=float(spread[-1,j]),diferenca_final_relativa=float(relativo[-1,j]),
    convergencia_numerica=instante(ok[:,j]),igualdade_exata=instante(exact[:,j]))
  with (OUT/f'{nome}_{anos}anos_dispersao.csv').open('w',newline='') as f:
   w=csv.writer(f,lineterminator='\n');w.writerow(['data']+[k+'_abs' for k in INDICES]+[k+'_rel' for k in INDICES])
   for d,a,r in zip(selecionadas,spread,relativo):w.writerow([d['data_referencia'],*a,*r])
  resumo=dict(regiao=nome,anos=anos,dias=len(v),semente_convencional=CONV,metricas=metricas,
    janela_inicial=selecionadas[0]['data_referencia'],janela_final=selecionadas[-1]['data_referencia'])
  res.append(resumo)
 # Regressão contra trajetória já persistida, sem recolher/calcular novamente pelo fluxo de BD.
 antigos=json.loads((Path('/workspace/experiments')/REGIOES[nome]/f'{nome}_dias.json').read_text())
 usados=[o for o in obs if o['data_referencia']>=antigos[0]['data_referencia']]
 reg=calculados[1][:,CONV,:] if len(antigos)==365 else calcular(usados,[(85.,6.,15.)])[:,0,:]
 ref=np.array([[d[k] for k in INDICES] for d in antigos])
 assert np.allclose(reg,ref,atol=ATOL,rtol=RTOL),(nome,np.max(abs(reg-ref)))
 horizonte={str(a):{k:float(calculados[a][-1,CONV,j]-calculados[5][-1,CONV,j]) for j,k in enumerate(INDICES)} for a in (1,2,3)}
 guardar(f'{nome}_convergencia.json',dict(sementes=SEMENTES,regressao_existente=True,erro_regressao=float(np.max(abs(reg-ref))),
  resultados=res,diferenca_final_vs_5anos=horizonte,segundos=time.perf_counter()-t,pico_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))
 print(nome,'concluído',round(time.perf_counter()-t,2),'s',flush=True)

if __name__=='__main__':
 guardar('politica_ensaio.json',dict(sementes=SEMENTES,convencional=CONV,atol=ATOL,rtol=RTOL,
  relativo='(max-min)/max(abs), zero quando todos são zero',
  limiar='Tolerância numérica anterior, NÃO limiar material de decisão operacional.',
  aviso='Nenhuma promoção; amostra finita de sementes, sem demonstração de todas as condições iniciais possíveis.'))
 for nome in REGIOES:executar(nome)
