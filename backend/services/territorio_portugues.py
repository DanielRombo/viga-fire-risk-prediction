"""Filtro terrestre com o GeoJSON já usado no projeto, sem acesso à BD."""
import json
import math
from functools import lru_cache
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.prepared import prep


@lru_cache(maxsize=1)
def territorio():
    caminho = Path(__file__).resolve().parents[1] / "data/portugal_distritos.geojson"
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    grupos = {"continente": [], "acores": [], "madeira": []}
    for elemento in dados["features"]:
        nome = elemento["properties"]["name"]
        grupo = {"Azores": "acores", "Madeira": "madeira"}.get(nome, "continente")
        geometria = shape(elemento["geometry"])
        if geometria.is_empty or not geometria.is_valid or geometria.geom_type not in ("Polygon", "MultiPolygon"):
            raise ValueError("Geometria inválida no catálogo do território português.")
        grupos[grupo].append(geometria)
    if any(not geometrias for geometrias in grupos.values()):
        raise ValueError("O catálogo deve incluir continente, Açores e Madeira.")
    areas = {}
    for nome, geometrias in grupos.items():
        limites = [g.bounds for g in geometrias]
        minimo_x = math.floor(min(b[0] for b in limites) * 10000) / 10000
        minimo_y = math.floor(min(b[1] for b in limites) * 10000) / 10000
        maximo_x = math.ceil(max(b[2] for b in limites) * 10000) / 10000
        maximo_y = math.ceil(max(b[3] for b in limites) * 10000) / 10000
        areas[nome] = f"{minimo_x},{minimo_y},{maximo_x},{maximo_y}"
    return areas, tuple(prep(g) for geometrias in grupos.values() for g in geometrias)


def areas_consulta():
    return territorio()[0]


def pertence_a_portugal(latitude, longitude):
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        return False
    ponto = Point(longitude, latitude)
    return any(poligono.covers(ponto) for poligono in territorio()[1])
