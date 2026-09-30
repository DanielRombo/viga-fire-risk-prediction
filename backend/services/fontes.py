"""Erros de fontes externas, sem expor URLs que possam conter credenciais."""
from contextlib import contextmanager
import logging
import math

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def erro_fonte(fonte, codigo="erro_fonte", status_code=502):
    mensagens = {
        "erro_fonte": "Não foi possível obter dados da fonte externa.",
        "dados_incompletos": "A fonte devolveu dados incompletos ou inválidos.",
        "sem_dados": "A fonte não disponibiliza uma observação atual.",
    }
    logger.warning("Fonte %s: %s (HTTP %s)", fonte, codigo, status_code)
    return HTTPException(status_code=status_code, detail={
        "codigo": codigo, "fonte": fonte, "mensagem": mensagens[codigo],
    })


@contextmanager
def validar_fonte(fonte):
    try:
        yield
    except httpx.TimeoutException:
        raise erro_fonte(fonte, status_code=504) from None
    except (httpx.RequestError, httpx.HTTPStatusError):
        raise erro_fonte(fonte) from None
    except (ValueError, KeyError, TypeError, AttributeError):
        raise erro_fonte(fonte, "dados_incompletos") from None


def numero(valor):
    if isinstance(valor, bool) or valor is None:
        raise ValueError("Número indisponível")
    resultado = float(valor)
    if not math.isfinite(resultado):
        raise ValueError("Número inválido")
    return resultado
