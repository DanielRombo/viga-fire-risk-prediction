from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime
from config.database import Base


class Ocorrencia(Base):
    __tablename__ = "ocorrencias"

    id_ocorrencia = Column(Integer, primary_key=True, index=True)
    id_regiao = Column(Integer, ForeignKey(
        "regioes.id_regiao"), nullable=False)
    data_inicio = Column(DateTime, nullable=False)
    data_fim = Column(DateTime, nullable=True)
    area_ardida = Column(Float, nullable=True)
    causa = Column(String, nullable=True)
    gravidade = Column(String, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    estado = Column(String, nullable=False)
    fonte = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
