"""Exports públicos integrais, streaming, originais imutáveis, sem produção."""
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parent/'cobertura_5b2b'
URL='https://fogos.icnf.pt/download/ExportarDadosSGIF/'
FILES={'eventos':'Data2001_now.csv','eliminados':'Data2001_noweliminados.csv'}

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def obter(nome):
    ROOT.mkdir(exist_ok=True)
    p=ROOT/FILES[nome];meta=p.with_suffix('.manifesto.json')
    if p.exists():
        m=json.loads(meta.read_text(encoding='utf-8'))
        assert sha(p)==m['sha256'] and p.stat().st_size==m['bytes']
        print(nome,'cache verificada',flush=True);return
    if shutil.disk_usage(ROOT).free < 2_000_000_000:raise RuntimeError('Espaço livre insuficiente')
    temp=p.with_suffix('.part')
    if temp.exists():raise RuntimeError('Download parcial existente; inspecionar antes de repetir')
    with urlopen(Request(URL+FILES[nome],headers={'User-Agent':'VIGA-ML5B2B-audit'}),timeout=60) as r:
        if r.status!=200:raise RuntimeError('Resposta não integral')
        m={'url':r.url,'obtido_em':datetime.now(timezone.utc).isoformat(),
           'content_length':r.headers.get('Content-Length'),'etag':r.headers.get('ETag'),
           'last_modified':r.headers.get('Last-Modified')}
        total=0
        with temp.open('xb') as f:
            while b:=r.read(1024*1024):
                f.write(b);total+=len(b)
                if total%(50*1024*1024)==0:print(nome,total,'bytes',flush=True)
        if m['content_length'] and int(m['content_length'])!=total:raise RuntimeError('Resposta truncada')
    m.update(bytes=total,sha256=sha(temp))
    temp.rename(p)
    meta.write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(m),flush=True)

if __name__=='__main__':
    for nome in sys.argv[1:] or FILES:obter(nome)
