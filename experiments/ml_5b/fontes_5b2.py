"""Aquisição limitada de fontes públicas; cache imutável com SHA-256. Sem BD."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent / 'fontes_5b2'

def obter(nome, url, intervalo=None):
    if not nome.replace('_', '').isalnum():
        raise ValueError('Nome inválido')
    ROOT.mkdir(exist_ok=True)
    destino = ROOT / (nome + '.bin')
    meta = ROOT / (nome + '.json')
    if destino.exists() or meta.exists():
        info = json.loads(meta.read_text(encoding='utf-8'))
        dados = destino.read_bytes()
        assert info['url'] == url and info.get('range') == intervalo and hashlib.sha256(dados).hexdigest() == info['sha256']
        return dados
    headers = {'User-Agent': 'VIGA-research/ML5B2'}
    if intervalo:
        headers['Range'] = intervalo
    with urlopen(Request(url, headers=headers), timeout=60) as r:
        if intervalo and r.status != 206:
            raise ValueError('Fonte não respeitou Range; não descarregar integralmente')
        dados = r.read(20_000_001)
        if len(dados) > 20_000_000:
            raise ValueError('Resposta excede o limite da amostra')
        info = dict(url=url, url_final=r.url, status=r.status, range=intervalo,
                    content_range=r.headers.get('Content-Range'),
                    content_type=r.headers.get('Content-Type'),
                    obtido_em=datetime.now(timezone.utc).isoformat(),
                    bytes=len(dados), sha256=hashlib.sha256(dados).hexdigest())
    destino.write_bytes(dados)
    meta.write_text(json.dumps(info, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return dados

if __name__ == '__main__':
    dados = obter(*sys.argv[1:])
    print(json.dumps({'bytes': len(dados), 'sha256': hashlib.sha256(dados).hexdigest()}))
