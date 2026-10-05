"""Fase 7: reutiliza apenas o ensaio isolado da Fase 6, sem alterar produção."""
import asyncio
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path('/workspace')
sys.path.insert(0, str(ROOT/'backend'))
EXCLUIR = {'Lisboa','Faro','Vila Real','Funchal','Ponta Delgada'}
ANUAIS = {'Porto':'litoral norte','Bragança':'interior norte','Coimbra':'centro',
          'Castelo Branco':'interior centro','Évora':'Alentejo','Faro':'Algarve: único ponto no catálogo'}
DIAS = int(sys.argv[2])
assert DIAS in (60,365)
OUT = Path('/evidencias')/str(DIAS)
OUT.mkdir(exist_ok=True)


def modulo(nome, ficheiro):
    spec=importlib.util.spec_from_file_location(nome,ficheiro)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


prova=modulo('fase6',ROOT/'experiments/fwi_fase6/ensaio.py')
prova.OUT=OUT
analise=modulo('analise6',ROOT/'experiments/fwi_fase6/analisar.py')
analise.OUT=OUT


def ligar():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    url=os.environ['DATABASE_URL']
    assert url==f'postgresql+psycopg2://postgres@127.0.0.1/viga_fwi_test_phase7_{DIAS}'
    engine=create_engine(url)
    return engine,sessionmaker(engine,autoflush=False)


prova.ligar=ligar


def preparar():
    from sqlalchemy import text
    from models.regiao import Regiao
    from services.regioes_iniciais import inicializar_regioes
    from services.reconstrucao_fwi import preparar_estrutura_historica
    engine,factory=ligar()
    with engine.begin() as c: c.execute(text('CREATE EXTENSION IF NOT EXISTS postgis'))
    Regiao.__table__.create(engine,checkfirst=True)
    with factory() as db:
        inicializar_regioes(db)
        regioes=[{k:getattr(r,k) for k in ('id_regiao','nome','distrito','latitude','longitude')}
                 for r in db.query(Regiao).order_by(Regiao.id_regiao)]
    preparar_estrutura_historica(engine)
    prova.guardar('regioes.json',regioes)


def nomes():
    catalogo=json.loads((ROOT/'backend/data/regioes_principais.json').read_text())
    if DIAS==60: return [r['nome'] for r in catalogo if r['nome'] not in EXCLUIR]
    extras=json.loads((Path('/evidencias')/'ampliar.json').read_text()) if (Path('/evidencias')/'ampliar.json').exists() else []
    return list(dict.fromkeys([*ANUAIS,*extras]))


async def executar(modo):
    t=time.perf_counter()
    feitos=[]
    try:
        for nome in nomes():
            if modo=='recolher':
                if (OUT/f'{nome}_recolha.json').exists():
                    assert json.loads((OUT/f'{nome}_recolha.json').read_text())['estado']=='validado'
                    continue
                await prova.recolher(nome,DIAS)
            elif modo=='reconstruir':
                if (OUT/f'{nome}_resultado.json').exists(): continue
                await prova.reconstruir(nome)
                analise.preparar(nome)
            elif modo=='comparar': analise.comparar(nome)
            feitos.append(nome)
            print(modo,nome,flush=True)
    finally:
        prova.guardar(f'tempo_{modo}.json',dict(segundos=time.perf_counter()-t,regioes=feitos))


if __name__=='__main__':
    if sys.argv[1]=='preparar': preparar()
    else: asyncio.run(executar(sys.argv[1]))
