"""Mesma inferência e explicação técnica antes/depois da instalação do xclim."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import shap

sys.path.insert(0, '/app')
from services.artefactos_ml import carregar_artefactos
from services.modelo_ml import prever_risco

kaggle, escala_k, anpc, escala_a, encoder = carregar_artefactos()
distrito = int(encoder.transform(['LISBOA'])[0])
xk = escala_k.transform(np.array([[20,50,10,0,85,6,15,5,7,1]], dtype=float))
xa = escala_a.transform(np.array([[7,13,0,2024,distrito,38.7223,-9.1393]], dtype=float))
resultado = {
    'kaggle':kaggle.predict_proba(xk).tolist(), 'anpc':anpc.predict_proba(xa).tolist(),
    'shap':np.asarray(shap.TreeExplainer(kaggle).shap_values(xk)).tolist(),
    'api_servico':prever_risco(dict(temperatura=20.,humidade=50.,velocidade_vento=10.,precipitacao=0.,
        ffmc=85.,dmc=6.,dc=15.,isi=5.,distrito='Lisboa',latitude=38.7223,longitude=-9.1393,
        data_hora=datetime(2024,7,1,12,tzinfo=timezone.utc)))}
assert resultado['api_servico']['estado']=='ok'
assert np.isfinite(resultado['shap']).all()
Path(sys.argv[1]).write_text(json.dumps(resultado,indent=2,ensure_ascii=False),encoding='utf-8')
print('Cinco artefactos, dois modelos, scalers, encoder e SHAP validados.')
