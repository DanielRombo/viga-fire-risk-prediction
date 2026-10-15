import ast,csv,json,unittest
from validar_fecho import OUT,ML,ROOT,load,verificar

def rows(name):
    with (OUT/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))

class FechoTests(unittest.TestCase):
    def test_hashes_historicos(self):
        self.assertGreater(len(verificar()),20)

    def test_estado_e_configuracao(self):
        s=load(OUT/'estado_modelo.json'); d=load(ML/'modelo_5b5/decisao.json')
        self.assertEqual(s['estado'],'CANDIDATO EXPERIMENTAL CONGELADO')
        self.assertEqual(s['threshold'],0.15)
        self.assertEqual(s['calibracao'],'sigmoid')
        self.assertFalse(s['validado']);self.assertFalse(s['operacional'])
        self.assertEqual(s['features'],d['final']['features'])
        self.assertEqual(s['fit_end_exclusivo'],'2023-07-01')
        self.assertEqual(s['cal_end_exclusivo'],'2024-01-01')

    def test_metricas_2024_apenas_transcritas(self):
        original=load(ML/'modelo_5b4/metricas_teste.json')
        for r in rows('resultados_5b4_2024.csv'):
            src=original[r['modelo']]['1714']
            for k in ['threshold','pr_auc_ap','roc_auc','precision','recall','f1','brier']:
                self.assertEqual(float(r[k]),src[k])
        self.assertEqual(original['hist_gradient_boosting']['1714']['matriz'],[[269,29],[23,7]])
        self.assertEqual(original['hist_gradient_boosting']['1714']['threshold'],0.28)

    def test_rolling_apenas_transcrito(self):
        candidate=load(ML/'modelo_5b5/decisao.json')['candidato']
        src=next(x for x in load(ML/'modelo_5b5/estabilidade.json') if x['id']==candidate)['estatisticas']
        for r in rows('resultados_5b5_rolling.csv'):
            for k in ['media','mediana','desvio','pior','melhor']:
                self.assertEqual(float(r[k]),src[r['metrica']][k])

    def test_contagens_e_null(self):
        data={r['conjunto']:r for r in rows('dataset_resumo.csv')}
        for r in data.values():
            self.assertEqual(int(r['linhas']),sum(int(r[k]) for k in ['positivos','negativos_condicionais','null']))
        self.assertEqual(int(data['completo']['null']),467)
        self.assertEqual(int(data['elegivel']['linhas']),1693)
        self.assertEqual(load(ML/'cobertura_5b7/resultado.json')['totais']['negativos_condicionais_potenciais'],0)

    def test_fases_e_referencias(self):
        stages=rows('linha_temporal.csv');self.assertEqual(len(stages),10)
        for s in stages:self.assertTrue((ML/s['relatorio']).is_file(),s['relatorio'])
        for n in ['README.md','RELATORIO_FINAL.md','limitacoes.md','estado_modelo.json','config.json']:
            self.assertTrue((OUT/n).is_file(),n)

    def test_sem_execucao_modelo_no_fecho(self):
        for name in ['validar_fecho.py','test_fecho.py']:
            tree=ast.parse((OUT/name).read_text(encoding='utf-8'))
            imports=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):imports.extend(x.name.split('.')[0] for x in node.names)
                elif isinstance(node,ast.ImportFrom):imports.append(node.module.split('.')[0] if node.module else '')
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                    self.assertNotIn(node.func.attr,{'predict','predict_proba','fit','fit_transform'})
            self.assertFalse(set(imports)&{'joblib','pickle','sklearn','experimento','treinar','avaliar'})

    def test_recomendacao_commit_sem_raw(self):
        paths=(OUT/'commit_recomendado.txt').read_text(encoding='utf-8').splitlines()
        self.assertEqual(len(paths),len(set(paths)))
        for path in paths:
            self.assertTrue(path.startswith('experiments/ml_5b/'))
            self.assertTrue((ROOT/path).is_file(),path)
            self.assertNotIn('/_deps/',path)
            self.assertFalse(path.endswith(('.bin','.joblib','.gpkg','.zip','.pdf','.pyc')))
            self.assertNotIn(path.split('/')[-1],{'dataset_completo.csv','dataset_elegivel.csv','exclusoes.csv','scores_teste.csv'})

if __name__=='__main__':unittest.main()
