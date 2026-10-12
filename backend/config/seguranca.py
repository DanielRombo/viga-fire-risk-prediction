"""Configuração explícita; nunca gerar uma chave JWT diferente por worker."""
import os
from urllib.parse import urlsplit


def chave_jwt():
    chave = os.getenv('SECRET_KEY', '')
    if len(chave) < 32 or chave == 'viga-secret-key-2024':
        raise ValueError('SECRET_KEY é obrigatória e deve ter pelo menos 32 caracteres aleatórios.')
    return chave


def origens_cors():
    producao = os.getenv('APP_ENV', 'development') == 'production'
    valor = os.getenv('CORS_ORIGINS', '' if producao else 'http://localhost:5173,http://127.0.0.1:5173')
    origens = [s.strip() for s in valor.split(',') if s.strip()]
    for origem in origens:
        url = urlsplit(origem)
        if (url.scheme not in ('http', 'https') or not url.hostname or url.username
                or url.password or url.path or url.query or url.fragment or '*' in origem):
            raise ValueError('CORS_ORIGINS deve conter origens HTTP/HTTPS explícitas, sem caminhos ou credenciais.')
    return origens
