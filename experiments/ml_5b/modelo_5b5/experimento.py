"""Desenvolvimento temporal exclusivamente 2022–2023; sem consultas a resultados 2024."""
import csv
import hashlib
import importlib.metadata
import json
import platform
import sys
from collections import Counter
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier,RandomForestClassifier
from sklearn.inspection import permutation_importance
from scipy.stats import ks_2samp

OUT=Path(__file__).resolve().parent
DATA=OUT.parent/'dataset_5b3'
# Reutilização de funções puras de métricas, não de modelos/resultados da experiência anterior.
sys.path.insert(0,str(OUT.parent/'modelo_5b4'))
from comum import metricas

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def guardar(nome,o):
    (OUT/nome).write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def dados():
    manifest=json.loads((DATA/'checksums.json').read_text(encoding='utf-8'))
    assert sha(DATA/'dataset_elegivel.csv')==manifest['dataset_elegivel.csv']
    with (DATA/'dataset_elegivel.csv').open(encoding='utf-8') as f:
        rows=[r for r in csv.DictReader(f) if r['ano'] in ('2022','2023')]
    d=pd.DataFrame(rows)
    assert d['target_24h'].isin(['0','1']).all() and d['motivos_exclusao'].eq('').all()
    assert d['coverage_status'].isin(['aceitavel','forte']).all()
    d['t']=pd.to_datetime(d['data_T'],utc=True);d['fim']=d.t+pd.Timedelta(days=1)
    assert (d.t.dt.year<2024).all()
    for k in ('temperatura','humidade','vento','precipitacao_24h','ffmc','dmc','dc','isi','bui','fwi','mes','dia_do_ano','dia_da_semana','target_24h'):
        d[k]=pd.to_numeric(d[k])
    return d

def dividir(d,fit_end,cal_end,eval_end):
    a,b,c=[pd.Timestamp(x,tz='UTC') for x in (fit_end,cal_end,eval_end)]
    fit=d[(d.t<a)&(d.fim<a)]
    cal=d[(d.t>=a)&(d.t<b)&(d.fim<b)]
    test=d[(d.t>=b)&(d.t<c)&(d.fim<c)]
    assert fit.fim.max()<cal.t.min()
    if len(test):assert cal.fim.max()<test.t.min()
    return fit,cal,test

def pipeline(nome,features,balanced,seed):
    cat=[f for f in features if f in ('municipio','epoca_ano')];num=[f for f in features if f not in cat]
    trans=[('num',StandardScaler(),num)] if num else []
    if cat:trans.append(('cat',OneHotEncoder(handle_unknown='ignore',sparse_output=False),cat))
    w='balanced' if balanced else None
    models=dict(prevalencia=DummyClassifier(strategy='prior'),
        logistica=LogisticRegression(C=1.,max_iter=2000,class_weight=w,random_state=seed),
        hgb=HistGradientBoostingClassifier(max_iter=100,max_leaf_nodes=7,min_samples_leaf=20,l2_regularization=1.,early_stopping=False,class_weight=w,random_state=seed),
        rf=RandomForestClassifier(n_estimators=200,max_depth=5,min_samples_leaf=10,max_features='sqrt',class_weight=w,random_state=seed,n_jobs=1))
    return Pipeline([('pre',ColumnTransformer(trans)),('modelo',models[nome])])

def logit(p):
    p=np.clip(p,1e-6,1-1e-6);return np.log(p/(1-p)).reshape(-1,1)

def score(pipe,features,d,calibrador=None):
    p=pipe.predict_proba(d[features])[:,1]
    return calibrador.predict_proba(logit(p))[:,1] if calibrador is not None else p

def threshold(y,p):
    return max((metricas(y,p,t/100) for t in range(1,100)),key=lambda m:(m['f1'],m['threshold']))['threshold']

def config_id(model,fs,balanced,cal):return f'{model}|{fs}|{balanced}|{cal}'

def main():
    assert not (OUT/'resultados_folds.json').exists(),'Experiência já executada; preservar decisões originais.'
    cfg=json.loads((OUT/'config.json').read_text(encoding='utf-8'));d=dados()
    schema=json.loads((DATA/'schema.json').read_text(encoding='utf-8'))
    assert all(set(fs)<=set(schema['features_permitidas']) for fs in cfg['features'].values())
    folds=[];result=[];pred=[];pipes={};base={}
    for fid,a,b,c in cfg['folds']:
        fit,cal,test=dividir(d,a,b,c);cv=cal[cal.municipio.eq('1714')]
        assert fit.target_24h.nunique()==2 and cv.target_24h.nunique()==2
        folds.append(dict(fold=fid,fit_end=a,cal_end=b,eval_end=c,
            partes={nome:dict(n=len(x),positivos=int(x.target_24h.sum()),municipios=dict(Counter(x.municipio)),inicio=x.t.min().isoformat(),fim=x.t.max().isoformat()) for nome,x in [('fit',fit),('cal',cal),('eval',test)]}))
        for model in ('prevalencia','logistica','hgb','rf'):
            sets={'baseline':['temperatura']} if model=='prevalencia' else cfg['features']
            for fs,features in sets.items():
                for bal in ([False] if model=='prevalencia' else [False,True]):
                    pipe=pipeline(model,features,bal,cfg['seed']);pipe.fit(fit[features],fit.target_24h)
                    nums=[f for f in features if f not in ('municipio','epoca_ano')]
                    np.testing.assert_allclose(pipe.named_steps['pre'].named_transformers_['num'].mean_,fit[nums].mean())
                    calibrador=LogisticRegression(C=1.,random_state=cfg['seed']).fit(logit(score(pipe,features,cv)),cv.target_24h) if model!='prevalencia' else None
                    for cname in (['sem'] if model=='prevalencia' else cfg['calibracao']):
                        cc=calibrador if cname=='sigmoid' else None
                        tc=threshold(cv.target_24h.to_numpy(),score(pipe,features,cv,cc))
                        p=score(pipe,features,test,cc);cid=config_id(model,fs,bal,cname)
                        for group in ('global','1714','1106'):
                            mask=np.ones(len(test),bool) if group=='global' else test.municipio.eq(group).to_numpy()
                            if not mask.any():continue
                            m=metricas(test.loc[mask,'target_24h'].to_numpy(),p[mask],tc)
                            result.append(dict(id=cid,modelo=model,features=fs,balanced=bal,calibracao=cname,fold=fid,grupo=group,**m))
                            if model=='prevalencia' and group=='1714':base[fid]=m
                        pipes[fid,cid]=(pipe,features,cc,test)
        print(fid,'concluído',flush=True)
    guardar('folds.json',folds);guardar('resultados_folds.json',result)
    flat=[{k:v for k,v in r.items() if k not in ('reliability_bins','matriz')} for r in result]
    pd.DataFrame(flat).to_csv(OUT/'metricas_folds.csv',index=False)
    summaries=[]
    for cid in sorted({r['id'] for r in result}):
        rr=[r for r in result if r['id']==cid and r['grupo']=='1714']
        stats={}
        for k in ('pr_auc_ap','roc_auc','brier','precision','recall','f1'):
            v=np.array([r[k] for r in rr if r[k] is not None]);low=k=='brier'
            stats[k]=dict(n=len(v),media=float(v.mean()),mediana=float(np.median(v)),desvio=float(v.std(ddof=1)),
                pior=float(v.max() if low else v.min()),melhor=float(v.min() if low else v.max()))
        gains=[r['pr_auc_ap']-base[r['fold']]['pr_auc_ap'] for r in rr]
        bg=[base[r['fold']]['brier']-r['brier'] for r in rr]
        ok=len(rr)==4 and min(gains)>0 and np.median(bg)>0
        summaries.append(dict(id=cid,estatisticas=stats,pior_ganho_ap=min(gains),mediana_ganho_brier=float(np.median(bg)),elegivel=bool(ok)))
    guardar('estabilidade.json',summaries)
    ranked=sorted(summaries,key=lambda r:(r['pior_ganho_ap'],r['estatisticas']['pr_auc_ap']['mediana'],r['mediana_ganho_brier']),reverse=True)
    accepted=[r for r in ranked if r['elegivel']];selected=accepted[0]['id'] if accepted else None
    diagnostic=selected or ranked[0]['id'];importance=[]
    # Explicabilidade só de folds de desenvolvimento; não altera a seleção.
    for fid,_,_,_ in cfg['folds']:
        pipe,features,cc,test=pipes[fid,diagnostic];v=test[test.municipio.eq('1714')]
        perm=permutation_importance(pipe,v[features],v.target_24h,scoring='average_precision',n_repeats=10,random_state=cfg['seed'],n_jobs=1)
        importance.extend(dict(fold=fid,feature=f,media=float(m),desvio=float(s)) for f,m,s in zip(features,perm.importances_mean,perm.importances_std))
    guardar('importancia.json',dict(configuracao=diagnostic,apenas_diagnostico=selected is None,nota='AP do pipeline base antes da sigmoid; não causal.',folds=importance))
    final=None
    if selected:
        model,fs,bal,calname=selected.split('|');features=cfg['features'][fs]
        fit,cal,_=dividir(d,cfg['final_fit_end'],cfg['final_cal_end'],'2024-01-02');cv=cal[cal.municipio.eq('1714')]
        pipe=pipeline(model,features,bal=='True',cfg['seed']).fit(fit[features],fit.target_24h)
        cc=LogisticRegression(C=1.,random_state=cfg['seed']).fit(logit(score(pipe,features,cv)),cv.target_24h) if calname=='sigmoid' else None
        th=threshold(cv.target_24h.to_numpy(),score(pipe,features,cv,cc))
        final=dict(features=features,threshold=th,fit_end=cfg['final_fit_end'],cal_end=cfg['final_cal_end'],calibracao=calname)
        joblib.dump(dict(pipeline=pipe,calibrador=cc,**final),OUT/'candidato.joblib')
    guardar('decisao.json',dict(candidato=selected,final=final,criterio=cfg['criterio'],ranking=ranked,
        estado='pronto para validação externa futura; não validado' if selected else 'NO-GO: nenhuma configuração cumpre o critério',
        ano_2024='Consumido na experiência anterior; não carregado para ajuste ou avaliação nesta fase.',
        checks=dict(anos_desenvolvimento=[2022,2023],scaler_por_fit=True,purga_horizontes=True,threshold_bloco_anterior=True,calibracao_bloco_anterior=True,random_split=False,smote=False)))
    drift=[]
    for group in ('global','1714','1106'):
        x=d if group=='global' else d[d.municipio.eq(group)]
        aa=x[x.t.dt.year.eq(2022)];bb=x[x.t.dt.year.eq(2023)]
        for f in cfg['features']['D_calendario']:
            if f=='epoca_ano':continue
            scale=float(aa[f].std())
            drift.append(dict(grupo=group,feature=f,n2022=len(aa),n2023=len(bb),media2022=float(aa[f].mean()),media2023=float(bb[f].mean()),
                mediana2022=float(aa[f].median()),mediana2023=float(bb[f].median()),
                diferenca_padronizada=float((bb[f].mean()-aa[f].mean())/scale) if scale>0 else None,
                ks=float(ks_2samp(aa[f],bb[f]).statistic)))
    pd.DataFrame(drift).to_csv(OUT/'drift.csv',index=False)
    groups=[]
    for (year,mun,month),x in d.groupby([d.t.dt.year,'municipio','mes']):
        groups.append(dict(ano=int(year),municipio=mun,mes=int(month),n=len(x),positivos=int(x.target_24h.sum()),prevalencia=float(x.target_24h.mean())))
    guardar('composicao.json',groups)
    guardar('versoes.json',dict(python=platform.python_version(),**{n:importlib.metadata.version(n) for n in ('numpy','pandas','scikit-learn','joblib','scipy')}))
    guardar('manifesto.json',dict(dataset_sha256=sha(DATA/'dataset_elegivel.csv'),config_sha256=sha(OUT/'config.json'),
        metricas_puras_sha256=sha(OUT.parent/'modelo_5b4/comum.py'),
        checksums={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='manifesto.json'}))
    print('DECISÃO:',selected,final,flush=True)

if __name__=='__main__':main()
