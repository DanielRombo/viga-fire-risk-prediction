"""Contract tests using simulated HTTP sources and an in-memory SQLite DB."""
import asyncio
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@127.0.0.1:1/viga_test"}):
    from config.database import get_db
    from models.dado_meteorologico import DadoMeteorologico
    from routes import alertas, incendios, ipma, meteorologia, regioes
    from services import open_meteo
    from services.disponibilidade import estado_observacao

HTTP_CLIENT = httpx.AsyncClient
CSV_HEADER = "latitude,longitude,acq_date,acq_time\n"
ENDPOINTS = ["/api/incendios/focos", "/api/ipma/previsao", "/api/regioes/concelhos",
             "/api/meteorologia?latitude=38.7&longitude=-9.1"]


class ExternalSourceTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        for module in (incendios, ipma, meteorologia, regioes):
            app.include_router(module.router, prefix="/api")
        self.db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def source(self, handler):
        return patch("httpx.AsyncClient", side_effect=lambda **kwargs:
                     HTTP_CLIENT(transport=httpx.MockTransport(handler), **kwargs))

    def test_successful_empty_lists(self):
        for endpoint, payload, key in [
            (ENDPOINTS[0], CSV_HEADER, "focos"),
            (ENDPOINTS[1], {"data": []}, "previsoes"),
            (ENDPOINTS[2], {"elements": []}, "concelhos"),
        ]:
            with self.subTest(endpoint=endpoint), self.source(lambda request:
                    httpx.Response(200, text=payload) if isinstance(payload, str) else httpx.Response(200, json=payload)):
                response = self.client.get(endpoint)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"total": 0, key: []})

    def test_http_failure_is_not_empty_success(self):
        for status in (401, 429, 500, 503):
            for endpoint in ENDPOINTS:
                with self.subTest(status=status, endpoint=endpoint), self.source(lambda request: httpx.Response(status, text="upstream failure")):
                    response = self.client.get(endpoint)
                    self.assertEqual(response.status_code, 502)
                    self.assertEqual(response.json()["detail"]["codigo"], "erro_fonte")
                    self.assertNotIn("focos", response.json())

    def test_timeouts_and_connection_errors(self):
        for error, status in [(httpx.ReadTimeout, 504), (httpx.ConnectError, 502)]:
            def fail(request):
                raise error("simulated failure", request=request)
            for endpoint in ENDPOINTS:
                with self.subTest(endpoint=endpoint, error=error), self.source(fail):
                    self.assertEqual(self.client.get(endpoint).status_code, status)

    def test_malformed_success_is_explicit_error(self):
        for endpoint in ENDPOINTS:
            with self.subTest(endpoint=endpoint), self.source(lambda request: httpx.Response(200, text="invalid response")):
                response = self.client.get(endpoint)
                self.assertEqual(response.status_code, 502)
                self.assertEqual(response.json()["detail"]["codigo"], "dados_incompletos")

    def test_nasa_does_not_silently_drop_invalid_rows(self):
        payload = CSV_HEADER + "39,-8,2026-09-30,1200\ninvalid,-8,2026-09-30,1200\n"
        with self.source(lambda request: httpx.Response(200, text=payload)):
            self.assertEqual(self.client.get(ENDPOINTS[0]).status_code, 502)

    def test_nasa_valid_observation(self):
        with self.source(lambda request: httpx.Response(200, text=CSV_HEADER + "39,-8,2026-09-30,1200\n")):
            response = self.client.get(ENDPOINTS[0])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["total"], 1)

    def test_meteo_zero_missing_and_partial_are_distinct(self):
        complete = {k: 0 for k in ("temperature_2m", "relative_humidity_2m", "wind_speed_10m", "precipitation")}
        for current, status in [(complete, 200), (None, 503), ({}, 503),
                                ({"temperature_2m": 0}, 502), ({**complete, "precipitation": None}, 502)]:
            with self.subTest(current=current), self.source(lambda request: httpx.Response(200, json={"current": current})):
                response = self.client.get(ENDPOINTS[3])
                self.assertEqual(response.status_code, status)
                if status == 200:
                    self.assertEqual(response.json()["current"]["precipitation"], 0)

    def test_incomplete_ipma_and_overpass(self):
        for endpoint, payload in [(ENDPOINTS[1], {"data": [{}]}),
                                  (ENDPOINTS[2], {"elements": [{}]}),
                                  (ENDPOINTS[2], {"elements": [], "remark": "runtime error"})]:
            with self.subTest(endpoint=endpoint), self.source(lambda request: httpx.Response(200, json=payload)):
                self.assertEqual(self.client.get(endpoint).status_code, 502)

    def test_failed_source_is_not_persisted(self):
        with self.source(lambda request: httpx.Response(500)):
            with self.assertRaises(HTTPException):
                asyncio.run(open_meteo.guardar_dados_meteorologicos(39, -8, 1, self.db))
        self.db.add.assert_not_called()
        self.db.commit.assert_not_called()

    def test_region_fallback_propagates_source_error(self):
        self.db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(latitude=39, longitude=-8)
        self.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        with self.source(lambda request: httpx.Response(500)):
            self.assertEqual(self.client.get("/api/regioes/1/detalhes").status_code, 502)

    def test_region_without_data_or_coordinates(self):
        self.db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
            id_regiao=1, nome="Regiao", distrito="Distrito", latitude=None, longitude=None)
        self.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        response = self.client.get("/api/regioes/1/detalhes")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["estado"], "sem_dados")
        self.assertIsNone(response.json()["atual"])

    def test_region_keeps_history_without_presenting_stale_risk_as_current(self):
        self.db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
            id_regiao=1, nome="Regiao", distrito="Distrito", latitude=39, longitude=-8)
        observation = SimpleNamespace(temperatura=20, humidade=50, velocidade_vento=0,
                                      precipitacao=0, data_hora=datetime.now(timezone.utc) - timedelta(hours=3))
        self.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [observation]
        response = self.client.get("/api/regioes/1/detalhes")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["estado"], "desatualizado")
        self.assertIsNone(data["atual"]["fwi"])
        self.assertIsNotNone(data["historico"][0]["fwi"])
        observation.humidade = float('inf')
        response = self.client.get("/api/regioes/1/detalhes")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["estado"], "dados_incompletos")
        self.assertIsNone(response.json()["atual"]["humidade"])


class AlertCoverageTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.addCleanup(self.engine.dispose)
        # Only columns read by the alert query; no PostGIS dependency in SQLite.
        with self.engine.begin() as connection:
            connection.execute(text("CREATE TABLE regioes (id_regiao INTEGER PRIMARY KEY, nome TEXT)"))
        DadoMeteorologico.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.addCleanup(self.db.close)
        app = FastAPI()
        app.include_router(alertas.router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def region(self, identifier):
        self.db.execute(text("INSERT INTO regioes VALUES (:id, :nome)"), {"id": identifier, "nome": f"Regiao {identifier}"})
        self.db.commit()

    def observation(self, identifier, **values):
        fields = dict(id_regiao=identifier, data_hora=datetime.now(timezone.utc).replace(tzinfo=None),
                      temperatura=0, humidade=100, velocidade_vento=0, precipitacao=0)
        fields.update(values)
        self.db.add(DadoMeteorologico(**fields))
        self.db.commit()

    def response(self):
        response = self.client.get("/api/alertas")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("ok_nacional", response.text)
        self.assertNotIn("Condições normais", response.text)
        return response.json()

    def test_empty_database(self):
        data = self.response()
        self.assertEqual(data["estado"], "sem_dados")
        self.assertEqual(data["alertas"], [])
        self.assertEqual(data["cobertura"]["regioes_avaliadas"], 0)

    def test_registered_regions_without_observations(self):
        self.region(1)
        self.assertEqual(self.response()["estado"], "sem_dados")

    def test_partial_coverage(self):
        self.region(1)
        self.region(2)
        self.observation(1)
        data = self.response()
        self.assertEqual(data["estado"], "cobertura_parcial")
        self.assertEqual(data["cobertura"]["regioes_avaliadas"], 1)
        self.assertEqual(data["cobertura"]["sem_dados"], 1)

    def test_valid_zero_alerts(self):
        self.region(1)
        self.observation(1)
        data = self.response()
        self.assertEqual(data["estado"], "ok")
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["alertas"], [])

    def test_partial_values_and_stale_observations(self):
        self.region(1)
        self.observation(1, humidade=None)
        self.assertEqual(self.response()["estado"], "dados_incompletos")
        self.db.query(DadoMeteorologico).delete()
        self.observation(1, data_hora=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=3))
        self.assertEqual(self.response()["estado"], "desatualizado")

    def test_latest_observation_per_region_without_limit_ten(self):
        for identifier in range(1, 13):
            self.region(identifier)
            self.observation(identifier, velocidade_vento=40 if identifier == 1 else 0)
        # Many newer rows of one region must not hide another region's alert.
        for _ in range(15):
            self.observation(12)
        data = self.response()
        self.assertEqual(data["cobertura"]["regioes_avaliadas"], 12)
        self.assertTrue(any(a["id"] == "vento_Regiao 1" for a in data["alertas"]))
        self.observation(1)
        self.assertEqual(self.response()["total"], 0)

    def test_zero_humidity_is_not_missing(self):
        self.region(1)
        self.observation(1, humidade=0)
        data = self.response()
        self.assertEqual(data["estado"], "ok")
        self.assertTrue(any(a["id"].startswith("humidade_") for a in data["alertas"]))

    def test_nonfinite_and_future_observations_are_incomplete(self):
        data = SimpleNamespace(temperatura=float('inf'), humidade=50, velocidade_vento=0,
                               precipitacao=0, data_hora=datetime.now(timezone.utc))
        self.assertEqual(estado_observacao(data), "dados_incompletos")
        data.temperatura = 20
        data.data_hora += timedelta(hours=1)
        self.assertEqual(estado_observacao(data), "dados_incompletos")


if __name__ == "__main__":
    unittest.main()
