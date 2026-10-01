"""Identidade de uma observação do produto consultado, não de um incêndio."""
from hashlib import sha256

PRODUTO_NASA = "VIIRS_SNPP_NRT"


def chave_observacao(data, latitude, longitude):
    # float.hex normaliza representações CSV equivalentes, sem arredondar posições.
    coordenadas = [float(valor or 0).hex() for valor in (latitude, longitude)]
    valor = "|".join([PRODUTO_NASA, data.isoformat(), *coordenadas])
    return sha256(valor.encode("ascii")).hexdigest()
