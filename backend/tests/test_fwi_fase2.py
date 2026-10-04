"""Recolha, recuperação e concorrência. Sem repetir a prova científica da Fase 1."""
import asyncio
import math
import os
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, AsyncMock
import httpx
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DATABASE_URL','postgresql+psycopg2://test@127.0.0.1:1/viga_test')
from services.open_meteo_fwi import recolher_horas_fwi, interpretar_resposta, ErroRecolhaFWI, UNIDADES
from services.processamento_fwi import (preparar_estrutura_fwi, processar_regiao, executar_ciclo_fwi,
    preparar_dia_persistido, data_db_utc)
from services.meteorologia_fwi import (TerritorioFWI, ObservacaoDiariaFWI, UNIDADES_FWI,
    instante_referencia)
from services.fwi_diario import EstadoFWI, QualidadeEstado, ResultadoFWI, VERSAO_FWI
from services.persistencia_fwi import guardar_resultado_fwi
from models.fwi_diario import FWIDiario
from models.fwi_processamento import FWIHorario, FWIProcessamento

AGORA = datetime(2026,10,4,14,tzinfo=timezone.utc)
REGIAO = {'id_regiao':1,'distrito':'Lisboa','latitude':38.7223,'longitude':-9.1393}


def resposta(inicio,fim,alterar=None):
    n = int((fim-inicio).total_seconds()/3600)+1
    dados = {'latitude':38.7,'longitude':-9.1,'utc_offset_seconds':0,'hourly_units':dict(UNIDADES),
             'hourly':{'time':[(inicio+timedelta(hours=i)).replace(tzinfo=None).isoformat(timespec='minutes') for i in range(n)],
                       'temperature_2m':[20]*n,'relative_humidity_2m':[50]*n,
                       'wind_speed_10m':[0]*n,'precipitation':[0]*n}}
    if alterar:
        alterar(dados)
    return dados


class ClienteHorarioTests(unittest.IsolatedAsyncioTestCase):
    async def pedir(self,alterar=None,handler=None):
        fim = AGORA.replace(hour=12)
        inicio = fim-timedelta(hours=23)
        def mock(request):
            params = request.url.params
            self.assertEqual(params['temperature_unit'],'celsius')
            self.assertEqual(params['wind_speed_unit'],'kmh')
            self.assertEqual(params['precipitation_unit'],'mm')
            self.assertEqual(params['timezone'],'GMT')
            self.assertNotIn('current',params)
            self.assertEqual(params['start_hour'],inicio.strftime('%Y-%m-%dT%H:%M'))
            self.assertEqual(params['end_hour'],fim.strftime('%Y-%m-%dT%H:%M'))
            return handler(request) if handler else httpx.Response(200,json=resposta(inicio,fim,alterar))
        async with httpx.AsyncClient(transport=httpx.MockTransport(mock)) as cliente:
            return await recolher_horas_fwi(38.7,-9.1,inicio,fim,agora=AGORA,cliente=cliente)

    async def test_recolha_valida_unidades_utc_zero(self):
        horas = await self.pedir()
        self.assertEqual(len(horas),24)
        self.assertTrue(all(h.precipitacao_hora == 0 and h.qualidade == 'valido' for h in horas))
        self.assertEqual(horas[-1].instante_utc,AGORA.replace(hour=12))

    async def test_nulo_e_invalido_nao_viram_zero(self):
        for valor,qualidade in [(None,'incompleto'),(-1,'invalido'),('NaN','invalido')]:
            horas = await self.pedir(lambda d:d['hourly']['precipitation'].__setitem__(0,valor))
            self.assertIsNone(horas[0].precipitacao_hora)
            self.assertEqual(horas[0].qualidade,qualidade)
        fim=AGORA.replace(hour=12)
        for valor in (math.nan,math.inf):
            d=resposta(fim-timedelta(hours=23),fim)
            d['hourly']['precipitation'][0]=valor
            horas=interpretar_resposta(d,38.7,-9.1,fim-timedelta(hours=23),fim,AGORA)
            self.assertEqual(horas[0].qualidade,'invalido')

    async def test_unidades_offset_duplicados_e_estrutura_rejeitados(self):
        alteracoes = [lambda d:d['hourly_units'].update(precipitation='inch'),
                     lambda d:d.update(utc_offset_seconds=3600),
                     lambda d:d['hourly']['time'].__setitem__(1,d['hourly']['time'][0]),
                     lambda d:d['hourly']['temperature_2m'].pop()]
        for alterar in alteracoes:
            with self.assertRaises(ErroRecolhaFWI) as ctx:
                await self.pedir(alterar)
            self.assertEqual(ctx.exception.codigo,'resposta_invalida')

    async def test_fonte_timeout_sem_dados_distintos(self):
        def timeout(request):
            raise httpx.ReadTimeout('simulado',request=request)
        for handler,codigo in [(timeout,'timeout'),(lambda r:httpx.Response(503),'erro_fonte')]:
            with self.assertRaises(ErroRecolhaFWI) as ctx:
                await self.pedir(handler=handler)
            self.assertEqual(ctx.exception.codigo,codigo)
        def vazio(d):
            for k in d['hourly']:
                d['hourly'][k]=[]
        with self.assertRaises(ErroRecolhaFWI) as ctx:
            await self.pedir(vazio)
        self.assertEqual(ctx.exception.codigo,'sem_dados')

    async def test_historico_fora_janela_e_futuro_nao_fazem_pedido(self):
        cliente=AsyncMock()
        for inicio,fim,codigo in [(AGORA-timedelta(days=100),AGORA-timedelta(days=99),'historico_necessario'),
                                   (AGORA-timedelta(hours=23),AGORA,'janela_invalida')]:
            with self.assertRaises(ErroRecolhaFWI) as ctx:
                await recolher_horas_fwi(38,-9,inicio,fim,agora=AGORA,cliente=cliente)
            self.assertEqual(ctx.exception.codigo,codigo)
        cliente.get.assert_not_called()


class RecuperacaoTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine(os.getenv('VIGA_FWI_TEST_DATABASE_URL','sqlite://'))
        if self.engine.dialect.name=='sqlite':
            @event.listens_for(self.engine,'connect')
            def configurar(conn,_):
                conn.isolation_level=None
                conn.execute('PRAGMA foreign_keys=ON')
            @event.listens_for(self.engine,'begin')
            def begin(conn):
                conn.exec_driver_sql('BEGIN')
        else:
            self.assertTrue(self.engine.url.database.startswith('viga_fwi_test_'))
        self.addCleanup(self.engine.dispose)
        with self.engine.begin() as conn:
            conn.execute(text('CREATE TABLE regioes (id_regiao INTEGER PRIMARY KEY)'))
            conn.execute(text('INSERT INTO regioes VALUES (1),(2)'))
        preparar_estrutura_fwi(self.engine)
        self.addCleanup(self.limpar)
        self.factory=sessionmaker(self.engine,autoflush=False)
        self.pedidos=[]
        self.falha=None
        self.alterar=None
        async def fonte(lat,lon,inicio,fim,*,agora):
            self.pedidos.append((lat,inicio,fim))
            if self.falha and self.falha(lat,fim):
                raise ErroRecolhaFWI('erro_fonte','Falha simulada da fonte.')
            d=resposta(inicio,fim,self.alterar)
            return interpretar_resposta(d,lat,lon,inicio,fim,agora)
        self.fonte=fonte

    def limpar(self):
        for m in (FWIProcessamento,FWIHorario,FWIDiario):
            m.__table__.drop(self.engine)
        with self.engine.begin() as conn:
            conn.execute(text('DROP TABLE regioes'))

    def semear(self,data=date(2026,10,3),regiao=REGIAO,territorio=TerritorioFWI.CONTINENTE,qualidade=QualidadeEstado.ESTABELECIDO):
        obs=ObservacaoDiariaFWI(regiao['id_regiao'],data,instante_referencia(data,territorio),territorio,
            20,50,0,0,regiao['latitude'],'Estado sintético exclusivo do teste',UNIDADES_FWI)
        anterior=EstadoFWI(regiao['id_regiao'],data-timedelta(days=1),85,6,15,qualidade,'Fixture de recuperação')
        # Testar orquestração, não repetir a validação científica da Fase 1.
        r=ResultadoFWI(obs,anterior,85,6,15,1,6,1,AGORA)
        with self.factory.begin() as db:
            guardar_resultado_fwi(db,r)

    def executar(self,agora=AGORA,regiao=REGIAO):
        return asyncio.run(processar_regiao(self.factory,regiao,agora=agora,recolher=self.fonte))

    def cursor(self):
        with self.factory() as db:
            return db.query(FWIProcessamento).filter_by(id_regiao=1).one()

    def test_um_dia_idempotencia_e_janela_persistida(self):
        self.semear()
        self.assertEqual(self.executar()['calculados'],1)
        self.assertEqual(self.executar()['calculados'],0)
        self.assertEqual(len(self.pedidos),1)
        with self.factory() as db:
            self.assertEqual(db.query(FWIHorario).count(),24)
            self.assertEqual(db.query(FWIDiario).count(),2)
            obs=preparar_dia_persistido(db,REGIAO,date(2026,10,4),TerritorioFWI.CONTINENTE)
            self.assertEqual(obs.precipitacao_24h,0)
        self.assertEqual(self.cursor().data_pendente,date(2026,10,5))

    def test_varios_dias_ordem_limite_e_retoma(self):
        self.semear(date(2026,9,29))
        self.assertEqual(self.executar()['calculados'],3)
        self.assertEqual([p[2].date() for p in self.pedidos],[date(2026,9,30),date(2026,10,1),date(2026,10,2)])
        self.assertEqual(self.executar()['calculados'],2)

    def test_falha_dia_intermedio_retry_e_retoma(self):
        self.semear(date(2026,10,1))
        self.falha=lambda lat,t:t.date()==date(2026,10,3)
        self.assertEqual(self.executar()['calculados'],1)
        cursor=self.cursor()
        self.assertEqual(cursor.data_pendente,date(2026,10,3))
        self.assertEqual(cursor.codigo_erro,'erro_fonte')
        self.assertEqual(cursor.tentativas,2)
        self.assertIsNotNone(cursor.proxima_tentativa)
        self.assertEqual(self.executar()['calculados'],0)
        self.assertEqual(len(self.pedidos),2)
        self.falha=None
        self.assertEqual(self.executar(AGORA+timedelta(minutes=16))['calculados'],2)
        self.assertEqual(self.cursor().falhas_consecutivas,0)

    def test_nulo_lacuna_e_reparacao_persistida(self):
        self.semear()
        self.alterar=lambda d:d['hourly']['precipitation'].__setitem__(2,None)
        self.assertEqual(self.executar()['calculados'],0)
        with self.factory() as db:
            self.assertEqual(db.query(FWIHorario).count(),24)
            self.assertEqual(db.query(FWIHorario).filter_by(qualidade='incompleto').one().precipitacao_hora,None)
        self.alterar=None
        self.assertEqual(self.executar(AGORA+timedelta(minutes=16))['calculados'],1)

    def test_intervalo_em_falta_nao_calcula(self):
        self.semear()
        def lacuna(d):
            for lista in d['hourly'].values():
                lista.pop(5)
        self.alterar=lacuna
        self.assertEqual(self.executar()['calculados'],0)
        self.assertEqual(self.cursor().data_pendente,date(2026,10,4))

    def test_sem_estado_ou_estado_inicial_nao_inventa_sequencia(self):
        self.assertEqual(self.executar()['estado'],'inicializacao_necessaria')
        with self.factory() as db:
            self.assertEqual(db.query(FWIDiario).count(),0)
            self.assertEqual(db.query(FWIHorario).count(),24)
        self.semear(qualidade=QualidadeEstado.CONVENCIONAL)
        self.assertEqual(self.executar(AGORA+timedelta(hours=7))['calculados'],0)
        with self.factory() as db:
            self.assertEqual(db.query(FWIDiario).filter_by(estado='valido').count(),0)

    def test_continente_madeira_acores_antes_e_depois(self):
        # Usar regiões distintas em subtestes através de rollback da fixture.
        for distrito,lat,territorio,hora in [('Lisboa',38.7,TerritorioFWI.CONTINENTE,12),
                                            ('Madeira',32.6,TerritorioFWI.MADEIRA,12),
                                            ('Açores',37.7,TerritorioFWI.ACORES,13)]:
            regiao={**REGIAO,'distrito':distrito,'latitude':lat}
            self.semear(regiao=regiao,territorio=territorio)
            self.assertEqual(self.executar(AGORA.replace(hour=hora),regiao)['calculados'],0)
            self.assertEqual(self.executar(AGORA.replace(hour=hora,minute=16),regiao)['calculados'],1)
            self.assertEqual(self.pedidos[-1][2].hour,hora)
            with self.factory.begin() as db:
                db.query(FWIProcessamento).delete()
                db.query(FWIHorario).delete()
                # Remover descendentes antes dos antecessores na BD de teste.
                for r in db.query(FWIDiario).order_by(FWIDiario.data_referencia.desc()).all():
                    db.delete(r)
                    db.flush()

    def test_erro_regiao_nao_bloqueia_outra(self):
        r2={**REGIAO,'id_regiao':2,'latitude':41.1,'distrito':'Porto'}
        self.semear()
        self.semear(regiao=r2)
        self.falha=lambda lat,t:lat==REGIAO['latitude']
        r=asyncio.run(executar_ciclo_fwi(self.factory,regioes=[REGIAO,r2],agora=AGORA,recolher=self.fonte))
        self.assertEqual([x['calculados'] for x in r],[0,1])

    def test_rollback_de_fwi_nao_avanca_cursor(self):
        self.semear()
        def falhar(db,r):
            guardar_resultado_fwi(db,r)
            raise RuntimeError('Falha simulada depois do INSERT')
        with patch('services.processamento_fwi.guardar_resultado_fwi',side_effect=falhar):
            self.assertEqual(self.executar()['calculados'],0)
        with self.factory() as db:
            self.assertEqual(db.query(FWIDiario).count(),1)
            self.assertEqual(db.query(FWIHorario).count(),24)
        self.assertEqual(self.cursor().data_pendente,date(2026,10,4))
        self.assertEqual(self.executar(AGORA+timedelta(minutes=16))['calculados'],1)
        self.assertEqual(len(self.pedidos),1)  # Retoma dos inputs locais.

    def test_concorrencia_postgresql(self):
        if self.engine.dialect.name!='postgresql':
            self.skipTest('Requer PostgreSQL descartável.')
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        entrou,libertar=Event(),Event()
        self.semear()
        async def lento(*a,**kw):
            entrou.set()
            self.assertTrue(libertar.wait(10))
            return await self.fonte(*a,**kw)
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(lambda:asyncio.run(processar_regiao(self.factory,REGIAO,agora=AGORA,recolher=lento)))
            try:
                self.assertTrue(entrou.wait(10))
                b=pool.submit(self.executar)
                self.assertEqual(b.result(5)['estado'],'ocupada')
            finally:
                libertar.set()
            self.assertEqual(a.result(15)['calculados'],1)
        with self.factory() as db:
            self.assertEqual(db.query(FWIDiario).count(),2)
            self.assertEqual(db.query(FWIHorario).count(),24)

    def test_lacuna_no_cursor_nao_e_saltada(self):
        self.semear(date(2026,10,1))
        self.falha=lambda lat,t:True
        self.executar()
        self.semear(date(2026,10,3))  # Simula inserção externa posterior à lacuna.
        self.falha=None
        self.assertEqual(self.executar(AGORA+timedelta(minutes=16))['calculados'],0)
        self.assertEqual(self.cursor().data_pendente,date(2026,10,2))
        self.assertIn('lacuna',self.cursor().causa)

    def test_falha_de_commit_reverte_fwi_cursor_e_horas(self):
        self.semear()
        def falhar(sessao):
            if not sessao.in_nested_transaction():
                raise RuntimeError('Commit simulado indisponível')
        event.listen(self.factory,'before_commit',falhar)
        try:
            r=asyncio.run(executar_ciclo_fwi(self.factory,regioes=[REGIAO],agora=AGORA,recolher=self.fonte))
            self.assertEqual(r[0]['estado'],'erro_transacao')
            self.assertEqual(r[0]['calculados'],0)
        finally:
            event.remove(self.factory,'before_commit',falhar)
        with self.factory() as db:
            self.assertEqual(db.query(FWIDiario).count(),1)
            self.assertEqual(db.query(FWIHorario).count(),0)
            self.assertEqual(db.query(FWIProcessamento).count(),0)
        self.assertEqual(self.executar()['calculados'],1)

    def test_horas_validas_nao_sao_reescritas_ao_reparar_lacuna(self):
        self.semear()
        self.alterar=lambda d:d['hourly']['precipitation'].__setitem__(0,None)
        self.executar()
        def revisao(d):
            d['hourly']['precipitation']=[2]*24
        self.alterar=revisao
        self.assertEqual(self.executar(AGORA+timedelta(minutes=16))['calculados'],1)
        with self.factory() as db:
            atual=db.query(FWIDiario).filter_by(data_referencia=date(2026,10,4)).one()
            self.assertEqual(atual.precipitacao_24h,2)  # Só a hora ausente foi reparada.

    def test_historico_necessario_fica_registado(self):
        self.semear(date(2026,1,1))
        r=asyncio.run(processar_regiao(self.factory,REGIAO,agora=AGORA))
        self.assertEqual(r['estado'],'reconstrucao_necessaria')
        self.assertEqual(self.cursor().data_pendente,date(2026,1,2))
        self.assertEqual(self.cursor().codigo_erro,'historico_necessario')


if __name__=='__main__':
    unittest.main()
