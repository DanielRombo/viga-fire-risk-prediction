"""Regista dependências e dimensões da imagem experimental, sem segredos."""
import json
from pathlib import Path

origem = Path('/prova')
destino = Path('/saida')
def ler(nome):
    return dict(linha.split('==',1) for linha in (origem/nome).read_text().splitlines() if '==' in linha)
antes, depois = ler('antes.txt'), ler('depois.txt')
novos = {k:v for k,v in depois.items() if k not in antes}
alterados = {k:[v,depois.get(k)] for k,v in antes.items() if depois.get(k) != v}
assert not alterados, alterados
for original, copia in [('antes.txt','baseline.lock'),('depois.txt','xclim.lock')]:
    (destino/copia).write_bytes((origem/original).read_bytes())
a = int((origem/'tamanho_antes.txt').read_text().split()[0])
d = int((origem/'tamanho_depois.txt').read_text().split()[0])
(destino/'resultados'/'dependencias.json').write_text(json.dumps({
    'novos':novos,'alterados':alterados,'site_packages_antes_bytes':a,
    'site_packages_depois_bytes':d,'adicional_bytes':d-a},indent=2),encoding='utf-8')
print(json.dumps({'novos':novos,'alterados':alterados,'adicional_bytes':d-a}))
