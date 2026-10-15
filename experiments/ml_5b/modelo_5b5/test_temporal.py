import json
import unittest
import joblib
import numpy as np
from experimento import OUT,DATA,dados,dividir,sha

class TemporalTests(unittest.TestCase):
    def test_2024_excluido(self):
        d=dados();self.assertEqual(set(d.t.dt.year),{2022,2023});self.assertEqual(len(d),1095)

    def test_purga_e_ordem(self):
        cfg=json.loads((OUT/'config.json').read_text());d=dados();seen=set()
        for _,a,b,c in cfg['folds']:
            fit,cal,test=dividir(d,a,b,c)
            self.assertLess(fit.fim.max(),cal.t.min());self.assertLess(cal.fim.max(),test.t.min())
            keys=set(zip(test.municipio,test.data_T));self.assertFalse(keys&seen);seen|=keys
            self.assertEqual(fit.target_24h.nunique(),2)

    def test_baselines_e_bins(self):
        rows=json.loads((OUT/'resultados_folds.json').read_text())
        for r in rows:
            self.assertEqual(sum(b['n'] for b in r['reliability_bins']),r['n'])
            self.assertEqual(sum(map(sum,r['matriz'])),r['n'])
            if r['modelo']=='prevalencia' and r['pr_auc_ap'] is not None:
                self.assertAlmostEqual(r['pr_auc_ap'],r['prevalencia'])

    def test_todos_folds_e_ablation(self):
        rows=json.loads((OUT/'resultados_folds.json').read_text())
        ids={r['id'] for r in rows if r['grupo']=='1714'}
        self.assertEqual(len(ids),61)
        for cid in ids:self.assertEqual({r['fold'] for r in rows if r['id']==cid and r['grupo']=='1714'},{'F1','F2','F3','F4'})

    def test_decisao_por_criterio(self):
        d=json.loads((OUT/'decisao.json').read_text());c=d['candidato']
        eligible=[r for r in d['ranking'] if r['elegivel']]
        self.assertEqual(c,eligible[0]['id'] if eligible else None)
        if c:
            self.assertGreater(eligible[0]['pior_ganho_ap'],0)
            self.assertGreater(eligible[0]['mediana_ganho_brier'],0)
            a=joblib.load(OUT/'candidato.joblib')
            self.assertEqual(a['threshold'],d['final']['threshold'])
            self.assertNotIn('target_24h',a['features'])

    def test_integridade(self):
        m=json.loads((OUT/'manifesto.json').read_text())
        self.assertEqual(sha(DATA/'dataset_elegivel.csv'),m['dataset_sha256'])
        for n,h in m['checksums'].items():self.assertEqual(sha(OUT/n),h,n)

if __name__=='__main__':unittest.main()
