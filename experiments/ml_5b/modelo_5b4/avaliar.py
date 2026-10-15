"""Holdout 2024, sem ajuste. Recusa sobrescrever uma avaliação já concluída."""
import json
import joblib
import numpy as np
import pandas as pd
from comum import *

def main():
    assert not (OUT/'metricas_teste.json').exists(),'Teste já avaliado; não repetir seleção sobre o holdout.'
    lock=json.loads((OUT/'decisao_congelada.json').read_text(encoding='utf-8'))
    assert sha(OUT/'config.json')==lock['config_sha256']
    assert sha(DATA/'dataset_elegivel.csv')==lock['dataset_sha256']
    for n,h in lock['scripts'].items():assert sha(OUT/n)==h
    test=carregar([2024]);result={};pred=[]
    for name,h in lock['modelos'].items():
        assert sha(OUT/f'{name}.joblib')==h
        pipe=joblib.load(OUT/f'{name}.joblib');p=pipe.predict_proba(test[FEATURES])[:,1]
        result[name]=grupos(test,p,lock['thresholds'][name])
        for (_,r),score in zip(test.iterrows(),p):pred.append(dict(modelo=name,municipio=r.municipio,data_T=r.data_T,target=int(r.target_24h),score=float(score)))
    guardar('metricas_teste.json',result);pd.DataFrame(pred).to_csv(OUT/'scores_teste.csv',index=False)
    val=json.loads((OUT/'metricas_validacao.json').read_text(encoding='utf-8'));table=[]
    for split,rr in [('validacao',val),('teste',result)]:
        for name,groups in rr.items():
            for c,m in groups.items():table.append(dict(split=split,modelo=name,municipio=c,**{k:v for k,v in m.items() if k not in ('reliability_bins','matriz')}))
    pd.DataFrame(table).to_csv(OUT/'metricas.csv',index=False)
    selected=lock['modelo'];m=result[selected]['1714'];base=result['prevalencia']['1714']
    guardar('resultado.json',dict(modelo_congelado=selected,threshold=lock['thresholds'][selected],
        supera_baseline_ap_vila_real=m['pr_auc_ap']>base['pr_auc_ap'],
        ap_teste=m['pr_auc_ap'],ap_baseline=base['pr_auc_ap'],
        nota='Decisão científica final no relatório. Não escolher outro modelo depois de consultar o teste.'))
    # Curvas de fiabilidade em SVG autónomo, sem dependências novas.
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="780" height="540" viewBox="0 0 780 540">',
         '<rect width="780" height="540" fill="white"/>',
         '<text x="50" y="24">Fiabilidade — teste 2024, Vila Real (bins de 0,1)</text>',
         '<path d="M50 450 L450 50 M50 50 V450 H450" stroke="#aaa" fill="none"/>',
         '<text x="130" y="495">Score médio (0–1)</text>',
         '<text x="5" y="40">Frequência observada (0–1)</text>']
    for j,(name,color) in enumerate(zip(result,('#555','#0072b2','#d55e00','#009e73'))):
        bins_=result[name]['1714']['reliability_bins'];pts=[b for b in bins_ if b['n']]
        coords=' '.join(f"{50+400*b['score_medio']},{450-400*b['frequencia']}" for b in pts)
        svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}"/>')
        for b in pts:svg.append(f'<circle cx="{50+400*b["score_medio"]}" cy="{450-400*b["frequencia"]}" r="4" fill="{color}"><title>n={b["n"]}</title></circle>')
        svg.append(f'<text x="470" y="{80+j*30}" fill="{color}">{name}</text>')
    svg.append('</svg>');(OUT/'fiabilidade.svg').write_text('\n'.join(svg),encoding='utf-8')
    guardar('manifesto.json',dict(decisao_sha256=sha(OUT/'decisao_congelada.json'),
        checksums={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.suffix in ('.json','.csv','.py','.svg','.joblib') and p.name!='manifesto.json'},
        avaliacao='2024 avaliado uma vez; sem ajuste ou calibração no teste'))
    print(json.dumps(result[selected],ensure_ascii=True),flush=True)

if __name__=='__main__':main()
