"""Integração opcional: executar apenas numa BD descartável explicitamente indicada."""
import os
import unittest

import psycopg2
from sqlalchemy import text


@unittest.skipUnless(os.getenv('VIGA_SECURITY_POSTGRES_TEST') == '1', 'Exige PostgreSQL descartável.')
class PostgreSQLSegurancaTests(unittest.TestCase):
    def setUp(self):
        from config.database import engine
        self.engine = engine
        self.assertEqual(engine.url.database, 'viga_fwi_test_security')
        self.assertIn(engine.url.host, ('localhost', '127.0.0.1'))

    def test_readiness_e_postgis(self):
        from routes.health import ready
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text('SELECT current_database()')).scalar(), 'viga_fwi_test_security')
            self.assertTrue(conn.execute(text('SELECT postgis_version()')).scalar())
        self.assertEqual(ready(), {'estado': 'ok'})

    def test_pool_recupera_ligacao_interrompida(self):
        self.engine.dispose()
        with self.engine.connect() as conn:
            pid = conn.execute(text('SELECT pg_backend_pid()')).scalar()
        # Termina apenas a ligação ociosa deste teste; nenhuma ligação da aplicação real.
        with psycopg2.connect(dbname='viga_fwi_test_security', user='postgres', host='127.0.0.1') as controlo:
            with controlo.cursor() as cursor:
                cursor.execute('SELECT pg_terminate_backend(%s)', (pid,))
                self.assertTrue(cursor.fetchone()[0])
        with self.engine.connect() as conn:
            self.assertNotEqual(conn.execute(text('SELECT pg_backend_pid()')).scalar(), pid)
            self.assertEqual(conn.execute(text('SELECT 1')).scalar(), 1)
        self.assertTrue(self.engine.hide_parameters)
