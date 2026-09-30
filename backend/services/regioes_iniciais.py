"""Catálogo mínimo de produção; os identificadores pertencem à base de dados."""
import json
import unicodedata
from pathlib import Path

from sqlalchemy import text
from config.database import SessionLocal
from models.regiao import Regiao

CATALOGO = json.loads((Path(__file__).resolve().parents[1] / "data/regioes_principais.json").read_text(encoding="utf-8"))
REGIOES_RECOLHA = [r for r in CATALOGO if r["recolha_automatica"]]


def normalizar(valor):
    return " ".join("".join(c for c in unicodedata.normalize("NFD", valor or "")
                           if not unicodedata.combining(c)).casefold().split())


def existentes(db):
    return db.query(Regiao.id_regiao, Regiao.nome, Regiao.distrito,
                    Regiao.latitude, Regiao.longitude).order_by(Regiao.id_regiao).all()


def encontrar(regiao, registos):
    candidatos = [r for r in registos if normalizar(r.nome) == normalizar(regiao["nome"])]
    correspondencias = [r for r in candidatos if normalizar(r.distrito) == normalizar(regiao["distrito"])]
    if correspondencias:
        # Não apagar duplicados históricos; reutilizar o identificador mais antigo.
        return correspondencias[0]
    desconhecidos = [r for r in candidatos if normalizar(r.distrito) in ("", "desconhecido")]
    if len(desconhecidos) == 1:
        return desconhecidos[0]
    if desconhecidos:
        raise ValueError(f"Região ambígua na base de dados: {regiao['nome']}.")
    return None


def inicializar_regioes(db):
    try:
        # Serializar inicializações concorrentes sem modificar o esquema existente.
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("LOCK TABLE regioes IN SHARE ROW EXCLUSIVE MODE"))
        registos = existentes(db)
        inseridas = 0
        for regiao in CATALOGO:
            if encontrar(regiao, registos) is None:
                db.add(Regiao(**{k: v for k, v in regiao.items() if k != "recolha_automatica"}))
                inseridas += 1
        db.commit()
        return inseridas
    except Exception:
        db.rollback()
        raise


def preparar_regioes():
    with SessionLocal() as db:
        inicializar_regioes(db)


def resolver_regioes(db):
    registos = existentes(db)
    resolvidas = []
    for regiao in REGIOES_RECOLHA:
        existente = encontrar(regiao, registos)
        if existente is None:
            raise ValueError(f"Região necessária não preparada: {regiao['nome']}.")
        resolvidas.append({"id_regiao": existente.id_regiao, "nome": regiao["nome"],
                           "latitude": existente.latitude, "longitude": existente.longitude})
    return resolvidas
