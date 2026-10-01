"""Inputs de observação e ensemble com disponibilidade parcial."""
from datetime import datetime, timezone
from pathlib import Path
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import modelo_ml as ml


class InferenciaMLTests(unittest.TestCase):
    def setUp(self):
        self.dados = dict(temperatura=0, humidade=0, velocidade_vento=0, precipitacao=0,
                          ffmc=0, dmc=0, dc=0, isi=0, distrito='Lisboa', latitude=38.7169,
                          longitude=-9.1399, data_hora=datetime(2024, 7, 1, 23, 30, tzinfo=timezone.utc))
        self.kaggle, self.anpc = Mock(), Mock()
        self.kaggle.predict_proba.return_value = np.array([[0.8, 0.2]])
        self.anpc.predict_proba.return_value = np.array([[0.2, 0.8]])
        self.scaler_k, self.scaler_a = Mock(), Mock()
        self.scaler_k.transform.side_effect = lambda x: x
        self.scaler_a.transform.side_effect = lambda x: x
        for nome, valor in [('modelo', self.kaggle), ('modelo_anpc', self.anpc),
                            ('scaler', self.scaler_k), ('scaler_anpc', self.scaler_a)]:
            p = patch.object(ml, nome, valor)
            p.start()
            self.addCleanup(p.stop)

    def test_ordem_coordenadas_timestamp_e_encoder_reais(self):
        resultado = ml.prever_risco(self.dados)
        np.testing.assert_array_equal(self.scaler_k.transform.call_args.args[0], [[0, 0, 0, 0, 0, 0, 0, 0, 7, 2]])
        codigo = ml.encoder_distrito.transform(['LISBOA'])[0]
        np.testing.assert_array_equal(self.scaler_a.transform.call_args.args[0], [[7, 0, 1, 2024, codigo, 38.7169, -9.1399]])
        self.assertEqual(resultado['estado'], 'ok')
        self.assertEqual(resultado['probabilidade_incendio'], 0.56)
        self.assertEqual(resultado['pesos_aplicados'], {'prob_meteorologico': 0.4, 'prob_historico_portugal': 0.6})

    def test_apenas_kaggle_nao_reduz_probabilidade(self):
        self.dados['distrito'] = 'Desconhecido'
        resultado = ml.prever_risco(self.dados)
        self.assertEqual(resultado['estado'], 'parcial')
        self.assertEqual(resultado['probabilidade_incendio'], 0.2)
        self.anpc.predict_proba.assert_not_called()

    def test_apenas_anpc_nao_amplifica_probabilidade(self):
        del self.dados['dmc']
        resultado = ml.prever_risco(self.dados)
        self.assertEqual(resultado['probabilidade_incendio'], 0.8)
        self.assertEqual(resultado['estado'], 'parcial')
        self.kaggle.predict_proba.assert_not_called()
        self.assertIn('dmc', resultado['disponibilidade']['prob_meteorologico']['campos'])

    def test_nenhum_modelo_sem_constantes(self):
        resultado = ml.prever_risco({})
        self.assertEqual(resultado['estado'], 'indisponivel')
        self.assertIsNone(resultado['probabilidade_incendio'])
        self.kaggle.predict_proba.assert_not_called()
        self.anpc.predict_proba.assert_not_called()

    def test_indices_invalidos_e_coordenadas_fora_dos_limites(self):
        for campo, valor in [('ffmc', -1), ('dmc', float('nan')), ('isi', float('inf')),
                             ('humidade', 101), ('dc', False), ('latitude', 91), ('longitude', -181)]:
            resposta = ml.prever_risco({**self.dados, campo: valor})
            chave = 'prob_historico_portugal' if campo in ('latitude', 'longitude') else 'prob_meteorologico'
            self.assertEqual(resposta['disponibilidade'][chave]['estado'], 'indisponivel')

    def test_todos_os_campos_obrigatorios_e_zeros(self):
        for campo in self.dados:
            with self.subTest(campo=campo):
                resultado = ml.prever_risco({**self.dados, campo: None})
                modelo = 'prob_historico_portugal' if campo in ('distrito', 'latitude', 'longitude') else 'prob_meteorologico'
                self.assertEqual(resultado['disponibilidade'][modelo]['estado'], 'indisponivel')
                if campo == 'data_hora':
                    self.assertEqual(resultado['estado'], 'indisponivel')
        self.anpc.predict_proba.return_value = np.array([[1, 0]])
        del self.dados['ffmc']
        self.assertEqual(ml.prever_risco(self.dados)['probabilidade_incendio'], 0)

    def test_distritos_conhecidos_e_ilhas(self):
        for distrito in ('Lisboa', ' lisboa ', 'Évora', 'Vila Real'):
            self.assertEqual(ml.prever_risco({**self.dados, 'distrito': distrito})['estado'], 'ok')
        for distrito in ('Açores', 'Madeira', 'Desconhecido', ''):
            self.assertEqual(ml.prever_risco({**self.dados, 'distrito': distrito})['estado'], 'parcial')

    def test_modelo_falhado_ou_probabilidade_invalida(self):
        for resposta in (float('nan'), float('inf'), 1.1, -0.1):
            self.kaggle.predict_proba.return_value = np.array([[0, resposta]])
            self.assertEqual(ml.prever_risco(self.dados)['probabilidade_incendio'], 0.8)
        self.kaggle.predict_proba.side_effect = RuntimeError('teste')
        self.assertEqual(ml.prever_risco(self.dados)['estado'], 'parcial')
        self.anpc.predict_proba.side_effect = RuntimeError('teste')
        self.assertEqual(ml.prever_risco(self.dados)['estado'], 'indisponivel')

    def test_artefacto_indisponivel_em_memoria(self):
        with patch.object(ml, 'modelo', None):
            self.assertEqual(ml.prever_risco(self.dados)['probabilidade_incendio'], 0.8)
        with patch.object(ml, 'modelo_anpc', None):
            self.assertEqual(ml.prever_risco(self.dados)['probabilidade_incendio'], 0.2)
        with patch.object(ml, 'modelo', None), patch.object(ml, 'modelo_anpc', None):
            self.assertEqual(ml.prever_risco(self.dados)['estado'], 'indisponivel')

    def test_data_sem_fuso_da_bd_e_utc(self):
        self.dados['data_hora'] = self.dados['data_hora'].replace(tzinfo=None)
        ml.prever_risco(self.dados)
        self.assertEqual(self.scaler_a.transform.call_args.args[0][0][1], 0)

    def test_rota_envia_regiao_e_observacao_sem_indices_inventados(self):
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql+psycopg2://teste:teste@127.0.0.1:1/viga_test'}):
            from routes import risco
        db = MagicMock()
        observado = datetime.now(timezone.utc)
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = SimpleNamespace(
            temperatura=0, humidade=0, velocidade_vento=0, precipitacao=0, data_hora=observado)
        db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
            distrito='Coimbra', latitude=40.2033, longitude=-8.4103)
        with patch.object(risco, 'prever_risco', return_value={}) as prever:
            risco.get_risco_regiao(1234, db)
        dados = prever.call_args.args[0]
        self.assertEqual(dados['data_hora'], observado)
        self.assertEqual(dados['distrito'], 'Coimbra')
        self.assertEqual(dados['latitude'], 40.2033)
        self.assertEqual(dados['longitude'], -8.4103)
        self.assertTrue(all(k not in dados for k in ('ffmc', 'dmc', 'dc', 'isi')))
