from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from config.database import Base


class Utilizador(Base):
    __tablename__ = "utilizadores"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    ativo = Column(Boolean, default=True)
    admin = Column(Boolean, default=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
