"""Ensaio real isolado. Não importa main nem inicia o scheduler.

Recolha em lote apenas neste ensaio: um pedido por região, sem retries ocultos.
O fluxo de reconstrução existente recebe as horas reais validadas desse lote.
"""
import asyncio
import hashlib
import json
import os
import resource
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, '/workspace/backend')
OUT = Path('/evidencias')
OPERACIONAL = date(2026, 10, 1)


def guardar(nome, dados):
    (OUT / nome).write_text(json.dumps(dados, ensure_ascii=False, indent=2,
                                     default=str, allow_nan=False), encoding='utf-8')


def ligar():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    url = os.environ['DATABASE_URL']
    assert url == 'postgresql+psycopg2://postgres@127.0.0.1/viga_fwi_test_phase6'
    engine = create_engine(url)
    return engine, sessionmaker(engine, autoflush=False)


def preparar():
    from sqlalchemy import text
    from models.regiao import Regiao
    from services.regioes_iniciais import inicializar_regioes, resolver_regioes
    from services.reconstrucao_fwi import preparar_estrutura_historica
    engine, factory = ligar()
    with engine.begin() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS postgis'))
    Regiao.__table__.create(engine, checkfirst=True)
    with factory() as db:
        inicializar_regioes(db)
        regioes = resolver_regioes(db)
    preparar_estrutura_historica(engine)
    guardar('regioes.json', regioes)
    print('BD isolada preparada; identificadores resolvidos por nome na BD.')


async def recolher(nome, dias):
    import httpx
    from services.meteorologia_fwi import instante_referencia
    from services.processamento_fwi import TERRITORIOS
    from services.regioes_iniciais import normalizar
    from services.open_meteo_historico_fwi import recolher_historico_fwi
    r = next(r for r in json.loads((OUT/'regioes.json').read_text()) if r['nome'] == nome)
    inicio = OPERACIONAL-timedelta(days=dias)
    t0 = instante_referencia(inicio, TERRITORIOS[normalizar(r['distrito'])])-timedelta(hours=23)
    t1 = instante_referencia(OPERACIONAL-timedelta(days=1), TERRITORIOS[normalizar(r['distrito'])])
    evidencia = {'regiao': r, 'data_operacional': OPERACIONAL, 'inicio': inicio,
        'janela_dias': dias, 'inicio_utc': t0, 'fim_utc': t1, 'chamadas_externas': 0,
        'retries': 0, 'ingerido_em': datetime.now(timezone.utc)}

    class Cliente:
        async def get(self, url, params):
            evidencia['chamadas_externas'] += 1
            evidencia['url'] = url
            evidencia['parametros'] = params
            async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=10)) as client:
                resposta = await client.get(url, params=params)
            bruto = resposta.content
            (OUT/f'{nome}_resposta.json').write_bytes(bruto)
            evidencia.update(http_status=resposta.status_code,
                sha256=hashlib.sha256(bruto).hexdigest(), bytes=len(bruto))
            return resposta

    inicio_tempo = time.perf_counter()
    try:
        horas = await recolher_historico_fwi(r['latitude'], r['longitude'], t0, t1,
            agora=evidencia['ingerido_em'], cliente=Cliente())
        assert len(horas) == dias*24, 'Lacuna na janela horária'
        assert len({h.instante_utc for h in horas}) == len(horas), 'Horas duplicadas'
        assert all(h.qualidade == 'valido' for h in horas), 'Horas nulas ou inválidas'
        assert all(h.instante_utc == t0+timedelta(hours=i) for i,h in enumerate(horas)), 'Descontinuidade'
        evidencia.update(estado='validado', horas_utilizadas=len(horas),
            latitude_grelha=horas[0].latitude_grelha, longitude_grelha=horas[0].longitude_grelha,
            produto=horas[0].produto,
            produto_confirmacao='Modelo explicitamente pedido; a resposta não contém identificação independente do modelo.')
    except Exception as erro:
        evidencia.update(estado='bloqueado', erro_tipo=type(erro).__name__, erro=str(erro))
        raise
    finally:
        evidencia['duracao_segundos'] = time.perf_counter()-inicio_tempo
        guardar(f'{nome}_recolha.json', evidencia)


async def reconstruir(nome):
    import numpy as np
    from dataclasses import replace
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from config.database import get_db
    from routes.fwi_diario import router
    from services.open_meteo_fwi import interpretar_resposta
    from services.open_meteo_historico_fwi import PRODUTO
    from services.processamento_fwi import TERRITORIOS
    from services.regioes_iniciais import normalizar
    from services.fwi_diario import EstadoFWI, QualidadeEstado
    from services import reconstrucao_fwi as h
    from models.fwi_reconstrucao import FWIHistoricoDia
    from models.fwi_processamento import FWIHorario
    from models.fwi_diario import FWIDiario
    evidencia = json.loads((OUT/f'{nome}_recolha.json').read_text())
    assert evidencia['estado'] == 'validado'
    r = evidencia['regiao']
    inicio = date.fromisoformat(evidencia['inicio'])
    bruto = (OUT/f'{nome}_resposta.json').read_bytes()
    assert hashlib.sha256(bruto).hexdigest() == evidencia['sha256']
    horas = [replace(hora, produto=PRODUTO) for hora in interpretar_resposta(json.loads(bruto),
        r['latitude'], r['longitude'], datetime.fromisoformat(evidencia['inicio_utc']),
        datetime.fromisoformat(evidencia['fim_utc']), datetime.fromisoformat(evidencia['ingerido_em']))]
    por_instante = {hora.instante_utc: hora for hora in horas}
    chamadas = 0
    async def fonte(lat, lon, primeiro, ultimo, **kwargs):
        nonlocal chamadas
        chamadas += 1
        assert (lat,lon) == (r['latitude'], r['longitude'])
        return [por_instante[primeiro+timedelta(hours=i)] for i in range(24)]
    engine, factory = ligar()
    app = FastAPI()
    app.include_router(router, prefix='/api')
    def db_api():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = db_api
    client = TestClient(app)
    prefixo = f"/api/fwi-diario/{r['id_regiao']}"
    guardar(f'{nome}_api_antes.json', client.get(prefixo).json())
    semente = EstadoFWI(r['id_regiao'], inicio-timedelta(days=1), 85., 6., 15.,
        QualidadeEstado.CONVENCIONAL, 'Ensaio Fase 6: semente convencional 85/6/15, sem estabelecimento científico.')
    t0 = time.perf_counter()
    h.iniciar_reconstrucao(factory, id_regiao=r['id_regiao'], latitude=r['latitude'],
        longitude=r['longitude'], territorio=TERRITORIOS[normalizar(r['distrito'])],
        data_operacional=OPERACIONAL, data_inicial=inicio, estado_inicial=semente)
    resultado = await h.reconstruir(factory, r['id_regiao'], limite_dias=evidencia['janela_dias'], recolher=fonte)
    duracao = time.perf_counter()-t0
    guardar(f'{nome}_estado.json', resultado)
    assert resultado['estado'] == 'reconstruido', resultado
    with factory() as db:
        dias = db.query(FWIHistoricoDia).filter_by(id_reconstrucao=resultado['id_reconstrucao']).order_by(FWIHistoricoDia.data_referencia).all()
        assert len(dias) == evidencia['janela_dias']
        exportados = []
        for i,dia in enumerate(dias):
            assert dia.data_referencia == inicio+timedelta(days=i)
            assert len(dia.horas) == 24
            assert dia.id_anterior == (dias[i-1].id_dia if i else None)
            assert dia.validade == 'calculado'
            assert all(np.isfinite(getattr(dia,k)) and getattr(dia,k)>=0 for k in h.CAMPOS_INDICES)
            exportados.append({c.name: getattr(dia,c.name) for c in dia.__table__.columns})
        assert db.query(FWIDiario).count() == 0
        horarios = db.query(FWIHorario).filter_by(id_regiao=r['id_regiao']).count()
    guardar(f'{nome}_dias.json', exportados)
    repeticao = await h.reconstruir(factory, r['id_regiao'], limite_dias=1, recolher=fonte)
    assert repeticao['calculados'] == 0 and repeticao['estado'] == 'reconstruido'
    resposta = client.get(prefixo)
    assert resposta.status_code == 200
    api = resposta.json()
    assert api['operacional'] is False and api['estabelecido'] is False
    assert api['estado_inicializacao'] == 'reconstruido' and api['fwi'] is not None
    assert api['data_referencia'] == str(OPERACIONAL-timedelta(days=1))
    historico = client.get(prefixo+'/historico?limite=366').json()
    assert len(historico['resultados']) == len(dias)
    assert [d['data_referencia'] for d in historico['resultados']] == [str(d.data_referencia) for d in dias]
    guardar(f'{nome}_api.json', api)
    guardar(f'{nome}_api_historico.json', historico)
    estatisticas = {k: dict(zip(['min','p05','p25','mediana','p75','p95','max'],
        np.percentile([getattr(d,k) for d in dias], [0,5,25,50,75,95,100]).tolist())) for k in h.CAMPOS_INDICES}
    guardar(f'{nome}_resultado.json', dict(estado=resultado, estatisticas=estatisticas,
        duracao_reconstrucao_segundos=duracao, duracao_recolha_segundos=evidencia['duracao_segundos'],
        horas=horarios, dias=len(dias), chamadas_externas=evidencia['chamadas_externas'],
        leituras_lote=chamadas, retries=0, pico_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        idempotencia=True, api=True, anomalias_estruturais=0))
    print(nome, resultado, 'segundos:', duracao, flush=True)


if __name__ == '__main__':
    if sys.argv[1] == 'preparar':
        preparar()
    elif sys.argv[1] == 'recolher':
        asyncio.run(recolher(sys.argv[2], int(sys.argv[3])))
    elif sys.argv[1] == 'reconstruir':
        asyncio.run(reconstruir(sys.argv[2]))
