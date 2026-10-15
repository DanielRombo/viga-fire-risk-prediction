import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score,roc_auc_score,precision_score,recall_score,
                             f1_score,balanced_accuracy_score,brier_score_loss,confusion_matrix)

OUT=Path(__file__).resolve().parent
DATA=OUT.parent/'dataset_5b3'
NUM=['temperatura','humidade','vento','precipitacao_24h','ffmc','dmc','dc','isi','bui','fwi','mes','dia_do_ano','dia_da_semana']
CAT=['municipio','epoca_ano']
FEATURES=NUM+CAT

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def guardar(nome,obj):
    (OUT/nome).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def carregar(anos):
    hashes=json.loads((DATA/'checksums.json').read_text(encoding='utf-8'))
    assert sha(DATA/'dataset_elegivel.csv')==hashes['dataset_elegivel.csv']
    schema=json.loads((DATA/'schema.json').read_text(encoding='utf-8'))
    assert set(FEATURES)<=set(schema['features_permitidas'])
    # Filtrar antes de formar X/y; treino nunca recebe linhas de 2024.
    with (DATA/'dataset_elegivel.csv').open(encoding='utf-8') as f:
        rows=[r for r in csv.DictReader(f) if int(r['ano']) in anos]
    d=pd.DataFrame(rows)
    assert not d.duplicated(['municipio','data_T']).any()
    assert d['coverage_status'].isin(['aceitavel','forte']).all()
    assert d['territory_confidence'].isin(['alta','media']).all()
    assert d['target_24h'].isin(['0','1']).all()
    assert d['motivos_exclusao'].eq('').all()
    for k in NUM:d[k]=pd.to_numeric(d[k],errors='raise')
    assert np.isfinite(d[NUM].to_numpy()).all()
    d['target_24h']=d['target_24h'].astype(int)
    t=pd.to_datetime(d['data_T'],utc=True)
    assert (pd.to_datetime(d['instante_referencia_utc'],utc=True)<=t).all()
    assert (t+pd.Timedelta(days=1)).dt.year.eq(t.dt.year).all()
    return d

def bins(y,p):
    result=[]
    for i in range(10):
        mask=(p>=i/10)&((p<(i+1)/10) if i<9 else (p<=1))
        result.append(dict(inferior=i/10,superior=(i+1)/10,n=int(mask.sum()),
            score_medio=float(p[mask].mean()) if mask.any() else None,
            frequencia=float(y[mask].mean()) if mask.any() else None))
    return result

def metricas(y,p,threshold):
    y=np.asarray(y);p=np.asarray(p);pred=p>=threshold
    ambas=len(np.unique(y))==2
    return dict(n=len(y),positivos=int(y.sum()),prevalencia=float(y.mean()),threshold=float(threshold),
        roc_auc=float(roc_auc_score(y,p)) if ambas else None,
        pr_auc_ap=float(average_precision_score(y,p)) if y.sum() else None,
        precision=float(precision_score(y,pred,zero_division=0)),recall=float(recall_score(y,pred,zero_division=0)) if y.sum() else None,
        f1=float(f1_score(y,pred,zero_division=0)),balanced_accuracy=float(balanced_accuracy_score(y,pred)) if ambas else None,
        brier=float(brier_score_loss(y,p)),matriz=confusion_matrix(y,pred,labels=[0,1]).tolist(),
        reliability_bins=bins(y,p),nota=None if ambas else 'ROC-AUC/balanced accuracy indisponíveis: falta uma classe; precision sem previsões positivas é 0 por convenção.')

def grupos(d,p,threshold):
    resultado={'global':metricas(d.target_24h.to_numpy(),p,threshold)}
    for c in ('1106','0805','1714'):
        mask=d.municipio.eq(c).to_numpy()
        resultado[c]=metricas(d.loc[mask,'target_24h'].to_numpy(),p[mask],threshold) if mask.any() else {'n':0,'nota':'Sem linhas elegíveis neste split.'}
    return resultado
