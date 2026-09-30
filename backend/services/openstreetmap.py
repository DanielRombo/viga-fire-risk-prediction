import httpx
import logging
from services.fontes import validar_fonte, numero

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


async def obter_concelhos_portugal():
    query = """
    [out:json][timeout:60];
    area["name"="Portugal"]["admin_level"="2"]->.portugal;
    relation["admin_level"="8"]["boundary"="administrative"](area.portugal);
    out center;
    """

    with validar_fonte("Overpass"):
        async with httpx.AsyncClient(timeout=60) as client:
            resposta = await client.post(OVERPASS_URL, data={"data": query}, headers={"User-Agent": "VIGA/1.0 (projeto academico)"})
            resposta.raise_for_status()
            dados = resposta.json()

            if not isinstance(dados["elements"], list) or dados.get("remark"):
                raise ValueError("Resposta Overpass incompleta")
            concelhos = []
            for elemento in dados["elements"]:
                if not elemento.get("tags", {}).get("name"):
                    raise ValueError("Região sem nome")
                if "tags" in elemento and "name" in elemento["tags"]:
                    concelho = {
                        "nome": elemento["tags"]["name"],
                        "distrito": elemento["tags"].get("is_in:district", "Desconhecido"),
                        "latitude": numero(elemento["center"]["lat"]),
                        "longitude": numero(elemento["center"]["lon"]),
                    }
                    concelhos.append(concelho)

            logger.info(f"Concelhos obtidos: {len(concelhos)}")
            return concelhos



async def popular_regioes(db):
    from models.regiao import Regiao

    concelhos = await obter_concelhos_portugal()
    inseridos = 0

    for concelho in concelhos:
        existe = db.query(Regiao).filter(
            Regiao.nome == concelho["nome"]).first()
        if not existe:
            nova_regiao = Regiao(
                nome=concelho["nome"],
                distrito=concelho["distrito"],
                latitude=concelho["latitude"],
                longitude=concelho["longitude"],
            )
            db.add(nova_regiao)
            inseridos += 1

    db.commit()
    logger.info(f"Regioes inseridas: {inseridos}")
    return {"regioes_inseridas": inseridos}
