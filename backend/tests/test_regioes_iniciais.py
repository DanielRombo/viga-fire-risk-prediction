"""Inicialização idempotente e recolha sem IDs predefinidos."""
import asyncio
import os
import re
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with patch.dict(os.environ, {"DATABASE_URL": "postgresql+psycopg2://test:test@127.0.0.1:1/viga_test"}):
    from models.regiao import Regiao
    from models.dado_meteorologico import DadoMeteorologico
    from models.ocorrencia import Ocorrencia
    from services import scheduler
    from services.regioes_iniciais import CATALOGO, REGIOES_RECOLHA, inicializar_regioes, resolver_regioes


class RegioesIniciaisTests(unittest.TestCase):
    def setUp(self):
        url = os.getenv("VIGA_TEST_DATABASE_URL", "sqlite://")
        self.engine = create_engine(url)
        self.addCleanup(self.engine.dispose)
        if self.engine.dialect.name == "sqlite":
            @event.listens_for(self.engine, "connect")
            def configurar(connection, _):
                connection.execute("PRAGMA foreign_keys=ON")
                connection.create_function("GeomFromEWKT", 1, lambda value: value)
            with self.engine.begin() as connection:
                connection.execute(text("""CREATE TABLE regioes (
                    id_regiao INTEGER PRIMARY KEY, nome TEXT NOT NULL, distrito TEXT NOT NULL,
                    latitude FLOAT NOT NULL, longitude FLOAT NOT NULL,
                    area_km2 FLOAT, geometria TEXT, created_at DATETIME)"""))
        else:
            # Só aceitar uma BD de teste explicitamente identificada e vazia.
            self.assertTrue(self.engine.url.database.startswith("viga_test_"))
            with self.engine.begin() as connection:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            Regiao.__table__.create(self.engine)
            self.addCleanup(lambda: Regiao.__table__.drop(self.engine))
        DadoMeteorologico.__table__.create(self.engine)
        Ocorrencia.__table__.create(self.engine)
        if self.engine.dialect.name != "sqlite":
            self.addCleanup(lambda: DadoMeteorologico.__table__.drop(self.engine))
            self.addCleanup(lambda: Ocorrencia.__table__.drop(self.engine))
        self.db = Session(self.engine)
        self.addCleanup(self.db.close)

    def test_base_vazia_e_segunda_inicializacao(self):
        self.assertEqual(inicializar_regioes(self.db), 30)
        ids = {r["nome"]: r["id_regiao"] for r in resolver_regioes(self.db)}
        self.assertEqual(len(ids), 28)
        for nome in ("Lisboa", "Porto", "Coimbra", "Faro", "Vila Real"):
            self.assertIn(nome, ids)
        self.assertEqual(inicializar_regioes(self.db), 0)
        self.assertEqual(self.db.query(Regiao.id_regiao).count(), 30)
        self.assertEqual(ids, {r["nome"]: r["id_regiao"] for r in resolver_regioes(self.db)})

    @unittest.skipUnless((Path(__file__).resolve().parents[2] / "database/seeds/cidades_principais.sql").exists(),
                         "O seed SQL histórico não faz parte da imagem do backend")
    def test_catalogo_mantem_coordenadas_do_seed(self):
        seed = (Path(__file__).resolve().parents[2] / "database/seeds/cidades_principais.sql").read_text(encoding="utf-8")
        coordenadas_seed = {
            nome: (float(latitude), float(longitude))
            for nome, latitude, longitude in re.findall(
                r"\('([^']+)', '[^']+', ([\d.-]+), ([\d.-]+), [\d.-]+\)", seed)
        }
        coordenadas_catalogo = {r["nome"]: (r["latitude"], r["longitude"]) for r in CATALOGO}
        self.assertEqual(len(coordenadas_seed), 30)
        self.assertEqual(coordenadas_catalogo, coordenadas_seed)
        self.assertEqual(coordenadas_catalogo["Faro"], (37.0194, -7.9322))
        self.assertEqual(coordenadas_catalogo["Vila Real"], (41.3006, -7.7457))

    def test_coordenadas_enviadas_na_recolha_meteorologica(self):
        coordenadas_catalogo = {r["nome"]: (r["latitude"], r["longitude"]) for r in CATALOGO}
        inicializar_regioes(self.db)
        self.assertEqual(inicializar_regioes(self.db), 0)
        regioes = resolver_regioes(self.db)
        meteo = AsyncMock(return_value={"current": {
            "time": datetime.now(timezone.utc).isoformat(),
            "temperature_2m": 20, "relative_humidity_2m": 50,
            "wind_speed_10m": 10, "precipitation": 0,
        }})
        with patch.object(scheduler, "SessionLocal", return_value=self.db), \
                patch.object(scheduler, "obter_dados_meteorologicos", meteo):
            asyncio.run(scheduler._atualizar_dados())
        self.assertEqual(meteo.await_count, 28)
        enviadas = {r["nome"]: chamada.args for r, chamada in zip(regioes, meteo.await_args_list)}
        self.assertEqual(enviadas["Faro"], (37.0194, -7.9322))
        self.assertEqual(enviadas["Vila Real"], (41.3006, -7.7457))
        for nome, coordenadas in enviadas.items():
            self.assertEqual(coordenadas, coordenadas_catalogo[nome])

    def test_base_existente_preserva_ids_campos_e_duplicados_historicos(self):
        self.db.add_all([
            Regiao(id_regiao=7000, nome=" LISBOA ", distrito="Lisboa", latitude=38.72, longitude=-9.14, area_km2=99),
            Regiao(id_regiao=8000, nome="Lisboa", distrito="Lisboa", latitude=38.71, longitude=-9.13),
            Regiao(id_regiao=9000, nome="Evora", distrito="Evora", latitude=38.57, longitude=-7.91),
            Regiao(id_regiao=9500, nome="Coimbra", distrito="Desconhecido", latitude=40.20, longitude=-8.41),
        ])
        self.db.commit()
        antes = self.db.execute(text("SELECT id_regiao, nome, distrito, latitude, longitude, area_km2 FROM regioes ORDER BY id_regiao")).all()
        self.assertEqual(inicializar_regioes(self.db), 30)
        resolvidas = {r["nome"]: r for r in resolver_regioes(self.db)}
        for nome in ("Lisboa", "Évora", "Coimbra"):
            self.assertNotIn(resolvidas[nome]["id_regiao"], (7000, 8000, 9000, 9500))
        depois = self.db.execute(text("SELECT id_regiao, nome, distrito, latitude, longitude, area_km2 FROM regioes WHERE id_regiao IN (7000,8000,9000,9500) ORDER BY id_regiao")).all()
        self.assertEqual(antes, depois)
        self.assertEqual(inicializar_regioes(self.db), 0)

    def test_recolha_resolve_todas_as_regioes_com_ids_arbitrarios(self):
        for indice, regiao in enumerate(reversed(CATALOGO)):
            self.db.add(Regiao(id_regiao=10000 + indice * 11,
                              **{k: v for k, v in regiao.items() if k != "recolha_automatica"}))
        self.db.commit()
        self.assertEqual(inicializar_regioes(self.db), 0)
        resolvidas = resolver_regioes(self.db)
        meteo = AsyncMock(return_value={"current": {"time": datetime.now(timezone.utc).isoformat(), "temperature_2m": 20, "relative_humidity_2m": 50,
                                                    "wind_speed_10m": 10, "precipitation": 0}})
        with patch.object(scheduler, "SessionLocal", return_value=self.db), \
                patch.object(scheduler, "obter_dados_meteorologicos", meteo):
            asyncio.run(scheduler._atualizar_dados())
        with Session(self.engine) as db:
            self.assertEqual({r.id_regiao for r in db.query(DadoMeteorologico).all()},
                             {r["id_regiao"] for r in resolvidas})
        self.assertEqual(meteo.await_count, len(REGIOES_RECOLHA))
        self.assertEqual([(c.args) for c in meteo.await_args_list],
                         [(r["latitude"], r["longitude"]) for r in resolvidas])
        foco = {"latitude": 39, "longitude": -8, "data": "2026-09-30", "hora": "1230", "fonte": "NASA FIRMS"}
        with patch.object(scheduler, "SessionLocal", return_value=self.db), \
                patch("services.nasa_firms.obter_focos_incendio", AsyncMock(return_value=[foco])):
            asyncio.run(scheduler._atualizar_focos())
        with Session(self.engine) as db:
            self.assertIsNone(db.query(Ocorrencia).one().id_regiao)

    def test_ambiguidade_nao_insere_parcialmente(self):
        for indice in range(2):
            self.db.add(Regiao(nome="Porto", distrito="Porto", latitude=41.1579, longitude=-8.6291))
        self.db.commit()
        with self.assertRaisesRegex(ValueError, "ambígua"):
            inicializar_regioes(self.db)
        self.assertEqual(self.db.query(Regiao.id_regiao).count(), 2)


if __name__ == "__main__":
    unittest.main()
