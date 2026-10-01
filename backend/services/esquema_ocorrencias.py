"""Adaptação transacional do esquema existente, sem apagar ocorrências."""
from sqlalchemy import text
from services.identidade_nasa import chave_observacao


def preparar_ocorrencias(engine):
    if engine.dialect.name != "postgresql":
        raise RuntimeError("A atualização do esquema de ocorrências requer PostgreSQL.")
    with engine.begin() as connection:
        connection.execute(text("LOCK TABLE ocorrencias IN ACCESS EXCLUSIVE MODE"))
        connection.execute(text("ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS nasa_chave VARCHAR(64)"))
        connection.execute(text("""ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS
                                associacao_geografica VARCHAR NOT NULL DEFAULT 'legado_nao_validado'"""))
        connection.execute(text("ALTER TABLE ocorrencias ALTER COLUMN id_regiao DROP NOT NULL"))
        # Um índice nullable aceita os duplicados históricos, mas protege observações novas.
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_ocorrencias_nasa_chave ON ocorrencias (nasa_chave)"))
        chaves = set(connection.execute(text("SELECT nasa_chave FROM ocorrencias WHERE nasa_chave IS NOT NULL")).scalars())
        antigos = connection.execute(text("""SELECT id_ocorrencia, data_inicio, latitude, longitude
            FROM ocorrencias WHERE nasa_chave IS NULL AND fonte = 'NASA FIRMS - VIIRS'
            ORDER BY id_ocorrencia""")).all()
        for registo in antigos:
            chave = chave_observacao(registo.data_inicio, registo.latitude, registo.longitude)
            if chave not in chaves:
                connection.execute(text("UPDATE ocorrencias SET nasa_chave=:chave WHERE id_ocorrencia=:id"),
                                   {"chave": chave, "id": registo.id_ocorrencia})
                chaves.add(chave)
