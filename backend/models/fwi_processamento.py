"""Inputs horários e cursor de processamento, separados da meteorologia atual."""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, JSON, UniqueConstraint, CheckConstraint
from config.database import Base


class FWIHorario(Base):
    __tablename__ = 'fwi_horario'
    __table_args__ = (
        UniqueConstraint('id_regiao', 'instante_utc', 'produto', name='uq_fwi_horario_origem'),
        CheckConstraint("qualidade IN ('valido', 'incompleto', 'invalido')", name='ck_fwi_horario_qualidade'),
    )
    id_horario = Column(Integer, primary_key=True)
    id_regiao = Column(Integer, ForeignKey('regioes.id_regiao'), nullable=False)
    instante_utc = Column(DateTime(timezone=True), nullable=False)
    temperatura = Column(Float)
    humidade = Column(Float)
    vento = Column(Float)
    precipitacao_hora = Column(Float)
    latitude_consultada = Column(Float, nullable=False)
    longitude_consultada = Column(Float, nullable=False)
    latitude_grelha = Column(Float, nullable=False)
    longitude_grelha = Column(Float, nullable=False)
    produto = Column(String(100), nullable=False)
    ingerido_em = Column(DateTime(timezone=True), nullable=False)
    qualidade = Column(String(20), nullable=False)
    problemas = Column(JSON, nullable=False)


class FWIProcessamento(Base):
    __tablename__ = 'fwi_processamento'
    __table_args__ = (
        UniqueConstraint('id_regiao', 'versao', name='uq_fwi_processamento_regiao_versao'),
        CheckConstraint('tentativas >= 0 AND falhas_consecutivas >= 0', name='ck_fwi_tentativas'),
    )
    id_processamento = Column(Integer, primary_key=True)
    id_regiao = Column(Integer, ForeignKey('regioes.id_regiao'), nullable=False)
    versao = Column(String(80), nullable=False)
    data_pendente = Column(Date)
    estado = Column(String(40), nullable=False)
    tentativas = Column(Integer, nullable=False, default=0)
    falhas_consecutivas = Column(Integer, nullable=False, default=0)
    ultima_tentativa = Column(DateTime(timezone=True))
    proxima_tentativa = Column(DateTime(timezone=True))
    codigo_erro = Column(String(50))
    causa = Column(String)
