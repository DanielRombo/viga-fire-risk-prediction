"""Smoke test HTTP real; BD e jobs simulados para não lhes causar efeitos."""
import importlib
import json
import os
import sys
import threading
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ['DATABASE_URL'] = 'postgresql+psycopg2://prova@127.0.0.1:1/prova'
os.environ['SECRET_KEY'] = 'apenas-prova-isolada-sem-autenticacao-em-teste'
sys.path.insert(0, '/app')
import httpx
import uvicorn
import xclim
from config.database import Base

with patch.object(Base.metadata, 'create_all') as tabelas, \
     patch('services.esquema_ocorrencias.preparar_ocorrencias') as esquema, \
     patch('services.regioes_iniciais.preparar_regioes') as regioes, \
     patch('services.scheduler.iniciar_scheduler') as scheduler, \
     patch('services.scheduler.atualizar_dados_meteorologicos', new_callable=AsyncMock) as recolha:
    main = importlib.import_module('main')
    servidor = uvicorn.Server(uvicorn.Config(main.app, host='127.0.0.1', port=8765, log_level='warning'))
    thread = threading.Thread(target=servidor.run, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if servidor.started:
                break
            time.sleep(0.1)
        assert servidor.started, 'O servidor não arrancou.'
        resposta = httpx.get('http://127.0.0.1:8765/', timeout=5)
        assert resposta.status_code == 200, resposta.text
        assert resposta.json() == {'status':'VIGA API online'}
        resultado = {'http':resposta.status_code,'resposta':resposta.json(), 'xclim':xclim.__version__,
                     'bd_simulada':True,'scheduler_simulado':True,'recolha_simulada':True,
                     'artefactos_na_imagem':sorted(p.name for p in Path('/app').rglob('*.joblib'))}
        assert len(resultado['artefactos_na_imagem']) == 5
        Path('/prova/resultados/arranque.json').write_text(json.dumps(resultado,indent=2),encoding='utf-8')
        print(json.dumps(resultado))
    finally:
        servidor.should_exit = True
        thread.join(timeout=10)
        assert not thread.is_alive(), 'O servidor não terminou.'
