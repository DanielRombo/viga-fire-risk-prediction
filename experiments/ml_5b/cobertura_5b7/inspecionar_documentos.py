"""Extrai páginas relevantes do PDF local, sem rede ou acesso a modelos."""
import json,re,sys
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'_deps'))
from pypdf import PdfReader

if __name__=='__main__':
    reader=PdfReader(P/'evidencias/sgifr_relatorio.bin');out=[]
    for i,page in enumerate(reader.pages):
        s=page.extract_text() or ''
        if re.search(r'8[. ]?252|provis[oó]ri|consolidad|qualidade dos dados|SADO|dados.*SGIF',s,re.I):
            out.append({'pagina_pdf':i+1,'texto':s})
            lines=s.splitlines()
            for j,l in enumerate(lines):
                if re.search(r'8[. ]?252|provis[oó]ri|consolidad|qualidade dos dados|SADO',l,re.I):
                    print('PAGE',i+1,' '.join(lines[max(0,j-1):j+3]))
    (P/'evidencias/sgifr_paginas.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Páginas totais',len(reader.pages),'selecionadas',len(out))
