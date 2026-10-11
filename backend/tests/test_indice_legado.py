"""Compatibilidade da heurística; não certifica os seus limiares científicos."""
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from routes.alertas import gerar_alertas
from services.fwi import calcular_fwi


class IndiceLegadoTest(unittest.TestCase):
    def test_contrato_e_formula_preservados(self):
        self.assertEqual(calcular_fwi(20, 50, 10, 0), {
            'fwi': 30.0, 'nivel_risco': 'Muito Alto',
            'componentes': {'ffmc': 30.0, 'isi': 30.0}})

    def test_alerta_preserva_id_severidade_e_limiar(self):
        dados = SimpleNamespace(temperatura=20, humidade=50, velocidade_vento=10,
                                precipitacao=0, data_hora=datetime.now(timezone.utc))
        alerta, = gerar_alertas(dados, 'Lisboa')
        self.assertEqual(alerta['id'], 'fwi_Lisboa')
        self.assertEqual(alerta['severidade'], 'media')
        self.assertIn('Índice legado (experimental)', alerta['texto'])
        self.assertNotIn('Risco FWI', alerta['texto'])
        self.assertIn('não é o FWI diário', alerta['meta'])
        dados.precipitacao = 5  # Índice 20: não dispara.
        self.assertEqual(gerar_alertas(dados, 'Lisboa'), [])
