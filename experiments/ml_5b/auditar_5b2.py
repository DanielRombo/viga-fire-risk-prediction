"""Inspeção offline de amostras oficiais. Não certifica cobertura por ausência de linhas."""
import csv
import hashlib
import io
import json
import unicodedata
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
FONTES = BASE / 'fontes_5b2'
SAIDA = BASE / 'auditoria_5b2'

def normalizar(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.casefold()) if not unicodedata.combining(c)).strip()

def csv_amostra(nome):
    dados = (FONTES / (nome + '.bin')).read_bytes()
    # O último registo do Range pode estar cortado. Aceitar apenas linhas CSV completas.
    dados = dados[:dados.rfind(b'\n')+1]
    reader = csv.DictReader(io.StringIO(dados.decode('utf-8-sig')), strict=True)
    rows = list(reader)
    assert all(None not in r and all(v is not None for v in r.values()) for r in rows)
    return reader.fieldnames, rows

def main():
    SAIDA.mkdir(exist_ok=True)
    manifesto = []
    for p in sorted(FONTES.glob('*.json')):
        info = json.loads(p.read_text(encoding='utf-8'))
        raw = p.with_suffix('.bin').read_bytes()
        assert len(raw) == info['bytes'] and hashlib.sha256(raw).hexdigest() == info['sha256']
        manifesto.append(info)
    campos, amostra = csv_amostra('sgif_amostra')
    _, eliminados = csv_amostra('sgif_eliminados_amostra')
    _, adm = csv_amostra('sgif_administracao')
    catalogo = json.loads((BASE.parents[1] / 'backend/data/regioes_principais.json').read_text(encoding='utf-8'))
    municipios = []
    for p in catalogo:
        if not p.get('recolha_automatica', False):
            continue
        candidatos = [r for r in adm if normalizar(r['Concelho']) == normalizar(p['nome'])
                      and normalizar(r['Distrito']) == normalizar(p['distrito'])]
        codigos = sorted({r['DTCC'] for r in candidatos})
        municipios.append(dict(nome=p['nome'], distrito=p['distrito'], codigos_candidatos=codigos,
                               latitude=p['latitude'], longitude=p['longitude'],
                               estado='correspondencia_unica_sgif' if len(codigos)==1 else 'nao_resolvido',
                               validacao_caop=False, cobertura_certificada=False))
    resumo = dict(decisao='NO-GO', motivo='Cobertura e semântica temporal não certificadas',
                  amostra_parcial=True, numero_campos=len(campos), campos=campos,
                  registos_amostra=len(amostra), tipos=dict(Counter(r['Tipo'] for r in amostra)),
                  classificacoes=dict(Counter(r['ClassificacaoRegisto'] for r in amostra)),
                  estados=dict(Counter(r['EstadoRegisto'] for r in amostra)),
                  datas_amostra=[min(r['DHInicio'] for r in amostra), max(r['DHInicio'] for r in amostra)],
                  eliminados_amostra=len(eliminados), motivos_eliminacao=dict(Counter(r['EstadoRegisto'] for r in eliminados)),
                  municipios_administracao=len({r['DTCC'] for r in adm}),
                  registos_administracao=len(adm),
                  catalogo_resolvido=sum(len(r['codigos_candidatos'])==1 for r in municipios),
                  positivos_certificados=0, negativos_certificados=0,
                  linhas_dataset_5b2=0, null_dataset_5b2=0, prevalencia=None,
                  nota='Zero labels emitidos não significa zero incêndios. Nenhum município-dia certificado foi criado.')
    for nome, valor in [('integridade',manifesto),('resumo',resumo),('municipios_catalogo',municipios)]:
        (SAIDA/(nome+'.json')).write_text(json.dumps(valor,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (SAIDA/'amostra_eventos.csv').open('w',encoding='utf-8',newline='') as f:
        keep=['Codigo','CodigoSado','Tipo','DHInicio','Distrito','Concelho','INE',
              'Lat_4326','Lon_4326','Reacendimento_IncendioPai','ClassificacaoRegisto','EstadoRegisto']
        w=csv.DictWriter(f,fieldnames=keep);w.writeheader()
        w.writerows({k:r[k] for k in keep} for r in amostra)
    grupos=Counter((r['Concelho'],r['DHInicio'][:4],r['DHInicio'][5:7]) for r in amostra)
    with (SAIDA/'contagens_amostra.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['municipio_declarado','ano','mes','eventos_candidatos_amostra','y1_emitidos','y0_emitidos','prevalencia'])
        for (municipio,ano,mes),n in sorted(grupos.items()):w.writerow([municipio,ano,mes,n,0,0,''])
    print(json.dumps({k:v for k,v in resumo.items() if k!='campos'},ensure_ascii=True,indent=2))

if __name__=='__main__':main()
