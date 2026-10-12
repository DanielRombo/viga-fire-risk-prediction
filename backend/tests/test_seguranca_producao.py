import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from config.seguranca import chave_jwt, origens_cors
from routes import health
from services.http_externo import get_com_retry
from services import auth


class SegurancaTests(unittest.TestCase):
    def test_chave_ausente_fraca_e_conhecida_rejeitada(self):
        for valor in ('', 'curta', 'viga-secret-key-2024'):
            with patch.dict(os.environ, SECRET_KEY=valor), self.assertRaises(ValueError):
                chave_jwt()
        with patch.dict(os.environ, SECRET_KEY='a' * 32):
            self.assertEqual(chave_jwt(), 'a' * 32)

    def test_cors_producao_same_origin_default(self):
        with patch.dict(os.environ, APP_ENV='production', CORS_ORIGINS=''):
            self.assertEqual(origens_cors(), [])

    def test_cors_origens_exatas_sem_credenciais(self):
        with patch.dict(os.environ, APP_ENV='production', CORS_ORIGINS='https://viga.example'):
            app = FastAPI()
            app.add_middleware(CORSMiddleware, allow_origins=origens_cors(),
                               allow_credentials=False, allow_methods=['*'], allow_headers=['*'])
            @app.get('/')
            def raiz(): return {'ok': True}
            with TestClient(app) as c:
                for origem, status in [('https://viga.example',200),('https://viga.example.evil',400),('null',400)]:
                    r=c.options('/',headers={'Origin':origem,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Authorization'})
                    self.assertEqual(r.status_code,status)
                    self.assertNotIn('access-control-allow-credentials',r.headers)
                self.assertEqual(c.get('/').status_code,200)

    def test_cors_wildcard_caminho_credenciais_rejeitados(self):
        for valor in ('*','https://*.example','https://example/path','https://u:p@example'):
            with patch.dict(os.environ, CORS_ORIGINS=valor), self.assertRaises(ValueError):origens_cors()

    def test_healthcheck_nao_expoe_segredo(self):
        app=FastAPI();app.include_router(health.router)
        with TestClient(app) as c, patch.object(health,'engine') as engine:
            engine.connect.side_effect=RuntimeError('password=segredo')
            self.assertEqual(c.get('/health/live').status_code,200)
            engine.connect.assert_not_called()
            r=c.get('/health/ready')
            self.assertEqual(r.status_code,503)
            self.assertEqual(r.json(),{'estado':'indisponivel'})

    def test_readiness_sucesso(self):
        with patch.object(health,'engine') as engine:
            engine.connect.return_value.__enter__.return_value.dialect.name='postgresql'
            self.assertEqual(health.ready(),{'estado':'ok'})
            self.assertEqual(engine.connect.return_value.__enter__.return_value.execute.call_count,2)

    def test_utilizador_inativo_nao_recebe_token(self):
        db=MagicMock();db.query.return_value.filter.return_value.first.return_value=SimpleNamespace(ativo=False)
        with patch.object(auth,'verificar_senha') as verificar:
            self.assertIsNone(auth.autenticar_utilizador(db,'a@example.test','senha'))
            verificar.assert_not_called()

    def test_retry_transitorio_sucesso_e_limite(self):
        async def verificar():
            for codigos, esperado in [([503,200],2),([429,429,429],3),([401],1),([200],1)]:
                cliente=SimpleNamespace(get=AsyncMock(side_effect=[httpx.Response(c) for c in codigos]))
                with patch('services.http_externo.asyncio.sleep',new_callable=AsyncMock):
                    r=await get_com_retry(cliente,'https://example.test')
                self.assertEqual(cliente.get.await_count,esperado)
                self.assertEqual(r.status_code,codigos[-1])
        asyncio.run(verificar())

    def test_timeout_esgota_e_propaga(self):
        async def verificar():
            cliente=SimpleNamespace(get=AsyncMock(side_effect=httpx.ReadTimeout('teste')))
            with patch('services.http_externo.asyncio.sleep',new_callable=AsyncMock), self.assertRaises(httpx.ReadTimeout):
                await get_com_retry(cliente,'https://example.test')
            self.assertEqual(cliente.get.await_count,3)
        asyncio.run(verificar())
