"""HTTP authorization checks with real JWT validation and no external I/O.

Run from the repository root:
    python -B -m unittest discover -s backend/tests -v
"""

import os
import sys
import unittest
from datetime import timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import the routers, never main.py (which creates tables and starts jobs).
with patch.dict(os.environ, {
    "DATABASE_URL": "postgresql://test:test@127.0.0.1:1/viga_test",
    "SECRET_KEY": "viga-write-authorization-test-key-only",
}):
    from config.database import get_db
    from routes import incendios, meteorologia, regioes
    from services import auth


class WriteAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.user = SimpleNamespace(email="admin@example.test", ativo=True, admin=True)
        self.db = MagicMock()
        self.db.query.return_value.filter.return_value.first.return_value = self.user

        self.app = FastAPI()
        for router in (meteorologia.router, incendios.router, regioes.router):
            self.app.include_router(router, prefix="/api")
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

        self.weather = AsyncMock(return_value=SimpleNamespace(id_dado=123))
        self.fires = AsyncMock(return_value={"focos_guardados": 1})
        self.regions = AsyncMock(return_value={"regioes_inseridas": 1})
        self.update = AsyncMock()
        scheduler = ModuleType("services.scheduler")
        scheduler.atualizar_dados_meteorologicos = self.update
        patches = [
            patch.object(auth, "SECRET_KEY", "viga-write-authorization-test-key-only"),
            patch.object(meteorologia, "guardar_dados_meteorologicos", self.weather),
            patch.object(incendios, "guardar_focos_incendio", self.fires),
            patch.object(regioes, "popular_regioes", self.regions),
            patch.dict(sys.modules, {"services.scheduler": scheduler}),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

        self.operations = [
            ("/api/meteorologia/guardar?latitude=38.7&longitude=-9.1&id_regiao=1", self.weather),
            ("/api/meteorologia/atualizar-agora", self.update),
            ("/api/incendios/guardar", self.fires),
            ("/api/regioes/popular", self.regions),
        ]

    def headers(self, **kwargs):
        token = auth.criar_token({"sub": self.user.email}, **kwargs)
        return {"Authorization": f"Bearer {token}"}

    def test_region_override_is_rejected(self):
        response = self.client.post("/api/incendios/guardar?id_regiao=1", headers=self.headers())
        self.assertEqual(response.status_code, 422)
        self.fires.assert_not_called()

    def assert_rejected(self, headers, expected):
        for url, operation in self.operations:
            with self.subTest(url=url):
                response = self.client.post(url, headers=headers)
                self.assertEqual(response.status_code, expected, response.text)
                if expected == 401:
                    self.assertEqual(response.headers.get("www-authenticate"), "Bearer")
        for _, operation in self.operations:
            operation.assert_not_called()

    def test_missing_token(self):
        self.assert_rejected({}, 401)

    def test_invalid_token(self):
        self.assert_rejected({"Authorization": "Bearer invalid-token"}, 401)

    def test_expired_token(self):
        self.assert_rejected(self.headers(expires_delta=timedelta(minutes=-1)), 401)

    def test_non_admin(self):
        self.user.admin = False
        self.assert_rejected(self.headers(), 403)

    def test_inactive_admin(self):
        self.user.ativo = False
        self.assert_rejected(self.headers(), 401)

    def test_deleted_user(self):
        self.db.query.return_value.filter.return_value.first.return_value = None
        self.assert_rejected(self.headers(), 401)

    def test_active_admin_executes_operations(self):
        for url, operation in self.operations:
            with self.subTest(url=url):
                response = self.client.post(url, headers=self.headers())
                self.assertEqual(response.status_code, 200, response.text)
                operation.assert_awaited_once()
        self.weather.assert_awaited_once_with(38.7, -9.1, 1, self.db)
        self.fires.assert_awaited_once_with(self.db)
        self.regions.assert_awaited_once_with(self.db)
        self.update.assert_awaited_once_with()

    def test_reads_remain_public(self):
        query = self.db.query.return_value
        query.filter.return_value = query
        query.order_by.return_value = query
        query.limit.return_value = query
        query.all.return_value = []
        query.first.return_value = None
        with (
            patch.object(meteorologia, "obter_dados_meteorologicos", AsyncMock(return_value={})),
            patch.object(incendios, "obter_focos_incendio", AsyncMock(return_value=[])),
            patch.object(regioes, "obter_concelhos_portugal", AsyncMock(return_value=[])),
        ):
            for url in (
                "/api/meteorologia?latitude=38.7&longitude=-9.1",
                "/api/incendios/focos",
                "/api/regioes/concelhos",
                "/api/regioes/pesquisa?q=Lisboa",
                "/api/regioes/distritos",
                "/api/regioes/1/detalhes",
            ):
                with self.subTest(url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200, response.text)


if __name__ == "__main__":
    unittest.main()
