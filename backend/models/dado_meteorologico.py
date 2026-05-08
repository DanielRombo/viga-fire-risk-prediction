from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime
from config.database import Base


class DadoMeteorologico(Base):
    __tablename__ = "dados_meteorologicos"

    id_dado = Column(Integer, primary_key=True, index=True)
    id_regiao = Column(Integer, ForeignKey(
        "regioes.id_regiao"), nullable=False)
    data_hora = Column(DateTime, nullable=False)
    temperatura = Column(Float, nullable=True)
    humidade = Column(Float, nullable=True)
    velocidade_vento = Column(Float, nullable=True)
    direcao_vento = Column(Float, nullable=True)
    precipitacao = Column(Float, nullable=True)
    indice_seca = Column(Float, nullable=True)
    indice_vegetacao = Column(Float, nullable=True)
    fonte = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
