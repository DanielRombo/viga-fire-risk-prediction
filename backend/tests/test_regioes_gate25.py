"""Resolução canónica em BD isolada; fontes meteorológicas simuladas."""
import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from sqlalchemy.orm import Session
from fastapi import FastAPI
from fastapi.testclient import TestClient
import test_regioes_iniciais as fixture
from models.regiao import Regiao
from models.dado_meteorologico import DadoMeteorologico
from models.fwi_diario import FWIDiario
from services.regioes_iniciais import CATALOGO, resolver_regioes, encontrar, existentes, inicializar_regioes
from services import scheduler, processamento_fwi
from routes.regioes import router
from config.database import get_db


class CanonicasTests(unittest.TestCase):
    setUp = fixture.RegioesIniciaisTests.setUp

    def preparar(self):
        # IDs da fotografia confirmada, apenas como fixture: o resolvedor não os conhece.
        self.esperados = {}
        for i, ponto in enumerate(CATALOGO):
            self.db.add(Regiao(id_regiao=3260+i, **{k:v for k,v in ponto.items() if k != 'recolha_automatica'}))
            if ponto['recolha_automatica']:
                self.esperados[ponto['nome']] = 3260+i
        self.db.add(Regiao(id_regiao=1, nome='Lisboa', distrito='Lisboa', latitude=38.72, longitude=-9.14))
        self.db.flush()
        self.db.add(DadoMeteorologico(id_regiao=1, data_hora=datetime(2026,1,1), temperatura=12))
        self.db.commit()

    def test_28_ids_e_historico_intacto(self):
        self.preparar()
        self.assertEqual(inicializar_regioes(self.db), 0)
        self.assertEqual({r['nome']:r['id_regiao'] for r in resolver_regioes(self.db)}, self.esperados)
        self.assertEqual(self.esperados['Lisboa'], 3260)
        self.assertEqual(self.db.get(Regiao, 1).latitude, 38.72)
        self.assertEqual(self.db.query(DadoMeteorologico).one().id_regiao, 1)
        self.assertEqual(self.db.query(DadoMeteorologico).one().temperatura, 12)

    def test_homonimos_ordem_e_normalizacao(self):
        self.preparar()
        self.db.add_all([
            Regiao(id_regiao=2, nome='Lisboa', distrito='Desconhecido', latitude=38.7169, longitude=-9.1399),
            Regiao(id_regiao=3, nome='Lisboa', distrito='Porto', latitude=38.7169, longitude=-9.1399)])
        self.db.get(Regiao, 3260).nome = ' LISBOA '
        self.db.commit()
        for registos in (existentes(self.db), list(reversed(existentes(self.db)))):
            self.assertEqual(encontrar(CATALOGO[0], registos).id_regiao, 3260)

    def test_sem_coordenadas_exatas_nao_escolhe_legado(self):
        self.preparar()
        self.db.get(Regiao, 3260).latitude = 38.71
        self.db.commit()
        with self.assertRaisesRegex(ValueError, 'não preparada'):
            resolver_regioes(self.db)

    def test_endpoint_monitorizadas_e_pesquisa_legada(self):
        self.preparar()
        app = FastAPI()
        app.include_router(router, prefix='/api')
        app.dependency_overrides[get_db] = lambda: self.db
        with TestClient(app) as client:
            resposta = client.get('/api/regioes/monitorizadas')
            self.assertEqual(resposta.status_code, 200)
            pontos = resposta.json()['regioes']
            self.assertEqual({r['nome']:r['id_regiao'] for r in pontos}, self.esperados)
            # A seleção inicial do dashboard usa Lisboa nesta lista.
            self.assertEqual(next(r['id_regiao'] for r in pontos if r['nome']=='Lisboa'), 3260)
            resposta = client.get('/api/regioes/pesquisa', params={'q':'Lisboa'})
            self.assertEqual(resposta.status_code, 200)
            self.assertIn('"id_regiao":1,', resposta.text)

    def test_scheduler_meteo_usa_canonicas_sem_mover_historico(self):
        self.preparar()
        fonte = AsyncMock(return_value={'current': {'time':datetime.now(timezone.utc).isoformat(),
            'temperature_2m':20, 'relative_humidity_2m':50, 'wind_speed_10m':10, 'precipitation':0}})
        with patch.object(scheduler, 'SessionLocal', return_value=self.db), \
                patch.object(scheduler, 'obter_dados_meteorologicos', fonte):
            asyncio.run(scheduler._atualizar_dados())
        self.assertEqual(fonte.await_count, 28)
        self.assertEqual(fonte.await_args_list[0].args, (38.7169, -9.1399))
        self.assertEqual({r.id_regiao for r in self.db.query(DadoMeteorologico).filter(DadoMeteorologico.id_regiao != 1)}, set(self.esperados.values()))
        self.assertEqual(self.db.query(DadoMeteorologico).filter_by(id_regiao=1).one().temperatura, 12)

    def test_scheduler_fwi_resolve_28_canonicas(self):
        self.preparar()
        FWIDiario.__table__.create(self.engine)
        self.addCleanup(lambda: FWIDiario.__table__.drop(self.engine))
        processar = AsyncMock(return_value={'estado':'estado_anterior_ausente', 'calculados':0})
        with patch('services.reconstrucao_fwi.atual', return_value=None), \
                patch.object(processamento_fwi, 'processar_regiao', processar):
            resultados = asyncio.run(processamento_fwi.executar_ciclo_fwi(lambda: Session(self.engine)))
        self.assertEqual(len(resultados), 28)
        self.assertEqual(processar.await_count, 28)
        self.assertEqual({c.args[1]['id_regiao'] for c in processar.await_args_list}, set(self.esperados.values()))
        lisboa = processar.await_args_list[0].args[1]
        self.assertEqual((lisboa['id_regiao'], lisboa['latitude'], lisboa['longitude']), (3260, 38.7169, -9.1399))
