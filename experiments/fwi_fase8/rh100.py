"""Impacto isolado nos 18 dias: RH real versus ajuste específico do wrapper R."""
import json
from pathlib import Path
import numpy as np
from convergencia import calcular,INDICES,ATOL,RTOL,guardar
BASE=Path('/workspace/experiments/fwi_fase7/evidencias')
div=json.loads((BASE/'divergencias.json').read_text())['divergencias']
casos=sorted({(r['regiao'],r['data']) for r in div})
internos=json.loads((BASE/'diagnostico_rh100.json').read_text())['comparacoes']
linhas=[]
for nome,data in casos:
 dias=json.loads((BASE/'365'/f'{nome}_dias.json').read_text());d=next(d for d in dias if d['data_referencia']==data)
 o=d['observacao'];assert o['humidade']==100
 seed=[tuple(d['estado_anterior'][k] for k in INDICES[:3])]
 real=calcular([o],seed)[0,0,:];ajustado=calcular([{**o,'humidade':99.9999}],seed)[0,0,:]
 publicos=json.loads((BASE/'365'/f'{nome}_comparacao.json').read_text())['comparacoes']
 for j,k in enumerate(INDICES):
  pub=next(c['referencia'] for c in publicos if c['data']==data and c['indice']==k)
  interno=next(c['r_interno_rh100'] for c in internos if c['regiao']==nome and c['data']==data and c['indice']==k)
  assert np.isclose(real[j],interno,atol=ATOL,rtol=RTOL)
  assert np.isclose(ajustado[j],pub,atol=ATOL,rtol=RTOL)
  delta=float(ajustado[j]-real[j])
  linhas.append(dict(regiao=nome,data=data,indice=k,xclim_rh100=float(real[j]),xclim_rh999999=float(ajustado[j]),
   cffdrs_publico=pub,cffdrs_interno_rh100=interno,diferenca_assinada=delta,diferenca_absoluta=abs(delta),
   diferenca_relativa_a_rh100=abs(delta)/abs(real[j]) if real[j] else None,
   denominador_zero=bool(real[j]==0),inputs=o,estado_anterior=d['estado_anterior']))
resumo={}
for k in INDICES:
 rows=[r for r in linhas if r['indice']==k]
 resumo[k]=dict(max_abs=max(r['diferenca_absoluta'] for r in rows),mediana_abs=float(np.median([r['diferenca_absoluta'] for r in rows])),
  max_rel_nao_zero=max([r['diferenca_relativa_a_rh100'] for r in rows if not r['denominador_zero']] or [0]),
  denominadores_zero=sum(r['denominador_zero'] for r in rows),
  comparacoes_publico_fora_tolerancia=sum(not np.isclose(r['xclim_rh100'],r['cffdrs_publico'],atol=ATOL,rtol=RTOL) for r in rows))
guardar('rh100_impacto.json',dict(casos=len(casos),regioes=len({n for n,d in casos}),atol=ATOL,rtol=RTOL,
 politica_recomendada='Manter RH real igual a 100%; não clamping implícito.',
 resumo=resumo,comparacoes=linhas,confirmacao='RH=100 coincide com R interno; RH=99,9999 coincide com R público. Tolerâncias inalteradas.'))
print(json.dumps(resumo,ensure_ascii=False,indent=2))
