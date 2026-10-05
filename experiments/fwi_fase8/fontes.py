"""Preserva fontes primárias consultadas, incluindo respostas não disponíveis."""
import hashlib,json
from pathlib import Path
import httpx
OUT=Path('/evidencias/fontes');OUT.mkdir(exist_ok=True)
urls={
 'cffdrs_1817_fwi.Rd':'https://raw.githubusercontent.com/cffdrs/cffdrs_r/9481404cad25387292c1d8692bdb126bbe514d9c/man/fwi.Rd',
 'cffdrs_historico.json':'https://api.github.com/repos/cffdrs/cffdrs_r/commits?path=R/fwi.r&sha=9481404cad25387292c1d8692bdb126bbe514d9c&per_page=100',
 'CFS_2015.pdf':'https://publications.gc.ca/collections/collection_2016/rncan-nrcan/Fo133-1-424-eng.pdf',
 'CFS_1985.pdf':'https://climatelibrary.ecc.gov.nt.ca/dataset/c36897fc-7ee0-44ea-9e8a-3b2147911139/resource/a4df620a-52bc-4a78-afed-2e6a8dd226d4/download/fwi_equation_19973.pdf',
 'xclim_062_cffwis.py':'https://raw.githubusercontent.com/Ouranosinc/xclim/v0.62.0/src/xclim/indices/fire/_cffwis.py',
}
manifesto={}
with httpx.Client(timeout=60,follow_redirects=True) as c:
 for nome,url in urls.items():
  try:
   r=c.get(url);dados=r.content
   (OUT/nome).write_bytes(dados)
   manifesto[nome]=dict(url=url,status=r.status_code,sha256=hashlib.sha256(dados).hexdigest())
  except Exception as e:manifesto[nome]=dict(url=url,erro=repr(e))
(OUT/'manifesto.json').write_text(json.dumps(manifesto,indent=2),encoding='utf-8')
print(json.dumps(manifesto,indent=2))
