"""API pública de leitura, paralela ao FWI heurístico legado."""
import logging
from datetime import date, datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from config.database import get_db
from services.leitura_fwi import ler_fwi

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/fwi-diario', tags=['FWI diário'])
Serie = Literal['auto', 'operacional', 'reconstrucao']


class RespostaFWI(BaseModel):
    id_regiao: int
    tipo: str
    estado: Literal['ok', 'desatualizado', 'indisponivel', 'em_inicializacao',
                    'em_reconstrucao', 'dados_incompletos', 'erro_fonte', 'estado_anterior_ausente']
    mensagem: str
    data_referencia: date | None
    instante_referencia_utc: datetime | None
    calculado_em: datetime | None
    ffmc: float | None
    dmc: float | None
    dc: float | None
    isi: float | None
    bui: float | None
    fwi: float | None
    origem: str | None
    metodo: str
    versao: str
    versao_xclim: str
    variante: str
    qualidade: str | None
    validade: str
    estado_inicializacao: str
    estabelecido: bool
    operacional: bool
    atualidade: str
    data_referencia_esperada: date | None
    prazo_calculo_utc: datetime | None
    atraso_permitido_minutos: int
    serie: str
    revisao: int | None
    revisao_ativa: bool | None
    proveniencia: dict
    processamento: dict | None


class HistoricoFWI(BaseModel):
    id_regiao: int
    serie: str
    versao: str
    revisao: int | None
    revisao_ativa: bool | None
    limite: int
    offset: int
    tem_mais: bool
    resultados: list[RespostaFWI]


def consultar(db, id_regiao, **opcoes):
    try:
        return ler_fwi(db, id_regiao, **opcoes)
    except SQLAlchemyError:
        logger.exception('Falha na leitura do FWI diário da região %s', id_regiao)
        raise HTTPException(503, 'Não foi possível consultar o FWI diário. Tente novamente mais tarde.')


@router.get('/{id_regiao}', response_model=RespostaFWI, summary='Consultar o novo FWI diário de uma região')
def ultimo_fwi(id_regiao: int = Path(gt=0), serie: Serie = 'auto',
               revisao: int | None = Query(default=None, ge=1), db: Session = Depends(get_db)):
    return consultar(db, id_regiao, serie=serie, revisao=revisao)


@router.get('/{id_regiao}/historico', response_model=HistoricoFWI, summary='Consultar o histórico do novo FWI diário')
def historico_fwi(id_regiao: int = Path(gt=0), serie: Serie = 'auto',
                  revisao: int | None = Query(default=None, ge=1), inicio: date | None = None,
                  fim: date | None = None, limite: int = Query(default=100, ge=1, le=366),
                  offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    return consultar(db, id_regiao, serie=serie, revisao=revisao, historico=True,
                     inicio=inicio, fim=fim, limite=limite, offset=offset)
