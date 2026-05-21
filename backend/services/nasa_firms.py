import httpx
import csv
import io
import os
from datetime import datetime
from models.ocorrencia import Ocorrencia

NASA_FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def is_portugal(lat, lon):
    # Portugal continental
    if 36.8 <= lat <= 42.2 and -9.6 <= lon <= -6.1:
        return True
    # Açores
    if 36.8 <= lat <= 40.0 and -31.3 <= lon <= -24.8:
        return True
    # Madeira
    if 32.4 <= lat <= 33.2 and -17.3 <= lon <= -16.2:
        return True
    return False


async def obter_focos_incendio(dias: int = 1):
    map_key = os.getenv("NASA_FIRMS_KEY")
    area = "-9.5,36.9,-6.2,42.2"
    url = f"{NASA_FIRMS_URL}/{map_key}/VIIRS_SNPP_NRT/{area}/{dias}"
    async with httpx.AsyncClient() as client:
        resposta = await client.get(url)
        conteudo = resposta.text
        leitor = csv.DictReader(io.StringIO(conteudo))
        focos = []
        for linha in leitor:
            try:
                lat = float(linha["latitude"])
                lon = float(linha["longitude"])
                if not is_portugal(lat, lon):
                    continue
                foco = {
                    "latitude": lat,
                    "longitude": lon,
                    "data": linha["acq_date"],
                    "hora": linha["acq_time"],
                    "fonte": "NASA FIRMS - VIIRS"
                }
                focos.append(foco)
            except Exception:
                continue
        return focos


async def guardar_focos_incendio(db, id_regiao: int = 1):
    focos = await obter_focos_incendio()
    registos_guardados = 0
    for foco in focos:
        novo_registo = Ocorrencia(
            id_regiao=id_regiao,
            data_inicio=datetime.strptime(
                f"{foco['data']} {foco['hora']}", "%Y-%m-%d %H%M"),
            latitude=foco["latitude"],
            longitude=foco["longitude"],
            estado="ativo",
            fonte=foco["fonte"]
        )
        db.add(novo_registo)
        registos_guardados += 1
    db.commit()
    return {"focos_guardados": registos_guardados}
