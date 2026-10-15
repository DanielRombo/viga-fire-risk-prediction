"""Aquisição limitada de documentação; nunca carrega datasets PRDF ou modelos."""
import argparse
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT=Path(__file__).resolve().parent
SOURCES={
 'anepc_historico':('http://www.prociv.pt/_vti_bin/ARM.ANPC.UI/ANPC_SituacaoOperacional.svc/GetHistoryOccurrencesByLocation',100_000),
 'ine_metodologia':('https://www.ine.pt/bddXplorer/htdocs/minfo.jsp?var_cd=0013512&lingua=PT',500_000),
 'sgifr_relatorio':('https://www.sgifr.gov.pt/documents/196633/196678/Relatorio_Atividades_SGIFR_2025_v20260715.pdf/83fdcf74-4a07-97d9-da97-da89052aa755?t=1784124175203',12_000_000),
 'ine_atual':('https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd=0013512&lang=PT',2_000_000),
 'sgifr_indice':('https://www.sgifr.gov.pt/relatorios-anuais',500_000),
 'sgif_diretorio':('https://fogos.icnf.pt/download/ExportarDadosSGIF/',100_000),
 'sgif_diario_amostra':('https://fogos.icnf.pt/download/ExportarDadosSGIF/daily_fires_summary.csv',32_768),
 'dadosgov_busca':('https://dados.gov.pt/api/1/datasets/?q=ProCiv&page_size=5',200_000),
}

def obter(key):
    url,limit=SOURCES[key]; folder=OUT/'evidencias';folder.mkdir(exist_ok=True)
    meta=folder/(key+'.json'); raw=folder/(key+'.bin')
    previous=json.loads(meta.read_text(encoding='utf-8')) if meta.exists() else None
    if previous and 'erro' not in previous:return previous
    result={'id':key,'url':url,'consultado_em':datetime.now(timezone.utc).isoformat(),'limite_bytes':limit}
    if previous:result['tentativa_anterior']=previous
    try:
        headers={'User-Agent':'VIGA-research-coverage-audit/1.0'}
        if key.endswith('amostra'):headers['Range']=f'bytes=0-{limit-1}'
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30) as response:
            body=response.read(limit+1)
            result.update(status=response.status,url_final=response.url,content_type=response.headers.get('Content-Type'),content_range=response.headers.get('Content-Range'),content_length=response.headers.get('Content-Length'))
        result.update(truncado=len(body)>limit,amostra=key.endswith('amostra'))
        body=body[:limit]; raw.write_bytes(body)
        result.update(bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
    except Exception as exc:
        result.update(erro=type(exc).__name__+': '+str(exc))
    meta.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('fonte',choices=list(SOURCES)+['todas']);args=parser.parse_args()
    for key in SOURCES if args.fonte=='todas' else [args.fonte]:print(json.dumps(obter(key),ensure_ascii=False))
