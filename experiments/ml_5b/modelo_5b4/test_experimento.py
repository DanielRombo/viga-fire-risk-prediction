import json
import unittest
import joblib
import numpy as np
import pandas as pd
from comum import *

class ExperimentoTests(unittest.TestCase):
    def test_splits(self):
        for ano,n,pos in [(2022,373,51),(2023,722,40),(2024,598,41)]:
            d=carregar([ano]);self.assertEqual(len(d),n);self.assertEqual(int(d.target_24h.sum()),pos)
            self.assertEqual(set(pd.to_datetime(d.data_T).dt.year),{ano})

    def test_pipeline_fit_so_treino(self):
        d=carregar([2022])
        for n in ('logistica','hist_gradient_boosting','random_forest','prevalencia'):
            p=joblib.load(OUT/f'{n}.joblib').named_steps['preparacao']
            np.testing.assert_allclose(p.named_transformers_['numericas'].mean_,d[NUM].mean())
            self.assertEqual(set(p.named_transformers_['categoricas'].categories_[0]),{'1106','1714'})

    def test_baseline(self):
        m=json.loads((OUT/'metricas_teste.json').read_text())['prevalencia']
        for c in ('global','1714','0805'):
            self.assertAlmostEqual(m[c]['pr_auc_ap'],m[c]['prevalencia'])
            self.assertEqual(m[c]['roc_auc'],.5)

    def test_threshold_congelado(self):
        lock=json.loads((OUT/'decisao_congelada.json').read_text())
        grid=pd.read_csv(OUT/'thresholds_validacao.csv')
        for n,t in lock['thresholds'].items():
            g=grid[grid.modelo.eq(n)].sort_values(['f1','threshold'],ascending=False).iloc[0]
            self.assertAlmostEqual(t,g.threshold)
            for fname in ('metricas_validacao.json','metricas_teste.json'):
                m=json.loads((OUT/fname).read_text())[n]
                self.assertEqual(m['1714']['threshold'],t)

    def test_metricas_casos_limite(self):
        m=metricas(np.array([0,0]),np.array([0.,.2]),.5)
        self.assertIsNone(m['roc_auc']);self.assertIsNone(m['pr_auc_ap']);self.assertIsNone(m['recall'])
        self.assertEqual(m['matriz'],[[2,0],[0,0]])
        self.assertEqual(sum(b['n'] for b in bins(np.array([0,1]),np.array([0.,1.]))),2)

    def test_municipios_e_confusao(self):
        m=json.loads((OUT/'metricas_teste.json').read_text())
        for name,groups in m.items():
            self.assertEqual(groups['1106']['n'],0)
            for c in ('global','1714','0805'):
                r=groups[c];self.assertEqual(sum(map(sum,r['matriz'])),r['n'])
                self.assertEqual(sum(b['n'] for b in r['reliability_bins']),r['n'])

    def test_hashes_e_features(self):
        lock=json.loads((OUT/'decisao_congelada.json').read_text())
        self.assertEqual(sha(OUT/'config.json'),lock['config_sha256'])
        for n,h in lock['modelos'].items():self.assertEqual(sha(OUT/f'{n}.joblib'),h)
        for n,h in lock['scripts'].items():self.assertEqual(sha(OUT/n),h)
        self.assertNotIn('target_24h',FEATURES);self.assertNotIn('n_local',FEATURES)
        self.assertNotIn('coverage_status',FEATURES)

if __name__=='__main__':unittest.main()
