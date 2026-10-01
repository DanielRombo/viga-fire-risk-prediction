"""Deduplicação persistente e associação por polígonos, com fontes simuladas."""
import asyncio
import os
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with patch.dict(os.environ, {"DATABASE_URL": "postgresql+psycopg2://test:test@127.0.0.1:1/viga_test"}):
    from models.regiao import Regiao
    from models.ocorrencia import Ocorrencia
    from services.nasa_firms import guardar_focos_incendio
    from services.esquema_ocorrencias import preparar_ocorrencias

FOCO = {"latitude": 39.0, "longitude": -8.0, "data": "2026-09-29", "hora": "0035", "fonte": "NASA FIRMS - VIIRS"}


class NasaPersistenciaTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(os.getenv("VIGA_TEST_DATABASE_URL", "sqlite://"))
        self.addCleanup(self.engine.dispose)
        self.postgis = self.engine.dialect.name == "postgresql"
        if self.postgis:
            self.assertTrue(self.engine.url.database.startswith("viga_test_"))
            with self.engine.begin() as connection:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            Regiao.__table__.create(self.engine)
            self.addCleanup(lambda: Regiao.__table__.drop(self.engine))
        else:
            with self.engine.begin() as connection:
                connection.execute(text("CREATE TABLE regioes (id_regiao INTEGER PRIMARY KEY)"))
        Ocorrencia.__table__.create(self.engine)
        self.addCleanup(lambda: Ocorrencia.__table__.drop(self.engine))

    def guardar(self, focos):
        with Session(self.engine) as db, patch("services.nasa_firms.obter_focos_incendio", AsyncMock(return_value=focos)):
            return asyncio.run(guardar_focos_incendio(db))

    def test_repeticoes_na_mesma_lista_e_em_sessoes_distintas(self):
        primeira = self.guardar([FOCO, dict(FOCO)])
        segunda = self.guardar([dict(FOCO)])
        self.assertEqual(primeira, {"focos_guardados": 1, "focos_duplicados": 1, "focos_sem_regiao": 1})
        self.assertEqual(segunda["focos_duplicados"], 1)
        self.assertEqual(segunda["focos_guardados"], 0)
        with Session(self.engine) as db:
            registo = db.query(Ocorrencia).one()
            self.assertIsNone(registo.id_regiao)
            self.assertEqual(registo.associacao_geografica, "nao_determinada")
            self.assertEqual(len(registo.nasa_chave), 64)

    def test_observacoes_distintas_nao_sao_fundidas(self):
        resultado = self.guardar([FOCO, {**FOCO, "hora": "0040"}, {**FOCO, "latitude": 39.000001}])
        self.assertEqual(resultado["focos_guardados"], 3)

    def test_lista_vazia(self):
        self.assertEqual(self.guardar([]), {"focos_guardados": 0, "focos_duplicados": 0, "focos_sem_regiao": 0})

    def test_erro_real_reverte_lote(self):
        with self.assertRaises(ValueError):
            self.guardar([FOCO, {**FOCO, "hora": "inválida"}])
        with Session(self.engine) as db:
            self.assertEqual(db.query(Ocorrencia).count(), 0)

    def criar_poligono(self, identifier, wkt):
        with self.engine.begin() as connection:
            connection.execute(text("""INSERT INTO regioes (id_regiao,nome,distrito,latitude,longitude,geometria)
                VALUES (:id,:nome,'Teste',39,-8,ST_GeomFromText(:wkt,4326))"""),
                {"id": identifier, "nome": f"Região {identifier}", "wkt": wkt})

    def test_postgis_duas_regioes_e_fora_dos_poligonos(self):
        if not self.postgis:
            self.skipTest("Requer PostgreSQL/PostGIS descartável")
        self.criar_poligono(10, "POLYGON((-8.5 38.5,-7.5 38.5,-7.5 39.5,-8.5 39.5,-8.5 38.5))")
        self.criar_poligono(20, "POLYGON((-8.5 40.5,-7.5 40.5,-7.5 41.5,-8.5 41.5,-8.5 40.5))")
        resultado = self.guardar([FOCO, {**FOCO, "latitude": 41}, {**FOCO, "longitude": -9}])
        self.assertEqual(resultado["focos_sem_regiao"], 1)
        with Session(self.engine) as db:
            registos = db.query(Ocorrencia).order_by(Ocorrencia.id_ocorrencia).all()
            self.assertEqual([r.id_regiao for r in registos], [10, 20, None])
            self.assertEqual([r.associacao_geografica for r in registos], ["poligono", "poligono", "nao_determinada"])

    def test_postgis_poligonos_sobrepostos_nao_escolhem_regiao_arbitraria(self):
        if not self.postgis:
            self.skipTest("Requer PostgreSQL/PostGIS descartável")
        for identifier in (10, 20):
            self.criar_poligono(identifier, "POLYGON((-8.5 38.5,-7.5 38.5,-7.5 39.5,-8.5 39.5,-8.5 38.5))")
        self.guardar([FOCO])
        with Session(self.engine) as db:
            foco = db.query(Ocorrencia).one()
            self.assertIsNone(foco.id_regiao)
            self.assertEqual(foco.associacao_geografica, "ambigua")

    def test_postgres_recolhas_concorrentes(self):
        if not self.postgis:
            self.skipTest("Requer PostgreSQL/PostGIS descartável")
        barreira = Barrier(2)

        async def obter():
            barreira.wait(timeout=10)
            return [FOCO]

        def gravar():
            with Session(self.engine) as db:
                return asyncio.run(guardar_focos_incendio(db))

        with patch("services.nasa_firms.obter_focos_incendio", obter), ThreadPoolExecutor(max_workers=2) as executor:
            futuros = [executor.submit(gravar) for _ in range(2)]
            resultados = [f.result(timeout=15) for f in futuros]
        self.assertEqual(sum(r["focos_guardados"] for r in resultados), 1)
        self.assertEqual(sum(r["focos_duplicados"] for r in resultados), 1)
        with Session(self.engine) as db:
            self.assertEqual(db.query(Ocorrencia).count(), 1)

    def test_postgis_srid_conhecido_e_desconhecido(self):
        if not self.postgis:
            self.skipTest("Requer PostgreSQL/PostGIS descartável")
        self.criar_poligono(10, "POLYGON((-8.5 38.5,-7.5 38.5,-7.5 39.5,-8.5 39.5,-8.5 38.5))")
        with self.engine.begin() as connection:
            connection.execute(text("UPDATE regioes SET geometria=ST_Transform(geometria,3857)"))
        self.guardar([FOCO])
        with Session(self.engine) as db:
            self.assertEqual(db.query(Ocorrencia).one().id_regiao, 10)
        with self.engine.begin() as connection:
            connection.execute(text("UPDATE regioes SET geometria=ST_SetSRID(geometria,0)"))
        self.guardar([{**FOCO, "hora": "0040"}])
        with Session(self.engine) as db:
            self.assertIsNone(db.query(Ocorrencia).order_by(Ocorrencia.id_ocorrencia.desc()).first().id_regiao)

    def test_postgres_adaptacao_preserva_duplicados_antigos(self):
        if not self.postgis:
            self.skipTest("Requer PostgreSQL/PostGIS descartável")
        self.criar_poligono(10, "POLYGON((-8.5 38.5,-7.5 38.5,-7.5 39.5,-8.5 39.5,-8.5 38.5))")
        Ocorrencia.__table__.drop(self.engine)
        with self.engine.begin() as connection:
            connection.execute(text("""CREATE TABLE ocorrencias (
                id_ocorrencia SERIAL PRIMARY KEY, id_regiao INTEGER NOT NULL REFERENCES regioes(id_regiao),
                data_inicio TIMESTAMP NOT NULL, data_fim TIMESTAMP, area_ardida FLOAT,
                causa VARCHAR, gravidade VARCHAR, latitude FLOAT NOT NULL, longitude FLOAT NOT NULL,
                estado VARCHAR NOT NULL, fonte VARCHAR, created_at TIMESTAMP)"""))
            for _ in range(2):
                connection.execute(text("""INSERT INTO ocorrencias (id_regiao,data_inicio,latitude,longitude,estado,fonte)
                    VALUES (10,'2026-09-29 00:35:00',39,-8,'ativo','NASA FIRMS - VIIRS')"""))
        preparar_ocorrencias(self.engine)
        preparar_ocorrencias(self.engine)
        resultado = self.guardar([FOCO])
        self.assertEqual(resultado["focos_guardados"], 0)
        self.assertEqual(resultado["focos_duplicados"], 1)
        with Session(self.engine) as db:
            registos = db.query(Ocorrencia).all()
            self.assertEqual(len(registos), 2)
            self.assertEqual(sum(r.nasa_chave is not None for r in registos), 1)
            self.assertEqual({r.id_regiao for r in registos}, {10})
            self.assertEqual({r.associacao_geografica for r in registos}, {"legado_nao_validado"})
        self.guardar([{**FOCO, "longitude": -9}])
        with Session(self.engine) as db:
            self.assertEqual(db.query(Ocorrencia).filter(Ocorrencia.id_regiao.is_(None)).count(), 1)


if __name__ == "__main__":
    unittest.main()
