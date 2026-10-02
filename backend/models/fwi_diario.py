"""Histórico diário independente dos dados meteorológicos existentes."""
from datetime import datetime, timezone
from sqlalchemy import (Column, Integer, String, Float, Date, DateTime, ForeignKey,
                        JSON, UniqueConstraint, CheckConstraint)
from config.database import Base


class FWIDiario(Base):
    __tablename__ = 'fwi_diario'
    __table_args__ = (
        UniqueConstraint('id_regiao', 'data_referencia', 'versao', name='uq_fwi_regiao_data_versao'),
        CheckConstraint("estado IN ('valido', 'em_inicializacao')", name='ck_fwi_estado'),
        CheckConstraint("qualidade_estado IN ('estabelecido', 'reconstrucao_historica', 'inicializacao_convencional', 'em_inicializacao')", name='ck_fwi_qualidade'),
        CheckConstraint("(estado = 'valido' AND qualidade_estado = 'estabelecido') OR (estado = 'em_inicializacao' AND qualidade_estado <> 'estabelecido')", name='ck_fwi_validade'),
        CheckConstraint('humidade >= 0 AND humidade <= 100 AND vento >= 0 AND precipitacao_24h >= 0', name='ck_fwi_meteo'),
        CheckConstraint('latitude >= -90 AND latitude <= 90 AND temperatura >= -273.15', name='ck_fwi_local'),
        CheckConstraint('ffmc >= 0 AND ffmc <= 101 AND dmc >= 0 AND dc >= 0 AND isi >= 0 AND bui >= 0 AND fwi >= 0', name='ck_fwi_indices'),
    )
    id_fwi = Column(Integer, primary_key=True)
    id_regiao = Column(Integer, ForeignKey('regioes.id_regiao'), nullable=False)
    data_referencia = Column(Date, nullable=False)
    instante_referencia_utc = Column(DateTime(timezone=True), nullable=False)
    territorio = Column(String(20), nullable=False)
    latitude = Column(Float, nullable=False)
    temperatura = Column(Float, nullable=False)
    humidade = Column(Float, nullable=False)
    vento = Column(Float, nullable=False)
    precipitacao_24h = Column(Float, nullable=False)
    ffmc = Column(Float, nullable=False)
    dmc = Column(Float, nullable=False)
    dc = Column(Float, nullable=False)
    isi = Column(Float, nullable=False)
    bui = Column(Float, nullable=False)
    fwi = Column(Float, nullable=False)
    id_anterior = Column(Integer, ForeignKey('fwi_diario.id_fwi'), nullable=True)
    estado_anterior = Column(JSON, nullable=False)
    versao = Column(String(80), nullable=False)
    estado = Column(String(30), nullable=False)
    qualidade_estado = Column(String(40), nullable=False)
    origem_dados = Column(String, nullable=False)
    origem_estado = Column(String, nullable=False)
    unidades = Column(JSON, nullable=False)
    assinatura = Column(String(64), nullable=False)
    calculado_em = Column(DateTime(timezone=True), nullable=False)
    criado_em = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
