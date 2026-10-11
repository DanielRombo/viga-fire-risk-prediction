"""Continuidade técnica, sem promoção científica nem acesso à produção."""
import asyncio
import threading
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch
from sqlalchemy import event
import test_fwi_fase3 as fixture
from models.fwi_diario import FWIDiario
from models.fwi_reconstrucao import FWIReconstrucao, FWIHistoricoDia
from services import reconstrucao_fwi as historico
from services.processamento_fwi import executar_ciclo_fwi
from services.leitura_fwi import representar
from services.meteorologia_fwi import TerritorioFWI, DadosFWIInvalidos


class ContinuidadeTests(unittest.TestCase):
    setUp = fixture.ReconstrucaoTests.setUp
    limpar = fixture.ReconstrucaoTests.limpar
    iniciar = fixture.ReconstrucaoTests.iniciar
    executar = fixture.ReconstrucaoTests.executar
    dias = fixture.ReconstrucaoTests.dias

    def preparar(self):
        self.iniciar(date(2024, 2, 28), 2)
        self.assertEqual(self.executar()['estado'], 'reconstruido')

    def continuar(self, agora=None, limite=3, fonte=None):
        return asyncio.run(historico.reconstruir(self.factory, 1, continuar=True,
            limite_dias=limite, agora=agora or datetime(2024,3,3,14,tzinfo=timezone.utc),
            recolher=fonte or self.fonte))

    def confirmar_tecnica(self):
        with self.factory() as db:
            r = historico.atual(db, 1)
            self.assertEqual(r.estado, 'reconstruido')
            ultimo = db.query(FWIHistoricoDia).filter_by(id_reconstrucao=r.id_reconstrucao).order_by(
                FWIHistoricoDia.data_referencia.desc()).first()
            resposta = representar(1, ultimo, TerritorioFWI.CONTINENTE, 'reconstrucao',
                r, True, r, datetime.now(timezone.utc)+timedelta(minutes=1))
            self.assertEqual(resposta['estado_inicializacao'], 'reconstruido')
            self.assertFalse(resposta['operacional'])
            self.assertFalse(resposta['estabelecido'])
            self.assertEqual(db.query(FWIDiario).count(), 0)

    def test_dia_seguinte_usa_estado_e_nao_promove(self):
        self.preparar()
        antes = self.dias()[-1]
        self.assertEqual(self.continuar(limite=1)['calculados'], 1)
        novo = self.dias()[-1]
        self.assertEqual(novo.data_referencia, date(2024,3,1))
        self.assertEqual(novo.id_anterior, antes.id_dia)
        for campo in ('ffmc','dmc','dc'):
            self.assertEqual(novo.estado_anterior[campo],getattr(antes,campo))
        self.confirmar_tecnica()

    def test_varios_dias_limite_idempotencia_e_referencia(self):
        self.preparar()
        self.assertEqual(self.continuar()['calculados'],3)
        dias = self.dias()
        for a,b in zip(dias,dias[1:]):
            self.assertEqual(b.data_referencia,a.data_referencia+timedelta(days=1))
            self.assertEqual(b.id_anterior,a.id_dia)
            for campo in ('ffmc','dmc','dc'):
                self.assertEqual(b.estado_anterior[campo],getattr(a,campo))
        self.assertEqual(self.continuar()['calculados'],0)
        self.assertEqual([d.assinatura for d in dias],[d.assinatura for d in self.dias()])
        with self.assertRaises(DadosFWIInvalidos):
            self.continuar(limite=4)
        self.confirmar_tecnica()

    def test_sem_estado_nao_inicia(self):
        self.assertEqual(self.continuar()['estado'],'sem_estado')
        self.iniciar(date(2024,2,28),2)
        self.assertEqual(self.continuar()['calculados'],0)
        self.assertEqual(len(self.dias()),0)

    def test_anterior_ausente_bloqueia_sem_inventar(self):
        self.preparar()
        with self.factory.begin() as db:
            db.query(FWIHistoricoDia).filter_by(data_referencia=date(2024,2,29)).delete()
        r=self.continuar()
        self.assertEqual(r['calculados'],0)
        self.assertEqual(r['estado'],'falha_reconstrucao')
        self.assertEqual(r['codigo_erro'],'dados_invalidos')
        self.assertEqual(r['data_pendente'],'2024-03-01')

    def test_erro_calculo_rollback_e_retry(self):
        self.preparar()
        antes=[d.assinatura for d in self.dias()]
        with patch.object(historico,'calcular_fwi_diario',side_effect=RuntimeError('Falha simulada')):
            self.assertEqual(self.continuar()['estado'],'falha_reconstrucao')
        self.assertEqual([d.assinatura for d in self.dias()],antes)
        self.assertEqual(self.continuar()['calculados'],0)
        self.assertEqual(self.continuar(datetime(2024,3,3,15,tzinfo=timezone.utc))['calculados'],3)
        self.confirmar_tecnica()

    def test_commit_falha_nao_confirma_avanco(self):
        self.preparar()
        def falhar(sessao):
            if not sessao.in_nested_transaction():
                raise RuntimeError('Commit simulado')
        event.listen(self.factory,'before_commit',falhar)
        try:
            with self.assertRaises(RuntimeError):
                self.continuar()
        finally:
            event.remove(self.factory,'before_commit',falhar)
        self.assertEqual(len(self.dias()),2)
        self.assertEqual(historico.consultar_reconstrucao(self.factory,1)['data_pendente'],'2024-03-01')

    def test_scheduler_encaminha_para_serie_tecnica(self):
        self.preparar()
        original=historico.reconstruir
        async def ensaio(*args,**kwargs):
            return await original(*args,**kwargs,recolher=self.fonte)
        regiao=dict(id_regiao=1,distrito='Lisboa',latitude=38.7,longitude=-9.1)
        with patch.object(historico,'reconstruir',side_effect=ensaio):
            saida=asyncio.run(executar_ciclo_fwi(self.factory,regioes=[regiao],
                agora=datetime(2024,3,3,14,tzinfo=timezone.utc)))
        self.assertEqual(saida[0]['calculados'],3)
        self.confirmar_tecnica()

    def test_concorrencia_postgresql(self):
        if self.engine.dialect.name!='postgresql':
            self.skipTest('Requer PostgreSQL descartável.')
        self.preparar()
        entrou,libertar=threading.Event(),threading.Event()
        async def lenta(*args,**kwargs):
            entrou.set()
            await asyncio.to_thread(libertar.wait,20)
            return await self.fonte(*args,**kwargs)
        erros=[]
        def executar():
            try:
                self.continuar(limite=1,fonte=lenta)
            except Exception as erro:
                erros.append(erro)
        thread=threading.Thread(target=executar)
        thread.start()
        try:
            self.assertTrue(entrou.wait(20))
            self.assertEqual(self.continuar()['estado'],'ocupada')
        finally:
            libertar.set()
            thread.join(30)
        self.assertFalse(thread.is_alive())
        self.assertFalse(erros)
        self.assertEqual(len(self.dias()),3)
        self.confirmar_tecnica()
