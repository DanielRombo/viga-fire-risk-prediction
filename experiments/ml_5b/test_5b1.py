"""Validação da junção experimental; não valida completude da fonte."""
import csv
import json
import math
import unittest
from datetime import datetime, timedelta, timezone
from prova_5b1 import OUT, ROOT, janela, digest, INDICES


class ProvaTest(unittest.TestCase):
    def test_limites_janela_24h_e_hora_civil_verao(self):
        T=datetime(2019,7,1,15,tzinfo=timezone.utc)
        def e(t):return {'data_local_sem_fuso_confirmado':t}
        self.assertFalse(janela(e('2019-07-01T16:00:00'),T))
        self.assertTrue(janela(e('2019-07-01T16:00:01'),T))
        self.assertTrue(janela(e('2019-07-02T16:00:00'),T))
        self.assertFalse(janela(e('2019-07-02T16:00:01'),T))

    def test_cadeia_e_inputs_anteriores_a_T(self):
        for nome in ('Lisboa','Vila Real'):
            d=json.loads((OUT/f'{nome}_sequencia.json').read_text(encoding='utf-8'))
            self.assertEqual(len(d),30)
            for i,r in enumerate(d):
                horas=[datetime.fromisoformat(t) for t in r['horas']]
                self.assertEqual(len(set(horas)),24)
                self.assertEqual(horas[-1]-horas[0],timedelta(hours=23))
                referencia=datetime.fromisoformat(r['observacao']['instante_referencia_utc'])
                self.assertEqual(horas[-1],referencia)
                self.assertEqual(referencia.hour,12)
                for k in INDICES:self.assertTrue(math.isfinite(r['indices'][k]) and r['indices'][k]>=0)
                self.assertEqual(r['estado_anterior']['qualidade'],'inicializacao_convencional')
                for k,seed in zip(('ffmc','dmc','dc'),(85,6,15)):
                    self.assertEqual(r['estado_anterior'][k],d[i-1]['indices'][k] if i else seed)

    def test_sem_negativos_nem_disponibilidade_inventados(self):
        with (OUT/'linhas_retrospetivas.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),60)
        self.assertEqual(len({(r['municipio'],r['T_utc']) for r in rows}),60)
        for r in rows:
            self.assertEqual(r['y_certificado'],'')
            self.assertEqual(r['available_at_historico'],'')
            self.assertEqual(r['features_conhecidas_em_T'],'False')
            self.assertEqual(r['operacional'],'False')
            self.assertLess(datetime.fromisoformat(r['max_valid_time']),datetime.fromisoformat(r['T_utc']))
        resumo=json.loads((OUT/'resumo.json').read_text(encoding='utf-8'))
        self.assertEqual(resumo['sha256_eventos_piloto'],digest((OUT.parent/'fase1/ocorrencias_piloto.json').read_bytes()))
        for r in resumo['regioes']:
            self.assertEqual(r['sha256_input'],digest((OUT/f"{r['municipio']}_archive.json").read_bytes()))

    def test_anpc_originais_preservados_e_ilhas_nao_inferidas(self):
        d=json.loads((OUT.parent/'fase1/auditoria.json').read_text(encoding='utf-8'))
        for f in d['fontes']:self.assertEqual(f['sha256'],digest((ROOT/f['ficheiro']).read_bytes()))
        self.assertIn('2019-12-17',d['dias_nacionais_vazios_dentro_extremos'])
        for r in d['pontos']:
            if r['nome'] in ('Funchal','Ponta Delgada'):
                self.assertEqual(r['registos_todas_naturezas'],0)
                self.assertIsNone(r['negativos_certificados'])


if __name__=='__main__':unittest.main()
