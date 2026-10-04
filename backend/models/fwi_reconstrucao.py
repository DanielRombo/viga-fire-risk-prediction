"""Sequências históricas revistas, separadas do FWI operacional."""
from sqlalchemy import (Column, Integer, String, Float, Date, DateTime, ForeignKey,
                        JSON, UniqueConstraint, CheckConstraint)
from config.database import Base


class FWIReconstrucao(Base):
    __tablename__ = 'fwi_reconstrucao'
    __table_args__ = (
        UniqueConstraint('id_regiao', 'versao', 'revisao', name='uq_fwi_reconstrucao_revisao'),
        CheckConstraint("estado IN ('sem_estado','em_reconstrucao','inicializado_convencionalmente',"
                        "'reconstruido','estabelecido','falha_reconstrucao')", name='ck_fwi_reconstrucao_estado'),
        CheckConstraint('data_inicial < data_operacional AND revisao > 0', name='ck_fwi_reconstrucao_janela'),
    )
    id_reconstrucao = Column(Integer, primary_key=True)
    id_regiao = Column(Integer, ForeignKey('regioes.id_regiao'), nullable=False)
    versao = Column(String(80), nullable=False)
    revisao = Column(Integer, nullable=False)
    estado = Column(String(40), nullable=False)
    data_inicial = Column(Date, nullable=False)
    data_operacional = Column(Date, nullable=False)
    data_pendente = Column(Date, nullable=False)
    configuracao = Column(JSON, nullable=False)
    assinatura_configuracao = Column(String(64), nullable=False)
    correcao = Column(JSON)
    substituida = Column(Integer, nullable=False, default=0)
    tentativas = Column(Integer, nullable=False, default=0)
    falhas_consecutivas = Column(Integer, nullable=False, default=0)
    ultima_tentativa = Column(DateTime(timezone=True))
    proxima_tentativa = Column(DateTime(timezone=True))
    codigo_erro = Column(String(50))
    causa = Column(String)
    criado_em = Column(DateTime(timezone=True), nullable=False)
    concluido_em = Column(DateTime(timezone=True))


class FWIHistoricoDia(Base):
    __tablename__ = 'fwi_historico_dia'
    __table_args__ = (
        UniqueConstraint('id_reconstrucao', 'data_referencia', name='uq_fwi_historico_dia'),
        CheckConstraint("validade IN ('calculado','desatualizado')", name='ck_fwi_historico_validade'),
        CheckConstraint('ffmc >= 0 AND ffmc <= 101 AND dmc >= 0 AND dc >= 0 AND '
                        'isi >= 0 AND bui >= 0 AND fwi >= 0', name='ck_fwi_historico_indices'),
    )
    id_dia = Column(Integer, primary_key=True)
    id_reconstrucao = Column(Integer, ForeignKey('fwi_reconstrucao.id_reconstrucao'), nullable=False)
    data_referencia = Column(Date, nullable=False)
    id_anterior = Column(Integer, ForeignKey('fwi_historico_dia.id_dia'))
    observacao = Column(JSON, nullable=False)
    horas = Column(JSON, nullable=False)
    estado_anterior = Column(JSON, nullable=False)
    assinatura = Column(String(64), nullable=False)
    ffmc = Column(Float, nullable=False)
    dmc = Column(Float, nullable=False)
    dc = Column(Float, nullable=False)
    isi = Column(Float, nullable=False)
    bui = Column(Float, nullable=False)
    fwi = Column(Float, nullable=False)
    validade = Column(String(30), nullable=False)
    calculado_em = Column(DateTime(timezone=True), nullable=False)
