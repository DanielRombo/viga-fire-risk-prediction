"""Persistência automática com HTTP simulado e transações reais em memória."""
import asyncio
import os
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with patch.dict(os.environ, {"DATABASE_URL": "postgresql+psycopg2://test:test@127.0.0.1:1/viga_test"}):
    from models.regiao import Regiao
    from models.ocorrencia import Ocorrencia
    from services import scheduler

HTTP_CLIENT = httpx.AsyncClient
CABECALHO = "latitude,longitude,acq_date,acq_time\n"
FOCO = "39,-8,2026-09-29,0035\n"


class SchedulerFocosTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        self.addCleanup(self.engine.dispose)
        with self.engine.begin() as connection:
            connection.execute(text("PRAGMA foreign_keys=ON"))
            connection.execute(text("CREATE TABLE regioes (id_regiao INTEGER PRIMARY KEY)"))
            connection.execute(text("INSERT INTO regioes VALUES (1)"))
        # Criar apenas ocorrências evita a dependência PostGIS da tabela de regiões.
        Ocorrencia.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.addCleanup(self.db.close)

    def executar(self, handler, falha=False):
        with patch.object(scheduler, "SessionLocal", return_value=self.db), \
                patch("httpx.AsyncClient", side_effect=lambda **kwargs:
                      HTTP_CLIENT(transport=httpx.MockTransport(handler), **kwargs)), \
                patch.object(self.db, "commit", wraps=self.db.commit) as commit, \
                patch.object(self.db, "rollback", wraps=self.db.rollback) as rollback, \
                patch.object(self.db, "close", wraps=self.db.close) as close:
            asyncio.run(scheduler._atualizar_focos())
            close.assert_called_once()
            if falha:
                rollback.assert_called_once()
            else:
                rollback.assert_not_called()
                commit.assert_called_once()

    def registos(self):
        with Session(self.engine) as db:
            return db.query(Ocorrencia).all()

    def test_foco_valido_preserva_aquisicao_e_conclui_transacao(self):
        self.executar(lambda request: httpx.Response(200, text=CABECALHO + FOCO))
        registos = self.registos()
        self.assertEqual(len(registos), 1)
        foco = registos[0]
        self.assertIsInstance(foco, Ocorrencia)
        self.assertEqual(foco.data_inicio, datetime(2026, 9, 29, 0, 35))
        self.assertEqual(foco.estado, "ativo")
        self.assertIsNone(foco.id_regiao)
        self.assertEqual(foco.associacao_geografica, "nao_determinada")
        self.assertEqual((foco.latitude, foco.longitude), (39, -8))
        self.assertEqual(foco.fonte, "NASA FIRMS - VIIRS")

    def test_lista_vazia_conclui_sem_registos(self):
        self.executar(lambda request: httpx.Response(200, text=CABECALHO))
        self.assertEqual(self.registos(), [])

    def test_erro_da_fonte_provoca_rollback(self):
        self.executar(lambda request: httpx.Response(500), falha=True)
        self.assertEqual(self.registos(), [])

    def test_erro_real_na_bd_reverte_todo_o_lote(self):
        with self.engine.begin() as connection:
            connection.execute(text("""
                CREATE TRIGGER rejeitar_segundo_foco BEFORE INSERT ON ocorrencias
                WHEN NEW.latitude = 40
                BEGIN SELECT RAISE(ABORT, 'falha simulada na BD'); END
            """))
        lote = CABECALHO + FOCO + "40,-8,2026-09-29,0040\n"
        self.executar(lambda request: httpx.Response(200, text=lote), falha=True)
        self.assertEqual(self.registos(), [])
        # A sessão continua utilizável após o rollback.
        self.executar(lambda request: httpx.Response(200, text=CABECALHO + FOCO))
        self.assertEqual(len(self.registos()), 1)


if __name__ == "__main__":
    unittest.main()
