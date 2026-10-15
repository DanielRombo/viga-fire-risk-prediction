import json
import unittest
from datetime import datetime,timezone,timedelta
from comparar_timestamps import OUT,janela,stats

class ComparacaoTests(unittest.TestCase):
    def test_join_exato(self):
        r=json.loads((OUT/'comparacao_temporal.json').read_text())
        self.assertEqual(r['comuns'],24170)
        self.assertEqual(r['sgif_sem_prdf']+r['prdf_sem_sgif'],0)
        self.assertEqual(r['ids_sgif_duplicados']+r['ids_prdf_duplicados'],0)
        self.assertEqual(r['invalidos'],[])
        self.assertEqual(r['relogio']['global_']['min'],0)
        self.assertEqual(r['relogio']['global_']['max'],0)
        self.assertEqual(r['rastreio']['timestamps_inalterados'],24170)

    def test_null_preservado(self):
        r=json.loads((OUT/'comparacao_temporal.json').read_text())
        w=r['janelas_por_municipio_ano'].values()
        self.assertEqual(sum(v.get('presenca_diferente_local_vs_utc',0) for v in w),32)
        self.assertEqual(sum(v.get('ja_null',0) for v in w),32)
        self.assertEqual(sum(v.get('classificado',0) for v in w),0)
        self.assertEqual(set(r['relogio']['por_ano']),{'2022','2023','2024'})

    def test_limites_janela(self):
        t=datetime(2023,7,1,15,tzinfo=timezone.utc)
        self.assertEqual(janela(t),(t-timedelta(days=1)).isoformat())
        self.assertEqual(janela(t+timedelta(seconds=1)),t.isoformat())

    def test_estatisticas_sinal_e_absoluto(self):
        s=stats([-60,0,60]);self.assertEqual(s['media'],0)
        self.assertEqual(s['percentagem_abs_ate']['60'],100)
        self.assertAlmostEqual(s['percentagem_abs_ate']['5'],100/3)

if __name__=='__main__':unittest.main()
