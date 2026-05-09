import httpx
import csv
import io
import os
from datetime import datetime
from models.ocorrencia import Ocorrencia

NASA_FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


async def obter_focos_incendio(dias: int = 1):
    map_key = os.getenv("NASA_FIRMS_KEY")

    # Área de Portugal Continental (lat/lon min e max)
    area = "-9.5,36.9,-6.2,42.2"

    url = f"{NASA_FIRMS_URL}/{map_key}/VIIRS_SNPP_NRT/{area}/{dias}"

    async with httpx.AsyncClient() as client:
        resposta = await client.get(url)

        # A resposta é CSV — processamos linha a linha
        conteudo = resposta.text
        leitor = csv.DictReader(io.StringIO(conteudo))

        focos = []
        for linha in leitor:
            foco = {
                "latitude": float(linha["latitude"]),
                "longitude": float(linha["longitude"]),
                "data": linha["acq_date"],
                "hora": linha["acq_time"],
                "fonte": "NASA FIRMS - VIIRS"
            }
            focos.append(foco)

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
