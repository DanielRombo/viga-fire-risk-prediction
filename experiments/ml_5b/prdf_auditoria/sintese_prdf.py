"""Consolida pequenos artefactos; não acede a modelos ou serviços."""
import csv
import hashlib
import json
from collections import Counter
from auditar_prdf import OUT,DATA,guardar,csvout

def load(n):return json.loads((OUT/n).read_text(encoding='utf-8'))

def main():
    inv=load('inventario_inicial.json');fog=load('fogos.json');met=load('meteo.json');frp=load('frp.json');pba=load('pba.json');geo=load('geometria.json')
    descriptions={}
    with (DATA/'fogos-metadata.csv').open(encoding='utf-8-sig') as f:
        for r in list(csv.reader(f,delimiter=';'))[1:]:
            if len(r)>=2:descriptions[r[0].strip().upper()]=r[1].strip()
    schemas={'Fogos':[r['name'] for r in fog['schemas']], 'METEO':met['schema'], 'FRP':frp['schema'], 'PBA':[r['name'] for r in pba['schema']]}
    schemas['metadata_sem_coluna_exata']=[k for k in descriptions if k not in {s.upper() for s in schemas['Fogos']}]
    rows=[]
    for source,fields in schemas.items():
        for field in fields:
            u=field.upper();cat='DUVIDOSO';reason='Momento de disponibilidade/documentação insuficiente; não admitir diretamente como feature.';moment='Não demonstrado'
            if source=='METEO':
                cat='PROIBIDO';reason='Série selecionada pelo incêndio futuro, predominantemente durante/depois do alerta. Não fornece covariáveis completas ex ante para todos os município-dias.';moment='Associado ao evento; comparar DHMeteo com T e publicação'
                if u in ('ID','CODIGO','DHMETEO','IDGRELHA','IDECMWF_ERA5'):cat='DUVIDOSO';reason='Identificador/tempo para auditoria e associação, não feature preditiva.'
            elif source=='FRP':
                cat='PROIBIDO';reason='Deteção/energia/confiança associada a combustão observada; apenas validação auxiliar do positivo futuro, ausência não é negativo.';moment='Durante combustão/deteção'
            elif source=='PBA':
                cat='PROIBIDO';reason='Perímetro/atributo de incêndio observado, levantado ou revisto posteriormente; validação espacial, não predictor ex ante.';moment='Após evento ou revisão'
            elif u in ('CONCELHO','DISTRITO','FREGUESIA','INE','NUTS2','NUTS3'):
                cat='SAFE_EM_T';reason='Só como unidade territorial definida antes de T e disponível para positivos/negativos. Não selecionar localização a partir do incêndio futuro.';moment='Catálogo territorial pré-definido, condicional'
            elif any(x in u for x in ('DH','DURAC','AREA','INC','FRP','FRE','MODIS','EFFIS','CAUSA','BACOD','BASCORE','BAMETODO','VELOCIDADE','TEMPO','ORIGINOU','FONTEALERTA')) or u in ('ANO','MES','DIA','HORA','TIPO','GEOM','LAT_4326','LON_4326','LOCAL','X_3763','Y_3763','X_20790','Y_20790'):
                cat='PROIBIDO';reason='Característica/tempo/posição/resultado do evento futuro. DHInicio pode definir o target de alerta, nunca uma feature.';moment='No evento ou posteriormente'
            elif u in ('FWI','FFMC','DMC','DC','ISI','BUI','DSR','HFWI','HFFMC','HISI','RCM','THC','TEMPERATURA','HUMIDADERELATIVA','VENTOINTENSIDADE','VENTOINTENSIDADE_VETOR','VENTODIRECAO','VENTODIRECAO_VETOR','PRECEPITACAO','PRECIPITACAO'):
                cat='PROIBIDO';reason='Valor associado ao evento, sem prova de disponibilidade e janela compatível com T; usar apenas comparação, não substituir pipeline FWI VIGA.';moment='No alerta/durante evento; publicação desconhecida'
            rows.append(dict(campo=field,fonte=source,descricao=descriptions.get(u,'Sem definição individual no metadata local'),categoria=cat,momento=moment,justificacao=reason))
    csvout('leakage.csv',rows)
    inv['fase']='auditoria integral; estimativas agregadas, sem dataset final ou modelos'
    for filename,summary in [('fogos.gpkg',fog),('METEO.csv',met),('FRP.csv',frp),('PBA.gpkg',pba)]:inv['ficheiros'][filename]['auditoria']=summary
    inv['geometria']=geo;inv['taxonomia_leakage']=dict(Counter(r['categoria'] for r in rows));guardar('inventario.json',inv)
    guardar('cruzamentos.json',dict(fogos_meteo_exato={k:met[k] for k in ('fogos_com_meteo','fogos_sem_meteo','codigos_meteo_sem_fogo','ano2025')},
        fogos_meteo_alias=load('meteo_chaves.json'),fogos_pba=pba['cruzamento'],pba_chaves_secundarias=load('complementos.json')['pba_chaves_secundarias'],
        fogos_frp=load('frp_cruzamento.json'),territorio=geo['territorio2025']))
    # Integridade pós-leitura: todos os originais ainda correspondem aos SHA-256 iniciais.
    checks={}
    for name,meta in inv['ficheiros'].items():
        with (DATA/name).open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        assert digest==meta['sha256'],name
        checks[name]=digest
    guardar('integridade_originais.json',dict(sha256=checks,originais_inalterados=True))

if __name__=='__main__':main()
