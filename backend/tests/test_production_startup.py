"""Arranque de produção com Uvicorn e APScheduler reais, sem recolha ou BD externa."""
import importlib.util
import json
import os
import socket
import sys
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, Mock, patch

import httpx
import uvicorn
from apscheduler.events import EVENT_JOB_EXECUTED
from apscheduler.schedulers.background import BackgroundScheduler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


class ProductionStartupTests(unittest.TestCase):
    def test_single_worker_single_initial_collection_and_periodic_jobs(self):
        dockerfile = (ROOT / "docker/backend/Dockerfile.prod").read_text(encoding="utf-8")
        command = json.loads(next(line[4:] for line in dockerfile.splitlines() if line.startswith("CMD ")))
        self.assertEqual(command[:2], ["uvicorn", "main:app"])
        self.assertEqual(command[command.index("--workers") + 1], "1")
        self.assertNotIn("iniciar.py", " ".join(command))
        self.assertNotIn("--reload", command)

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql+psycopg2://test:test@127.0.0.1:1/viga_test"}):
            from config.database import Base
            from services import scheduler as jobs
            # Carregar os modelos antes de patch.dict(sys.modules): a reposição
            # desse dicionário não pode provocar uma segunda declaração ORM.
            from services import processamento_fwi

        # Isolar exclusivamente as operações externas; usar o startup real de main.py.
        modelo = ModuleType("services.modelo_ml")
        modelo.prever_risco = Mock()
        spec = importlib.util.spec_from_file_location("viga_startup_test", ROOT / "backend/main.py")
        main = importlib.util.module_from_spec(spec)
        with patch.object(Base.metadata, "create_all"), patch.dict(sys.modules, {"services.modelo_ml": modelo}):
            spec.loader.exec_module(main)

        scheduler = BackgroundScheduler()
        initial = AsyncMock()
        meteorologia = Mock()
        focos = Mock()
        executados = []
        concluido = threading.Event()

        def registar(event):
            executados.append((event.job_id, event.scheduled_run_time))
            if len(executados) >= 3:
                concluido.set()

        scheduler.add_listener(registar, EVENT_JOB_EXECUTED)
        with patch.object(jobs, "scheduler", scheduler), \
                patch("services.esquema_ocorrencias.preparar_ocorrencias"), \
                patch("services.regioes_iniciais.preparar_regioes") as preparar, \
                patch("services.processamento_fwi.preparar_estrutura_fwi") as preparar_fwi, \
                patch.object(scheduler, "start", wraps=scheduler.start) as start, \
                patch.object(jobs, "atualizar_dados_meteorologicos", initial), \
                patch.object(jobs, "atualizar_dados_meteorologicos_sync", meteorologia), \
                patch.object(jobs, "atualizar_focos_sync", focos), \
                patch.object(jobs, "atualizar_fwi_diario_sync") as fwi, \
                socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            config = uvicorn.Config(main.app, workers=int(command[-1]), log_level="error", lifespan="on")
            server = uvicorn.Server(config)
            thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
            thread.start()
            try:
                deadline = time.monotonic() + 10
                while not server.started and thread.is_alive() and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(server.started, "O backend não concluiu o arranque")
                start.assert_called_once()
                preparar.assert_called_once()
                preparar_fwi.assert_called_once()
                initial.assert_awaited_once()
                self.assertEqual({job.id for job in scheduler.get_jobs()}, {"meteorologia", "focos", "fwi_diario"})
                self.assertEqual(scheduler.get_job('fwi_diario').max_instances, 1)
                jobs.iniciar_scheduler()
                start.assert_called_once()
                self.assertEqual(scheduler.get_job("meteorologia").trigger.interval.total_seconds(), 3600)
                self.assertEqual(scheduler.get_job("focos").trigger.interval.total_seconds(), 21600)
                meteorologia.assert_not_called()
                focos.assert_not_called()

                # Antecipar só a próxima execução: manter os triggers periódicos reais.
                for job in scheduler.get_jobs():
                    if job.id != 'fwi_diario':  # Já agendado uma vez no arranque.
                        scheduler.modify_job(job.id, next_run_time=datetime.now(timezone.utc))
                self.assertTrue(concluido.wait(5), "Os jobs periódicos não foram executados")
                meteorologia.assert_called_once()
                focos.assert_called_once()
                fwi.assert_called_once()
                self.assertEqual(len(executados), len(set(executados)))
                self.assertEqual(sorted(job_id for job_id, _ in executados), ["focos", "fwi_diario", "meteorologia"])
                initial.assert_awaited_once()
                port = listener.getsockname()[1]
                response = httpx.get(f"http://127.0.0.1:{port}/", timeout=5, trust_env=False)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"status": "VIGA API online"})
            finally:
                server.should_exit = True
                thread.join(timeout=10)
                if scheduler.running:
                    scheduler.shutdown(wait=True)
            self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
