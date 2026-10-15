"""Ajuste 2022, seleção 2023. Não carrega o conjunto de teste."""
import importlib.metadata
import json
import platform
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
from comum import *

def main():
    cfg=json.loads((OUT/'config.json').read_text(encoding='utf-8'));seed=cfg['seed']
    train=carregar([cfg['treino']]);val=carregar([cfg['validacao']])
    X=train[FEATURES];y=train.target_24h
    models={
      'prevalencia':DummyClassifier(strategy='prior'),
      'logistica':LogisticRegression(C=1.,max_iter=2000,random_state=seed),
      'hist_gradient_boosting':HistGradientBoostingClassifier(max_iter=100,max_leaf_nodes=7,min_samples_leaf=20,l2_regularization=1.,early_stopping=False,random_state=seed),
      'random_forest':RandomForestClassifier(n_estimators=200,max_depth=5,min_samples_leaf=10,max_features='sqrt',random_state=seed,n_jobs=1)}
    results={};thresholds=[];importances={};pipes={}
    mask=val.municipio.eq('1714');v=val.loc[mask];selection={}
    for name,model in models.items():
        pre=ColumnTransformer([('numericas',StandardScaler(),NUM),('categoricas',OneHotEncoder(handle_unknown='ignore',sparse_output=False),CAT)])
        pipe=Pipeline([('preparacao',pre),('modelo',model)]);pipe.fit(X,y);pipes[name]=pipe
        # Verificar o scaler contra 2022, não apenas confiar no pipeline.
        assert np.allclose(pipe.named_steps['preparacao'].named_transformers_['numericas'].mean_,X[NUM].mean().to_numpy())
        assert set(pipe.named_steps['preparacao'].named_transformers_['categoricas'].categories_[0])==set(train.municipio)
        pv=pipe.predict_proba(v[FEATURES])[:,1]
        grid=[metricas(v.target_24h.to_numpy(),pv,t/100) for t in range(1,100)]
        best=max(grid,key=lambda r:(r['f1'],r['threshold']))
        for r in grid:thresholds.append(dict(modelo=name,**{k:r[k] for k in ('threshold','precision','recall','f1','balanced_accuracy')}))
        probs=pipe.predict_proba(val[FEATURES])[:,1]
        results[name]=grupos(val,probs,best['threshold']);selection[name]=best['threshold']
        joblib.dump(pipe,OUT/f'{name}.joblib')
        if name!='prevalencia':
            perm=permutation_importance(pipe,v[FEATURES],v.target_24h,scoring='average_precision',n_repeats=10,random_state=seed,n_jobs=1)
            importances[name]=[dict(feature=f,media=float(m),desvio=float(s)) for f,m,s in zip(FEATURES,perm.importances_mean,perm.importances_std)]
    selected=max((n for n in models if n!='prevalencia'),key=lambda n:(results[n]['1714']['pr_auc_ap'],-results[n]['1714']['brier']))
    logistic=pipes['logistica'];names=logistic.named_steps['preparacao'].get_feature_names_out()
    guardar('coeficientes_logistica.json',[dict(feature=str(f),coeficiente=float(c)) for f,c in zip(names,logistic.named_steps['modelo'].coef_[0])])
    guardar('importancia_validacao.json',importances);guardar('metricas_validacao.json',results)
    pd.DataFrame(thresholds).to_csv(OUT/'thresholds_validacao.csv',index=False)
    guardar('decisao_congelada.json',dict(modelo=selected,thresholds=selection,config_sha256=sha(OUT/'config.json'),
        dataset_sha256=sha(DATA/'dataset_elegivel.csv'),criterio=cfg['selecao'],modelos={n:sha(OUT/f'{n}.joblib') for n in models},
        n_treino=len(train),n_validacao=len(val),prevalencia_treino=float(y.mean()),
        verificacoes=dict(anos_fit=[2022],anos_selecao=[2023],teste_nao_carregado=True,scaler_so_treino=True,encoder_so_treino=True,
            calibracao_teste=False,features=FEATURES,smote=False,random_split=False),
        scripts={n:sha(OUT/n) for n in ('treinar.py','avaliar.py','comum.py')}))
    guardar('versoes.json',dict(python=platform.python_version(),**{n:importlib.metadata.version(n) for n in ('numpy','pandas','scikit-learn','joblib','scipy')}))
    print('Modelo selecionado em 2023:',selected,'threshold',selection[selected],flush=True)

if __name__=='__main__':main()
