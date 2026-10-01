from sqlalchemy import text


def determinar_regiao(db, latitude, longitude):
    if db.get_bind().dialect.name != "postgresql":
        return None, "nao_determinada"
    candidatos = db.execute(text("""
        SELECT id_regiao FROM regioes
        WHERE CASE
            WHEN geometria IS NOT NULL AND ST_SRID(geometria) > 0 AND ST_IsValid(geometria)
            THEN ST_Covers(ST_Transform(geometria, 4326),
                           ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326))
            ELSE FALSE
        END
        ORDER BY id_regiao LIMIT 2
    """), {"latitude": latitude, "longitude": longitude}).scalars().all()
    if len(candidatos) == 1:
        return candidatos[0], "poligono"
    return None, "ambigua" if candidatos else "nao_determinada"
