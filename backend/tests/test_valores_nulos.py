"""Zeros reais e ausência de valores nos cálculos e nas respostas da API."""
import importlib.util
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with patch.dict(os.environ, {"DATABASE_URL": "postgresql+psycopg2://test:test@127.0.0.1:1/viga_test"}):
    from config.database import get_db
from routes import alertas, regioes
from services.fwi import calcular_fwi, calcular_risco_regiao


class ValoresNulosTests(unittest.TestCase):
    def test_fwi_preserva_zeros_e_formula(self):
        self.assertEqual(calcular_fwi(0, 0, 0, 0)['fwi'], 24)
        self.assertEqual(calcular_fwi(0, 100, 0, 0)['fwi'], 0)
        self.assertEqual(calcular_fwi(20, 50, 10, 0)['fwi'], 30)
        self.assertEqual(calcular_risco_regiao(dict(temperatura=0, humidade=0, velocidade_vento=0, precipitacao=0))['fwi'], 24)

    def test_fwi_nao_calcula_com_valores_ausentes_ou_invalidos(self):
        for indice in range(4):
            for valor in (None, float('nan'), float('inf'), False, '0'):
                with self.subTest(indice=indice, valor=valor):
                    argumentos = [0, 0, 0, 0]
                    argumentos[indice] = valor
                    resultado = calcular_fwi(*argumentos)
                    self.assertEqual(resultado['estado'], 'dados_incompletos')
                    self.assertIsNone(resultado['fwi'])
                    self.assertIsNone(resultado['componentes'])

    def test_campos_omitidos_nao_recebem_defaults(self):
        completo = dict(temperatura=0, humidade=0, velocidade_vento=0, precipitacao=0)
        for campo in completo:
            dados = {k: v for k, v in completo.items() if k != campo}
            self.assertEqual(calcular_risco_regiao(dados)['estado'], 'dados_incompletos')

    def test_gerador_de_alertas_nao_compara_fwi_ausente(self):
        dado = SimpleNamespace(temperatura=None, humidade=0, velocidade_vento=0, precipitacao=0,
                               data_hora=datetime.now(timezone.utc))
        resultado = alertas.gerar_alertas(dado, 'Lisboa')
        self.assertFalse(any(a['id'] == 'fwi_Lisboa' for a in resultado))


class RotasValoresNulosTests(unittest.TestCase):
    def setUp(self):
        modelo = ModuleType('services.modelo_ml')
        modelo.prever_risco = Mock(return_value={'probabilidade_incendio': 0, 'nivel_risco_ml': 'Baixo'})
        spec = importlib.util.spec_from_file_location('risco_test_nulos', Path(__file__).resolve().parents[1] / 'routes/risco.py')
        self.risco = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'services.modelo_ml': modelo}):
            spec.loader.exec_module(self.risco)
        app = FastAPI()
        for rota in (self.risco, regioes, alertas):
            app.include_router(rota.router)
        self.db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.dado = SimpleNamespace(temperatura=0, humidade=0, velocidade_vento=0, precipitacao=0,
                                    data_hora=datetime.now(timezone.utc))
        self.db.query.return_value.filter.return_value.order_by.return_value.first.return_value = self.dado
        self.db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
            id_regiao=1, nome='Lisboa', distrito='Lisboa', latitude=38.7, longitude=-9.1)
        self.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [self.dado]
        self.db.query.return_value.outerjoin.return_value.outerjoin.return_value.all.return_value = [(1, 'Lisboa', self.dado)]

    def test_zeros_preservados_nas_tres_rotas(self):
        risco = self.client.get('/risco/1').json()
        self.assertEqual(risco['estado'], 'ok')
        self.assertTrue(all(v == 0 for v in risco['dados_meteorologicos'].values()))
        self.assertEqual(risco['ml']['probabilidade_incendio'], 0)
        detalhes = self.client.get('/regioes/1/detalhes').json()
        self.assertEqual(detalhes['estado'], 'ok')
        self.assertEqual(detalhes['atual']['temperatura'], 0)
        self.assertEqual(detalhes['atual']['humidade'], 0)
        avisos = self.client.get('/alertas').json()
        self.assertEqual(avisos['estado'], 'ok')
        self.assertTrue(any(a['id'] == 'humidade_Lisboa' for a in avisos['alertas']))

    def test_incompletos_nao_alimentam_fwi_nem_ml(self):
        for campo in ('temperatura', 'humidade', 'velocidade_vento', 'precipitacao'):
            with self.subTest(campo=campo):
                setattr(self.dado, campo, None)
                self.risco.prever_risco.reset_mock()
                with patch.object(self.risco, 'calcular_risco_regiao') as calcular, \
                        patch('services.fwi.calcular_fwi') as calcular_detalhe, \
                        patch.object(alertas, 'calcular_fwi') as calcular_alertas:
                    risco = self.client.get('/risco/1').json()
                    detalhes = self.client.get('/regioes/1/detalhes').json()
                    avisos = self.client.get('/alertas').json()
                    for resposta in (risco, detalhes, avisos):
                        self.assertEqual(resposta['estado'], 'dados_incompletos')
                    self.assertIsNone(risco['dados_meteorologicos'][campo])
                    self.assertIsNone(risco['fwi'])
                    self.assertIsNone(risco['ml'])
                    self.assertIsNone(detalhes['atual'][campo])
                    calcular.assert_not_called()
                    calcular_detalhe.assert_not_called()
                    calcular_alertas.assert_not_called()
                    self.risco.prever_risco.assert_not_called()
                setattr(self.dado, campo, 0)
