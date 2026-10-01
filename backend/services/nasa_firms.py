import httpx
import csv
import io
import os
from datetime import datetime
from models.ocorrencia import Ocorrencia
from services.fontes import validar_fonte, erro_fonte, numero
from services.identidade_nasa import PRODUTO_NASA, chave_observacao
from services.geografia_focos import determinar_regiao
from services.territorio_portugues import areas_consulta, pertence_a_portugal as is_portugal
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

NASA_FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


async def obter_focos_incendio(dias: int = 1):
    map_key = os.getenv("NASA_FIRMS_KEY")
    areas = areas_consulta()
    with validar_fonte("NASA FIRMS"):
        async with httpx.AsyncClient() as client:
            focos = []
            vistas = set()
            for area in areas.values():
                url = f"{NASA_FIRMS_URL}/{map_key}/{PRODUTO_NASA}/{area}/{dias}"
                resposta = await client.get(url)
                resposta.raise_for_status()
                leitor = csv.DictReader(io.StringIO(resposta.text))
                if not {"latitude", "longitude", "acq_date", "acq_time"}.issubset(leitor.fieldnames or []):
                    raise erro_fonte("NASA FIRMS", "dados_incompletos")
                for linha in leitor:
                    lat = numero(linha["latitude"])
                    lon = numero(linha["longitude"])
                    data = datetime.strptime(f"{linha['acq_date']} {linha['acq_time']}", "%Y-%m-%d %H%M")
                    if not is_portugal(lat, lon):
                        continue
                    foco = {
                        "latitude": lat,
                        "longitude": lon,
                        "data": linha["acq_date"],
                        "hora": linha["acq_time"],
                        "fonte": "NASA FIRMS - VIIRS"
                    }
                    chave = chave_observacao(data, lat, lon)
                    if chave not in vistas:
                        vistas.add(chave)
                        focos.append(foco)
            return focos


async def guardar_focos_incendio(db):
    contagens = {"focos_guardados": 0, "focos_duplicados": 0, "focos_sem_regiao": 0}
    try:
        focos = await obter_focos_incendio()
        inserir = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
        for foco in focos:
            data = datetime.strptime(f"{foco['data']} {foco['hora']}", "%Y-%m-%d %H%M")
            id_regiao, associacao = determinar_regiao(db, foco["latitude"], foco["longitude"])
            comando = inserir(Ocorrencia).values(
                nasa_chave=chave_observacao(data, foco["latitude"], foco["longitude"]),
                id_regiao=id_regiao, associacao_geografica=associacao,
                data_inicio=data, latitude=foco["latitude"], longitude=foco["longitude"],
                estado="ativo", fonte=foco["fonte"],
            ).on_conflict_do_nothing(index_elements=["nasa_chave"])
            if db.execute(comando).rowcount:
                contagens["focos_guardados"] += 1
                contagens["focos_sem_regiao"] += int(id_regiao is None)
            else:
                contagens["focos_duplicados"] += 1
        db.commit()
        return contagens
    except Exception:
        db.rollback()
        raise
