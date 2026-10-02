"""Executa apenas os testes ML relacionados, dentro do contentor experimental."""
import json
import subprocess
import sys
from pathlib import Path

saida = Path('/prova/resultados')
resultados = {}
for nome in ('test_artefactos_ml.py','test_inferencia_ml.py'):
    r = subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p',nome,'-v'],
                       cwd='/app',capture_output=True,text=True)
    (saida/(nome+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
    resultados[nome] = {'codigo_saida':r.returncode,'resumo':r.stderr.splitlines()[-4:]}
(saida/'testes_backend.json').write_text(json.dumps(resultados,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(resultados,ensure_ascii=False))
sys.exit(int(any(r['codigo_saida'] for r in resultados.values())))
