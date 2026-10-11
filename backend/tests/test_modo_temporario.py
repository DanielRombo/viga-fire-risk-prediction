"""Cada modo é importado num processo isolado, sem BD ou fontes externas."""
import os
from pathlib import Path
import subprocess
import sys
import unittest
import socket
import time
import httpx

SCRIPT = r'''
import os
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import event
from config.database import Base, engine

@event.listens_for(engine, 'do_connect')
def proibir_ligacao(*args):
    raise AssertionError('Ligação inesperada à BD')

with patch.object(Base.metadata, 'create_all') as ddl, \
     patch('services.esquema_ocorrencias.preparar_ocorrencias') as ocorrencias, \
     patch('services.regioes_iniciais.preparar_regioes') as regioes, \
     patch('services.processamento_fwi.preparar_estrutura_fwi') as fwi, \
     patch('services.scheduler.iniciar_scheduler') as scheduler, \
     patch('services.scheduler.atualizar_dados_meteorologicos', new_callable=AsyncMock) as meteo, \
     patch('httpx.AsyncClient.request', side_effect=AssertionError('Download inesperado')), \
     patch('requests.sessions.Session.request', side_effect=AssertionError('Download inesperado')):
    import main
    temporario = os.getenv('DISABLE_AUTOMATIC_TASKS', 'false').strip().lower() == 'true'
    with TestClient(main.app) as client:
        assert client.get('/').json() == {'status': 'VIGA API online'}
        schema = client.get('/openapi.json')
        assert schema.status_code == 200
        assert '/api/regioes/monitorizadas' in schema.json()['paths']
        assert '/api/fwi-diario/{id_regiao}' in schema.json()['paths']
    for mock in (ddl, ocorrencias, regioes, fwi, scheduler, meteo):
        if temporario:
            mock.assert_not_called()
        else:
            assert mock.call_count == 1, (mock, mock.call_count)
    if not temporario:
        meteo.assert_awaited_once()
'''


class ModoTemporarioTests(unittest.TestCase):
    def executar(self, valor):
        env = dict(os.environ, DATABASE_URL='postgresql+psycopg2://test@127.0.0.1:1/viga_test_sem_bd',
                   PYTHONDONTWRITEBYTECODE='1')
        env.pop('DISABLE_AUTOMATIC_TASKS', None)
        if valor is not None:
            env['DISABLE_AUTOMATIC_TASKS'] = valor
        return subprocess.run([sys.executable, '-c', SCRIPT], env=env,
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)

    def verificar(self, valor):
        p = self.executar(valor)
        self.assertEqual(p.returncode, 0, p.stdout+p.stderr)

    def test_ausente_preserva_arranque_normal(self):
        self.verificar(None)

    def test_false_preserva_arranque_normal(self):
        self.verificar('false')

    def test_true_sem_preparacao_scheduler_recolha_com_api_funcional(self):
        self.verificar('true')

    def test_valor_invalido_nao_ativa_jobs_silenciosamente(self):
        p = self.executar('tru')
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('DISABLE_AUTOMATIC_TASKS deve ser true ou false.', p.stderr)

    def test_uvicorn_real_sem_bd_disponivel(self):
        env = dict(os.environ, DISABLE_AUTOMATIC_TASKS='true',
            DATABASE_URL='postgresql+psycopg2://test@127.0.0.1:1/viga_test_sem_bd',
            PYTHONDONTWRITEBYTECODE='1')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            porta = sock.getsockname()[1]
        p = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'main:app', '--host',
            '127.0.0.1', '--port', str(porta), '--workers', '1'], env=env,
            cwd=Path(__file__).resolve().parents[1], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            with httpx.Client(trust_env=False, timeout=1) as client:
                for _ in range(100):
                    if p.poll() is not None:
                        self.fail(p.stdout.read().decode())
                    try:
                        resposta = client.get(f'http://127.0.0.1:{porta}/')
                        break
                    except httpx.TransportError:
                        time.sleep(0.1)
                else:
                    self.fail('Uvicorn não ficou disponível.')
                self.assertEqual(resposta.status_code, 200)
                self.assertEqual(resposta.json(), {'status':'VIGA API online'})
        finally:
            p.terminate()
            try:
                saida = p.communicate(timeout=10)[0].decode()
            except subprocess.TimeoutExpired:
                p.kill()
                saida = p.communicate()[0].decode()
        self.assertIn('tarefas automáticas desativadas', saida)
        self.assertNotIn('Traceback', saida)
