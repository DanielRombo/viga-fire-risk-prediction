"""Orquestração histórica, sem repetir a prova científica da Fase 1."""
import asyncio
import os
import sys
import threading
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import httpx
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg2://test@127.0.0.1:1/viga_test')
from models.fwi_diario import FWIDiario
from models.fwi_processamento import FWIHorario, FWIProcessamento
from models.fwi_reconstrucao import FWIReconstrucao, FWIHistoricoDia
from services import reconstrucao_fwi as historico
from services.fwi_diario import EstadoFWI, QualidadeEstado, ResultadoFWI
from services.meteorologia_fwi import (TerritorioFWI, DadosFWIInvalidos, ObservacaoDiariaFWI,
    UNIDADES_FWI, instante_referencia)
from services.persistencia_fwi import guardar_resultado_fwi, restaurar_estado
from services.open_meteo_fwi import interpretar_resposta, UNIDADES, ErroRecolhaFWI
from services.open_meteo_historico_fwi import recolher_historico_fwi, PRODUTO, URL

AGORA = datetime(2026, 10, 4, 15, tzinfo=timezone.utc)


def resposta(inicio, fim):
    n = int((fim-inicio).total_seconds()/3600)+1
    return {'latitude': 38.7, 'longitude': -9.1, 'utc_offset_seconds': 0,
        'hourly_units': dict(UNIDADES), 'hourly': {
            'time': [(inicio+timedelta(hours=i)).replace(tzinfo=None).isoformat(timespec='minutes') for i in range(n)],
            'temperature_2m': [20]*n, 'relative_humidity_2m': [50]*n,
            'wind_speed_10m': [0]*n, 'precipitation': [0]*n}}


class ArchiveTests(unittest.IsolatedAsyncioTestCase):
    async def test_contrato_archive_produto_unidades_janela(self):
        inicio = datetime(2024, 2, 28, 13, tzinfo=timezone.utc)
        fim = inicio+timedelta(hours=23)
        def handler(req):
            self.assertEqual(str(req.url).split('?')[0], URL)
            self.assertEqual(req.url.params['models'], 'ecmwf_ifs')
            self.assertEqual(req.url.params['timezone'], 'GMT')
            self.assertEqual(req.url.params['temperature_unit'], 'celsius')
            self.assertEqual(req.url.params['wind_speed_unit'], 'kmh')
            self.assertEqual(req.url.params['precipitation_unit'], 'mm')
            self.assertEqual(req.url.params['start_date'], '2024-02-28')
            self.assertEqual(req.url.params['end_date'], '2024-02-29')
            self.assertNotIn('current', req.url.params)
            return httpx.Response(200, json=resposta(inicio-timedelta(hours=13), fim+timedelta(hours=11)))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            horas = await recolher_historico_fwi(38.7, -9.1, inicio, fim, agora=AGORA, cliente=client)
        self.assertEqual(len(horas), 24)
        self.assertTrue(all(h.produto == PRODUTO and h.precipitacao_hora == 0 for h in horas))

    async def test_falhas_sem_fallback(self):
        inicio = AGORA-timedelta(days=400)
        fim = inicio+timedelta(hours=23)
        for modo, codigo in [('http', 'erro_fonte'), ('timeout', 'timeout'), ('vazio', 'sem_dados'), ('nulo', None)]:
            with self.subTest(modo=modo):
                def handler(req):
                    if modo == 'timeout':
                        raise httpx.ReadTimeout('simulado', request=req)
                    if modo == 'http':
                        return httpx.Response(503)
                    dados = resposta(inicio, fim)
                    if modo == 'vazio':
                        dados['hourly'] = {k: [] for k in dados['hourly']}
                    else:
                        dados['hourly']['precipitation'][0] = None
                    return httpx.Response(200, json=dados)
                async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                    if codigo:
                        with self.assertRaises(ErroRecolhaFWI) as ctx:
                            await recolher_historico_fwi(38, -9, inicio, fim, agora=AGORA, cliente=client)
                        self.assertEqual(ctx.exception.codigo, codigo)
                    else:
                        horas = await recolher_historico_fwi(38, -9, inicio, fim, agora=AGORA, cliente=client)
                        self.assertIsNone(horas[0].precipitacao_hora)


class ReconstrucaoTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(os.getenv('VIGA_FWI_TEST_DATABASE_URL', 'sqlite://'))
        if self.engine.dialect.name == 'sqlite':
            @event.listens_for(self.engine, 'connect')
            def connect(conn, _):
                conn.isolation_level = None
                conn.execute('PRAGMA foreign_keys=ON')
            @event.listens_for(self.engine, 'begin')
            def begin(conn):
                conn.exec_driver_sql('BEGIN')
        else:
            self.assertTrue(self.engine.url.database.startswith('viga_fwi_test_'))
        self.addCleanup(self.engine.dispose)
        with self.engine.begin() as conn:
            conn.execute(text('CREATE TABLE regioes (id_regiao INTEGER PRIMARY KEY)'))
            conn.execute(text('INSERT INTO regioes VALUES (1),(2)'))
        historico.preparar_estrutura_historica(self.engine)
        self.addCleanup(self.limpar)
        self.factory = sessionmaker(self.engine, autoflush=False)
        self.pedidos = []
        self.falha = None
        self.chuva = 0
        self.lacuna = False
        async def fonte(lat, lon, inicio, fim, *, agora):
            self.pedidos.append((lat, lon, inicio, fim))
            if fim.date() == self.falha:
                raise ErroRecolhaFWI('erro_fonte', 'Falha histórica simulada.')
            dados = resposta(inicio, fim)
            dados['hourly']['precipitation'] = [self.chuva]*24
            if self.lacuna:
                for valores in dados['hourly'].values():
                    valores.pop(5)
            return [replace(h, produto=PRODUTO) for h in interpretar_resposta(dados, lat, lon, inicio, fim, agora)]
        self.fonte = fonte

    def limpar(self):
        for m in (FWIHistoricoDia, FWIReconstrucao, FWIProcessamento, FWIHorario, FWIDiario):
            m.__table__.drop(self.engine)
        with self.engine.begin() as conn:
            conn.execute(text('DROP TABLE regioes'))

    def iniciar(self, inicio=date(2024, 2, 28), dias=3, territorio=TerritorioFWI.CONTINENTE, regiao=1, semente=None):
        semente = semente or EstadoFWI(regiao, inicio-timedelta(days=1), 85, 6, 15,
                                       QualidadeEstado.CONVENCIONAL, 'Semente convencional explícita de teste')
        lat, lon = {TerritorioFWI.CONTINENTE: (38.7, -9.1), TerritorioFWI.MADEIRA: (32.65, -16.9),
                    TerritorioFWI.ACORES: (37.74, -25.67)}[territorio]
        return historico.iniciar_reconstrucao(self.factory, id_regiao=regiao, latitude=lat,
            longitude=lon, territorio=territorio, data_operacional=inicio+timedelta(days=dias),
            estado_inicial=semente, data_inicial=inicio, agora=AGORA)

    def executar(self, limite=366, agora=AGORA, regiao=1):
        return asyncio.run(historico.reconstruir(self.factory, regiao, limite_dias=limite,
                                               agora=agora, recolher=self.fonte))

    def dias(self, revisao=1):
        with self.factory() as db:
            r = db.query(FWIReconstrucao).filter_by(id_regiao=1, revisao=revisao).one()
            return db.query(FWIHistoricoDia).filter_by(id_reconstrucao=r.id_reconstrucao).order_by(
                FWIHistoricoDia.data_referencia).all()

    def test_sem_estado_e_semente_explicita(self):
        self.assertEqual(self.executar()['estado'], 'sem_estado')
        self.assertEqual(historico.consultar_reconstrucao(self.factory, 1)['estado'], 'sem_estado')
        self.assertEqual(self.iniciar()['estado'], 'inicializado_convencionalmente')
        self.assertEqual(self.executar()['estado'], 'reconstruido')
        with self.factory() as db:
            self.assertEqual(db.query(FWIDiario).count(), 0)

    def test_varios_dias_bissexto_e_idempotencia(self):
        self.iniciar()
        self.assertEqual(self.executar(1)['estado'], 'em_reconstrucao')
        self.assertEqual(self.executar()['calculados'], 2)
        dias = self.dias()
        self.assertEqual([d.data_referencia for d in dias], [date(2024,2,28), date(2024,2,29), date(2024,3,1)])
        for anterior, atual in zip(dias, dias[1:]):
            self.assertEqual(atual.id_anterior, anterior.id_dia)
            for campo in ('ffmc', 'dmc', 'dc'):
                self.assertEqual(atual.estado_anterior[campo], getattr(anterior, campo))
        self.iniciar()
        self.assertEqual(self.executar()['calculados'], 0)
        self.assertEqual([d.assinatura for d in dias], [d.assinatura for d in self.dias()])
        self.assertEqual(len(self.pedidos), 3)

    def test_365_dias_nao_promovem_convencional(self):
        inicio = date(2023, 10, 1)
        semente = EstadoFWI(1, inicio-timedelta(days=1), 85, 6, 15, QualidadeEstado.CONVENCIONAL, 'Teste 365 dias')
        historico.iniciar_reconstrucao(self.factory, id_regiao=1, latitude=38.7, longitude=-9.1,
            territorio=TerritorioFWI.CONTINENTE, data_operacional=inicio+timedelta(days=365),
            estado_inicial=semente, agora=AGORA)
        r = self.executar()
        self.assertEqual(r['calculados'], 365)
        self.assertEqual(r['estado'], 'reconstruido')
        self.assertEqual(len(self.dias()), 365)
        self.assertEqual(self.executar()['calculados'], 0)

    def test_lacuna_intermedia_retoma_e_limite(self):
        self.iniciar()
        self.falha = date(2024, 2, 29)
        r = self.executar()
        self.assertEqual((r['estado'], r['calculados'], r['data_pendente']), ('falha_reconstrucao', 1, '2024-02-29'))
        pedidos = len(self.pedidos)
        self.assertEqual(self.executar()['calculados'], 0)
        self.assertEqual(len(self.pedidos), pedidos)
        self.falha = None
        self.assertEqual(self.executar(1, AGORA+timedelta(minutes=16))['calculados'], 1)
        self.assertEqual(self.executar(1, AGORA+timedelta(minutes=16))['calculados'], 1)
        self.assertEqual(len(self.dias()), 3)

    def test_intervalo_em_falta_bloqueia(self):
        self.iniciar()
        self.lacuna = True
        self.assertEqual(self.executar()['estado'], 'falha_reconstrucao')
        self.assertEqual(len(self.dias()), 0)
        self.lacuna = False
        self.assertEqual(self.executar(agora=AGORA+timedelta(minutes=16))['calculados'], 3)

    def test_correcao_invalida_dependentes_e_recalcula(self):
        self.iniciar()
        self.executar()
        antigos = self.dias()
        self.chuva = 4
        r = asyncio.run(historico.corrigir_dia_historico(self.factory, 1, date(2024,2,29),
            motivo='Revisão simulada da fonte', agora=AGORA, recolher=self.fonte))
        self.assertEqual(r['revisao'], 2)
        self.assertEqual([d.validade for d in self.dias()], ['calculado', 'desatualizado', 'desatualizado'])
        self.assertEqual(self.executar()['calculados'], 3)
        novos = self.dias(2)
        self.assertEqual(antigos[0].fwi, novos[0].fwi)
        self.assertNotEqual(antigos[1].dc, novos[1].dc)
        self.assertNotEqual(antigos[2].dc, novos[2].dc)
        self.assertEqual(novos[2].estado_anterior['dc'], novos[1].dc)
        r = asyncio.run(historico.corrigir_dia_historico(self.factory, 1, date(2024,2,29),
            motivo='Mesmos inputs', agora=AGORA, recolher=self.fonte))
        self.assertEqual(r['revisao'], 2)
        self.assertEqual(self.executar()['calculados'], 0)

    def test_alteracao_persistida_detetada(self):
        self.iniciar()
        self.executar()
        with self.factory.begin() as db:
            h = db.query(FWIHorario).order_by(FWIHorario.instante_utc).first()
            h.precipitacao_hora = 10
        r = self.executar()
        self.assertEqual((r['revisao'], r['calculados']), (2,3))
        self.assertTrue(all(d.validade == 'desatualizado' for d in self.dias()))

    def test_segunda_correcao_invalida_tambem_revisoes_antigas(self):
        self.iniciar()
        self.executar()
        for data, chuva in [(date(2024,3,1), 1), (date(2024,2,28), 2)]:
            self.chuva = chuva
            asyncio.run(historico.corrigir_dia_historico(self.factory, 1, data,
                motivo='Correção sucessiva', agora=AGORA, recolher=self.fonte))
            self.executar()
        self.assertTrue(all(d.validade == 'desatualizado' for d in self.dias(1)+self.dias(2)))
        self.assertTrue(all(d.validade == 'calculado' for d in self.dias(3)))

    def test_correcao_rollback_nao_invalida_cadeia(self):
        self.iniciar()
        self.executar()
        self.chuva = 4
        real = historico.nova_revisao
        def falhar(*args):
            real(*args)
            raise RuntimeError('Falha após atualização dos inputs e invalidação')
        with patch.object(historico, 'nova_revisao', side_effect=falhar):
            with self.assertRaises(RuntimeError):
                asyncio.run(historico.corrigir_dia_historico(self.factory, 1, date(2024,2,29),
                    motivo='Teste de rollback', agora=AGORA, recolher=self.fonte))
        self.assertEqual(historico.consultar_reconstrucao(self.factory, 1)['revisao'], 1)
        self.assertTrue(all(d.validade == 'calculado' for d in self.dias()))
        with self.factory() as db:
            self.assertTrue(all(h.precipitacao_hora == 0 for h in db.query(FWIHorario)))

    def test_correcao_incompleta_nao_substitui_inputs_validos(self):
        self.iniciar()
        self.executar()
        self.lacuna = True
        with self.assertRaises(DadosFWIInvalidos):
            asyncio.run(historico.corrigir_dia_historico(self.factory, 1, date(2024,2,29),
                motivo='Fonte incompleta', agora=AGORA, recolher=self.fonte))
        self.assertEqual(historico.consultar_reconstrucao(self.factory, 1)['revisao'], 1)
        self.assertEqual(self.executar()['calculados'], 0)

    def test_rollback_calculo_e_retoma(self):
        self.iniciar()
        with patch.object(historico, 'calcular_fwi_diario', side_effect=RuntimeError('falha simulada')):
            self.assertEqual(self.executar()['estado'], 'falha_reconstrucao')
        with self.factory() as db:
            self.assertEqual(db.query(FWIHistoricoDia).count(), 0)
            self.assertEqual(db.query(FWIHorario).count(), 0)
        self.assertEqual(self.executar(agora=AGORA+timedelta(minutes=16))['calculados'], 3)

    def test_rollback_commit(self):
        self.iniciar()
        def falhar(session):
            if not session.in_nested_transaction():
                raise RuntimeError('Commit simulado')
        event.listen(self.factory, 'before_commit', falhar)
        try:
            with self.assertRaises(RuntimeError):
                self.executar(1)
        finally:
            event.remove(self.factory, 'before_commit', falhar)
        self.assertEqual(len(self.dias()), 0)
        self.assertEqual(historico.consultar_reconstrucao(self.factory, 1)['data_pendente'], '2024-02-28')
        self.assertEqual(self.executar()['calculados'], 3)

    def test_tres_territorios_transicao_ano(self):
        for territorio, hora in [(TerritorioFWI.CONTINENTE,12), (TerritorioFWI.MADEIRA,12), (TerritorioFWI.ACORES,13)]:
            with self.subTest(territorio=territorio):
                # Uma BD independente por território mantém a identidade da região.
                with self.factory.begin() as db:
                    db.query(FWIHistoricoDia).delete()
                    db.query(FWIReconstrucao).delete()
                    db.query(FWIHorario).delete()
                self.iniciar(date(2023,12,31), 2, territorio)
                self.assertEqual(self.executar()['calculados'], 2)
                for d in self.dias():
                    self.assertEqual(datetime.fromisoformat(d.observacao['instante_referencia_utc']).hour, hora)
                    self.assertEqual(d.observacao['latitude'], self.pedidos[-1][0])
                self.assertEqual(self.dias()[1].data_referencia, date(2024,1,1))

    def test_nao_aceita_estabelecido_inventado(self):
        semente = EstadoFWI(1, date(2024,2,27), 85,6,15, QualidadeEstado.ESTABELECIDO, 'Sem prova')
        with self.assertRaises(DadosFWIInvalidos):
            self.iniciar(semente=semente)

    def test_estabelecido_apenas_com_ancora_persistida(self):
        data = date(2024,2,27)
        obs = ObservacaoDiariaFWI(1,data,instante_referencia(data,TerritorioFWI.CONTINENTE),
            TerritorioFWI.CONTINENTE,20,50,0,0,38.7,'Fixture de estado estabelecido',UNIDADES_FWI)
        anterior = EstadoFWI(1,data-timedelta(days=1),85,6,15,QualidadeEstado.ESTABELECIDO,'Fixture')
        with self.factory.begin() as db:
            row = guardar_resultado_fwi(db, ResultadoFWI(obs,anterior,85,6,15,1,6,1,AGORA))
            semente = restaurar_estado(row)
        self.iniciar(semente=semente)
        self.assertEqual(self.executar()['estado'], 'estabelecido')
        with self.factory() as db:
            self.assertEqual(db.query(FWIDiario).count(), 1)  # Não publica a reconstrução.

    def test_configuracao_diferente_nao_substitui(self):
        self.iniciar()
        with self.assertRaises(DadosFWIInvalidos):
            self.iniciar(dias=4)

    def test_referencia_futura_bloqueia_e_retoma(self):
        self.iniciar(date(2026,10,4), 1)
        antes = AGORA.replace(hour=11)
        r = self.executar(agora=antes)
        self.assertEqual(r['codigo_erro'], 'aguardar_referencia')
        self.assertEqual(len(self.pedidos), 0)
        self.assertEqual(self.executar()['calculados'], 1)

    def test_limite_e_dados_iniciais_invalidos(self):
        for limite in (0, 367, True):
            with self.assertRaises(DadosFWIInvalidos):
                self.executar(limite)
        semente = EstadoFWI(1,date(2024,2,26),85,6,15,QualidadeEstado.CONVENCIONAL,'Teste')
        with self.assertRaises(DadosFWIInvalidos):
            self.iniciar(semente=semente)

    def test_concorrencia_postgresql(self):
        if self.engine.dialect.name != 'postgresql':
            self.skipTest('Requer PostgreSQL descartável.')
        self.iniciar()
        entrou, libertar = threading.Event(), threading.Event()
        async def lenta(*args, **kwargs):
            entrou.set()
            await asyncio.to_thread(libertar.wait, 20)
            return await self.fonte(*args, **kwargs)
        resultados = []
        erros = []
        def executar():
            try:
                resultados.append(asyncio.run(historico.reconstruir(self.factory, 1,
                    limite_dias=1, agora=AGORA, recolher=lenta)))
            except Exception as erro:
                erros.append(erro)
        thread = threading.Thread(target=executar)
        thread.start()
        try:
            self.assertTrue(entrou.wait(20))
            self.assertEqual(self.executar()['estado'], 'ocupada')
            self.assertEqual(self.iniciar()['estado'], 'ocupada')
        finally:
            libertar.set()
            thread.join(30)
        self.assertFalse(erros)
        self.assertFalse(thread.is_alive())
        self.assertEqual(resultados[0]['calculados'], 1)
        self.assertEqual(len(self.dias()), 1)


if __name__ == '__main__':
    unittest.main()
