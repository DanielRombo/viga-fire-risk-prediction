"""Recolhe só a extensão em falta; nenhuma ligação à BD ou ao scheduler."""
import asyncio
import hashlib
import json
import sys
import time
from datetime import datetime,date,timedelta,timezone
from pathlib import Path
sys.path.insert(0,'/workspace/backend')
from services.open_meteo_historico_fwi import recolher_historico_fwi
from services.meteorologia_fwi import instante_referencia,TerritorioFWI
from dataclasses import asdict

ROOT=Path('/workspace');OUT=Path('/evidencias')
REGIOES={'Lisboa':'fwi_fase6/evidencias', 'Faro':'fwi_fase7/evidencias/365',
 'Vila Real':'fwi_fase6/evidencias','Castelo Branco':'fwi_fase7/evidencias/365',
 'Évora':'fwi_fase7/evidencias/365','Funchal':'fwi_fase6/evidencias',
 'Ponta Delgada':'fwi_fase6/evidencias'}

def guardar(nome,dados):
 (OUT/nome).write_text(json.dumps(dados,ensure_ascii=False,indent=2,default=str,allow_nan=False),encoding='utf-8')

async def obter(nome,pasta):
 import httpx
 destino=OUT/f'{nome}_horas.json'
 if destino.exists():
  print('Reutilizado sem nova chamada:',nome,flush=True);return
 base=ROOT/'experiments'/pasta
 meta=json.loads((base/f'{nome}_recolha.json').read_text())
 bruto=(base/f'{nome}_resposta.json').read_bytes()
 assert hashlib.sha256(bruto).hexdigest()==meta['sha256']
 existentes=json.loads((base/f'{nome}_dias.json').read_text())
 horas_antigas=[h for d in existentes for h in d['horas']]
 territorio=TerritorioFWI(existentes[0]['observacao']['territorio'])
 inicio=instante_referencia(date(2021,10,1),territorio)-timedelta(hours=23)
 fim=datetime.fromisoformat(horas_antigas[0]['instante_utc'])-timedelta(hours=1)
 regiao=meta['regiao'];agora=datetime.now(timezone.utc)
 evidencia=dict(regiao=regiao,territorio=territorio.value,inicio=inicio,fim=fim,
  horas_reutilizadas=len(horas_antigas),origem_reutilizada=str(base.relative_to(ROOT)),
  sha256_resposta_reutilizada=meta['sha256'],ingerido_em=agora,chamadas=0,retries=0)
 class Cliente:
  async def get(self,url,params):
   evidencia.update(url=url,parametros=params);evidencia['chamadas']+=1
   async with httpx.AsyncClient(timeout=httpx.Timeout(90,connect=10)) as c:r=await c.get(url,params=params)
   b=r.content;(OUT/f'{nome}_extensao_resposta.json').write_bytes(b)
   evidencia.update(status_http=r.status_code,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
   return r
 t=time.perf_counter()
 try:
  novas=await recolher_historico_fwi(regiao['latitude'],regiao['longitude'],inicio,fim,agora=agora,cliente=Cliente())
  todas=[asdict(h) for h in novas]+horas_antigas
  for h in todas:
   for k in ('instante_utc','ingerido_em'):
    if isinstance(h[k],datetime):h[k]=h[k].isoformat()
  assert len(todas)==1826*24
  for i,h in enumerate(todas):
   assert h['qualidade']=='valido' and not h['problemas'],(nome,h)
   assert datetime.fromisoformat(h['instante_utc'])==inicio+timedelta(hours=i)
   assert (h['latitude_consultada'],h['longitude_consultada'])==(regiao['latitude'],regiao['longitude'])
  evidencia.update(estado='validado',horas_novas=len(novas),horas_total=len(todas))
  guardar(f'{nome}_horas.json',todas)
 except Exception as e:
  evidencia.update(estado='bloqueado',erro=repr(e));raise
 finally:
  evidencia['segundos']=time.perf_counter()-t;guardar(f'{nome}_recolha.json',evidencia)
 print(nome,evidencia['horas_novas'],'novas,',len(horas_antigas),'reutilizadas',flush=True)

async def main():
 for n,p in REGIOES.items():await obter(n,p)

if __name__=='__main__':asyncio.run(main())
