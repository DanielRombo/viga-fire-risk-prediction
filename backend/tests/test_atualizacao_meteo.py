"""Estados de atualização, timestamps e regiões continentais/insulares."""
import importlib.util
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with patch.dict(os.environ, {"DATABASE_URL": "postgresql+psycopg2://test:test@127.0.0.1:1/viga_test"}):
    import config.database
from config.database import get_db
from models.dado_meteorologico import DadoMeteorologico
from models.regiao import Regiao
from routes import meteorologia, regioes, alertas
from routes.auth import get_administrador_atual
from services import scheduler
from services.disponibilidade import estado_observacao
from services.regioes_iniciais import inicializar_regioes, resolver_regioes

HTTP_CLIENT = httpx.AsyncClient


class AtualizacaoMeteoTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.addCleanup(self.engine.dispose)
        with self.engine.begin() as c:
            c.connection.driver_connection.create_function("GeomFromEWKT", 1, lambda x: x)
            c.connection.driver_connection.create_function("AsEWKB", 1, lambda x: None)
            c.execute(text("""CREATE TABLE regioes (id_regiao INTEGER PRIMARY KEY, nome TEXT, distrito TEXT,
                            latitude FLOAT, longitude FLOAT, area_km2 FLOAT, geometria TEXT, created_at DATETIME)"""))
        DadoMeteorologico.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.addCleanup(self.db.close)
        inicializar_regioes(self.db)
        self.regioes = resolver_regioes(self.db)
        self.data = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=20)
        app = FastAPI()
        app.include_router(meteorologia.router)
        app.include_router(regioes.router)
        modelo = ModuleType('services.modelo_ml')
        modelo.prever_risco = Mock(return_value={"nivel_risco_ml": "Baixo"})
        spec = importlib.util.spec_from_file_location('risco_test_atualidade', Path(__file__).resolve().parents[1] / 'routes/risco.py')
        risco = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'services.modelo_ml': modelo}):
            spec.loader.exec_module(risco)
        app.include_router(risco.router)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_administrador_atual] = lambda: object()
        self.client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)

    def resposta(self, request):
        self.assertEqual(request.url.params['timezone'], 'UTC')
        return httpx.Response(200, json={"current": {"time": self.data.isoformat(), "temperature_2m": 20,
                 "relative_humidity_2m": 50, "wind_speed_10m": 10, "precipitation": 0}})

    def atualizar(self, handler=None):
        with patch.object(scheduler, 'SessionLocal', return_value=self.db), \
                patch('httpx.AsyncClient', side_effect=lambda **kwargs:
                      HTTP_CLIENT(transport=httpx.MockTransport(handler or self.resposta), **kwargs)):
            return self.client.post('/meteorologia/atualizar-agora')

    def test_sucesso_timestamp_e_sete_regioes(self):
        response = self.atualizar()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')
        self.assertEqual(len(response.json()['atualizadas']), 28)
        for nome in ('Lisboa', 'Coimbra', 'Porto', 'Faro', 'Vila Real', 'Funchal', 'Ponta Delgada'):
            regiao = next(r for r in self.regioes if r['nome'] == nome)
            data = self.client.get(f"/risco/{regiao['id_regiao']}").json()
            self.assertEqual(data['estado'], 'ok', nome)
            self.assertEqual(datetime.fromisoformat(data['data_hora'].replace('Z', '+00:00')), self.data)
            self.assertEqual(data['dados_meteorologicos']['temperatura'], 20)
            detalhes = self.client.get(f"/regioes/{regiao['id_regiao']}/detalhes").json()
            self.assertEqual(datetime.fromisoformat(detalhes['atual']['data_hora']), self.data)
        monitorizadas = self.client.get('/regioes/monitorizadas').json()['regioes']
        self.assertEqual(next(r for r in monitorizadas if r['nome'] == 'Funchal')['distrito'], 'Madeira')
        self.assertEqual(next(r for r in monitorizadas if r['nome'] == 'Ponta Delgada')['distrito'], 'Açores')

    def test_falha_total_e_timeout_nao_devolvem_sucesso(self):
        for timeout in (False, True):
            def falhar(request):
                if timeout:
                    raise httpx.ReadTimeout('teste', request=request)
                return httpx.Response(500)
            response = self.atualizar(falhar)
            self.assertEqual(response.status_code, 504 if timeout else 503)
            self.assertEqual(response.json()['detail']['status'], 'falha')
            self.assertEqual(self.db.query(DadoMeteorologico).count(), 0)

    def test_sucesso_parcial_identifica_regiao_e_causa(self):
        funchal = next(r for r in self.regioes if r['nome'] == 'Funchal')
        def responder(request):
            if float(request.url.params['latitude']) == funchal['latitude']:
                return httpx.Response(200, json={"current": None})
            return self.resposta(request)
        response = self.atualizar(responder)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'parcial')
        self.assertEqual(len(data['atualizadas']), 27)
        self.assertEqual(data['falhas'][0]['nome'], 'Funchal')
        self.assertEqual(data['falhas'][0]['causa']['codigo'], 'sem_dados')
        self.assertEqual(self.client.get(f"/risco/{funchal['id_regiao']}").json()['estado'], 'sem_dados')

    def test_dados_antigos_na_fonte_nao_sao_rejuvenescidos(self):
        self.data -= timedelta(hours=3)
        response = self.atualizar()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['detail']['falhas'][0]['causa']['codigo'], 'desatualizado')
        self.assertEqual(self.db.query(DadoMeteorologico).count(), 0)

    def test_risco_antigo_sem_calculo_atual(self):
        self.atualizar()
        self.db.query(DadoMeteorologico).update({DadoMeteorologico.data_hora: self.data.replace(tzinfo=None) - timedelta(hours=3)})
        self.db.commit()
        data = self.client.get(f"/risco/{self.regioes[0]['id_regiao']}").json()
        self.assertEqual(data['estado'], 'desatualizado')
        self.assertIsNone(data['fwi'])
        self.assertIsNone(data['ml'])

    def test_commit_falhado_nao_devolve_sucesso(self):
        with patch.object(self.db, 'commit', side_effect=SQLAlchemyError('falha simulada')):
            self.assertEqual(self.atualizar().status_code, 500)
        self.assertEqual(self.db.query(DadoMeteorologico).count(), 0)

    def test_limite_duas_horas(self):
        agora = datetime.now(timezone.utc)
        dado = SimpleNamespace(temperatura=20, humidade=50, velocidade_vento=10, precipitacao=0,
                               data_hora=agora - timedelta(hours=2))
        self.assertEqual(estado_observacao(dado, agora), 'ok')
        dado.data_hora -= timedelta(seconds=1)
        self.assertEqual(estado_observacao(dado, agora), 'desatualizado')

    def test_alerta_usa_hora_da_observacao(self):
        dado = SimpleNamespace(temperatura=20, humidade=50, velocidade_vento=40, precipitacao=0,
                               data_hora=self.data)
        resultado = alertas.gerar_alertas(dado, 'Funchal')
        self.assertTrue(resultado)
        self.assertTrue(all(a['meta'].startswith(self.data.strftime('%H:%M')) for a in resultado))


if __name__ == '__main__':
    unittest.main()
