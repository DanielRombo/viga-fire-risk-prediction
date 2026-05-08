from sqlalchemy import String, Float, Integer, DateTime, Column
from datetime import datetime
from geoalchemy2 import Geometry
from config.database import Base


class Regiao(Base):
    __tablename__ = "regioes"

    id_regiao = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    distrito = Column(String, nullable=False)
    geometria = Column(Geometry("POLYGON"), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    area_km2 = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
