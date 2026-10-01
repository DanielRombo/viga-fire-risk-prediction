"""Cobertura nacional por polígonos e pedidos NASA simulados, sem BD."""
import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with patch.dict(os.environ, {"DATABASE_URL": "postgresql+psycopg2://test:test@127.0.0.1:1/viga_test"}):
    from services.nasa_firms import obter_focos_incendio, guardar_focos_incendio
    from services.territorio_portugues import areas_consulta, pertence_a_portugal

HTTP_CLIENT = httpx.AsyncClient
CABECALHO = "latitude,longitude,acq_date,acq_time\n"


class TerritorioNasaTests(unittest.TestCase):
    def fonte(self, handler):
        return patch("httpx.AsyncClient", side_effect=lambda **kwargs:
                     HTTP_CLIENT(transport=httpx.MockTransport(handler), **kwargs))

    def test_pontos_portugueses_e_espanhois(self):
        for ponto in [(39, -8), (40.2, -8.4), (37.8, -25.5), (39.7, -31.1),
                      (32.75, -17), (33.07, -16.34), (30.145, -15.86)]:
            with self.subTest(ponto=ponto):
                self.assertTrue(pertence_a_portugal(*ponto))
        # Badajoz e Cáceres estavam dentro do retângulo antigo; o oceano também.
        for ponto in [(38.88, -6.97), (39.47, -6.38), (39, -9.5), (38, -28), (32.5, -17)]:
            with self.subTest(ponto=ponto):
                self.assertFalse(pertence_a_portugal(*ponto))

    def test_tres_areas_consultadas_e_filtragem(self):
        areas = areas_consulta()
        self.assertEqual(set(areas), {"continente", "acores", "madeira"})
        pontos = {"continente": (39, -8), "acores": (39.7, -31.1), "madeira": (30.145, -15.86)}
        pedidos = []

        def handler(request):
            bbox = request.url.path.split('/')[-2]
            pedidos.append(bbox)
            nome = next(nome for nome, area in areas.items() if area == bbox)
            lat, lon = pontos[nome]
            minlon, minlat, maxlon, maxlat = map(float, bbox.split(','))
            self.assertTrue(minlon <= lon <= maxlon and minlat <= lat <= maxlat)
            return httpx.Response(200, text=CABECALHO + f"{lat},{lon},2026-09-30,1200\n38.88,-6.97,2026-09-30,1200\n")

        with self.fonte(handler):
            focos = asyncio.run(obter_focos_incendio())
        self.assertCountEqual(pedidos, areas.values())
        self.assertEqual({(f["latitude"], f["longitude"]) for f in focos}, set(pontos.values()))

    def test_lista_vazia_so_depois_das_tres_respostas_validas(self):
        pedidos = []

        def handler(request):
            pedidos.append(request.url.path)
            return httpx.Response(200, text=CABECALHO)

        with self.fonte(handler):
            self.assertEqual(asyncio.run(obter_focos_incendio()), [])
        self.assertEqual(len(pedidos), 3)

    def test_mesma_observacao_em_varias_areas_nao_se_repete(self):
        with self.fonte(lambda request: httpx.Response(200, text=CABECALHO + "39,-8,2026-09-30,1200\n")):
            self.assertEqual(len(asyncio.run(obter_focos_incendio())), 1)

    def test_falha_em_qualquer_area_nao_devolve_sucesso_parcial(self):
        for area in areas_consulta().values():
            for erro, estado in [("http", 502), ("timeout", 504), ("incompleta", 502)]:
                with self.subTest(area=area, erro=erro):
                    def handler(request):
                        if request.url.path.split('/')[-2] == area:
                            if erro == "timeout":
                                raise httpx.ReadTimeout("timeout simulado", request=request)
                            return httpx.Response(500 if erro == "http" else 200, text="erro")
                        return httpx.Response(200, text=CABECALHO + "39,-8,2026-09-30,1200\n")

                    db = MagicMock()
                    with self.fonte(handler), self.assertRaises(HTTPException) as raised:
                        asyncio.run(guardar_focos_incendio(db))
                    self.assertEqual(raised.exception.status_code, estado)
                    db.execute.assert_not_called()
                    db.commit.assert_not_called()
                    db.rollback.assert_called_once()

    @unittest.skipUnless((Path(__file__).resolve().parents[2] / "frontend/public/portugal_distritos.json").exists(),
                         "O frontend não faz parte da imagem do backend")
    def test_poligonos_reutilizados_sem_alteracoes(self):
        root = Path(__file__).resolve().parents[2]
        self.assertEqual((root / "backend/data/portugal_distritos.geojson").read_bytes(),
                         (root / "frontend/public/portugal_distritos.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
