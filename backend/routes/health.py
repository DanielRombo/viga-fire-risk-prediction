"""Liveness não consulta dependências; readiness confirma apenas acesso à BD."""
import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from config.database import engine

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get('/health/live', include_in_schema=False)
def live():
    return {'estado': 'ok'}


@router.get('/health/ready', include_in_schema=False)
def ready():
    try:
        with engine.connect() as conn:
            if conn.dialect.name == 'postgresql':
                conn.execute(text("SET LOCAL statement_timeout = '2000ms'"))
            conn.execute(text('SELECT 1'))
        return {'estado': 'ok'}
    except Exception:
        logger.warning('readiness_bd_indisponivel')
        return JSONResponse(status_code=503, content={'estado': 'indisponivel'})
