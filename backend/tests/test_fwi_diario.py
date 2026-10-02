"""FWI diário: referência independente, inputs, calendário e persistência real."""
import csv
import math
import os
import sys
import unittest
from dataclasses import replace
from datetime import date, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from unittest.mock import patch
import numpy as np
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg2://test@127.0.0.1:1/viga_test')
from services.fwi_diario import EstadoFWI, QualidadeEstado, calcular_fwi_diario, VERSAO_FWI
from services.meteorologia_fwi import (ObservacaoDiariaFWI, AmostraHorariaFWI, TerritorioFWI,
    UNIDADES_FWI, DadosFWIInvalidos, instante_referencia, preparar_observacao_diaria)
from services.persistencia_fwi import preparar_tabela_fwi, guardar_resultado_fwi, restaurar_estado
from models.fwi_diario import FWIDiario

NOMES = ('ffmc', 'dmc', 'dc', 'isi', 'bui', 'fwi')
ATOL, RTOL = 1e-8, 1e-10  # As mesmas tolerâncias da prova; não ajustar.
with (Path(__file__).parent / 'fixtures/cffdrs_1_8_17.csv').open() as f:
    REFERENCIA = list(csv.DictReader(f))


def observacao(linha=0, territorio=TerritorioFWI.CONTINENTE, latitude=40.):
    r = REFERENCIA[linha]
    data = date(int(r['YR']), int(r['MON']), int(r['DAY']))
    return ObservacaoDiariaFWI(1, data, instante_referencia(data, territorio), territorio,
        float(r['TEMP']), float(r['RH']), float(r['WS']), float(r['PREC']), latitude,
        'Caso de referência cffdrs 1.8.17', UNIDADES_FWI)


def inicial(qualidade=QualidadeEstado.CONVENCIONAL):
    return EstadoFWI(1, date(1985,4,12), 85, 6, 15, qualidade, 'Condições iniciais do caso publicado')


class CalculoDiarioTests(unittest.TestCase):
    def test_48_dias_seis_indices_referencia(self):
        anterior = inicial()
        for i, linha in enumerate(REFERENCIA):
            with self.subTest(dia=i):
                resultado = calcular_fwi_diario(observacao(i), anterior)
                np.testing.assert_allclose([getattr(resultado,k) for k in NOMES],
                                          [float(linha[k.upper()]) for k in NOMES], atol=ATOL,rtol=RTOL)
                anterior = resultado.proximo_estado()
                self.assertEqual(resultado.estado, 'em_inicializacao')

    def test_tres_territorios(self):
        for territorio, latitude in [(TerritorioFWI.CONTINENTE,38.7223),
                                     (TerritorioFWI.MADEIRA,32.6669),(TerritorioFWI.ACORES,37.7412)]:
            with self.subTest(territorio=territorio):
                r = calcular_fwi_diario(observacao(territorio=territorio,latitude=latitude), inicial())
                np.testing.assert_allclose([getattr(r,k) for k in NOMES],
                    [float(REFERENCIA[0][k.upper()]) for k in NOMES],atol=ATOL,rtol=RTOL)

    def test_zero_chuva_forte_e_limites_humidade(self):
        for chuva, vento, humidade in [(0,0,0),(0,0,100),(100,0,100),(100,30,0)]:
            with self.subTest(chuva=chuva,vento=vento,humidade=humidade):
                r = calcular_fwi_diario(replace(observacao(),precipitacao_24h=chuva,vento=vento,humidade=humidade), inicial())
                self.assertTrue(all(math.isfinite(getattr(r,k)) for k in NOMES))
                self.assertEqual(r.observacao.vento,vento)
                self.assertEqual(r.observacao.precipitacao_24h,chuva)
        seco = calcular_fwi_diario(observacao(),inicial())
        molhado = calcular_fwi_diario(replace(observacao(),precipitacao_24h=100),inicial())
        self.assertLess(molhado.ffmc,seco.ffmc)
        self.assertLess(molhado.dmc,seco.dmc)
        self.assertLess(molhado.dc,seco.dc)

    def test_inputs_ausentes_nao_finitos_unidades_e_limites(self):
        for campo in ('temperatura','humidade','vento','precipitacao_24h','latitude'):
            for valor in (None, math.nan, math.inf, -math.inf, True, '0'):
                with self.subTest(campo=campo,valor=valor), self.assertRaises(DadosFWIInvalidos):
                    replace(observacao(),**{campo:valor})
        for campo,valor in [('humidade',101),('humidade',-1),('vento',-1),('precipitacao_24h',-1),('latitude',91),('temperatura',-274)]:
            with self.assertRaises(DadosFWIInvalidos):
                replace(observacao(),**{campo:valor})
        with self.assertRaises(DadosFWIInvalidos):
            replace(observacao(),unidades=replace(UNIDADES_FWI,vento='m/s'))
        with self.assertRaises(DadosFWIInvalidos):
            replace(observacao(),unidades=replace(UNIDADES_FWI,altura_vento_m=2))
        with self.assertRaises(DadosFWIInvalidos):
            replace(observacao(),instante_referencia_utc=observacao().instante_referencia_utc.replace(tzinfo=None))

    def test_estado_obrigatorio_contiguo_mesma_regiao_e_versao(self):
        for estado in (None, replace(inicial(),id_regiao=2), replace(inicial(),data_referencia=date(1985,4,11))):
            with self.assertRaises(DadosFWIInvalidos):
                calcular_fwi_diario(observacao(),estado)
        for kwargs in ({'ffmc':None},{'dc':math.nan},{'ffmc':102},{'dmc':-1},{'versao':'outra'}):
            with self.assertRaises(DadosFWIInvalidos):
                replace(inicial(),**kwargs)

    def test_qualidade_nao_promovida_automaticamente(self):
        for qualidade in QualidadeEstado:
            r = calcular_fwi_diario(observacao(),inicial(qualidade))
            self.assertEqual(r.estado,'valido' if qualidade == QualidadeEstado.ESTABELECIDO else 'em_inicializacao')
            r2 = calcular_fwi_diario(observacao(1),r.proximo_estado())
            self.assertEqual(r2.estado,r.estado)
            self.assertEqual(r2.anterior.qualidade,qualidade)

    def test_versao_instalada_incorreta_e_output_nao_finito(self):
        import xclim
        from types import SimpleNamespace
        with patch.object(xclim,'__version__','outra'), self.assertRaises(RuntimeError):
            calcular_fwi_diario(observacao(),inicial())
        saida = SimpleNamespace(**{k.upper():np.array([math.nan]) for k in NOMES})
        with patch('xclim.indices.fire.cffwis_indices',return_value=saida), self.assertRaises(DadosFWIInvalidos):
            calcular_fwi_diario(observacao(),inicial())


class PreparacaoDiariaTests(unittest.TestCase):
    def preparar(self,data,territorio,amostras=None):
        t = instante_referencia(data,territorio)
        if amostras is None:
            amostras = [AmostraHorariaFWI(t-timedelta(hours=i),1,20,50,0) for i in range(24)]
        return preparar_observacao_diaria(id_regiao=1,data_referencia=data,territorio=territorio,
            latitude=37,amostras=amostras,unidades=UNIDADES_FWI,origem='Fonte horária simulada')

    def test_hora_padrao_ano_bissexto_mudancas_hora(self):
        for territorio,zona,hora in [(TerritorioFWI.CONTINENTE,'Europe/Lisbon',12),
                                    (TerritorioFWI.MADEIRA,'Atlantic/Madeira',12),
                                    (TerritorioFWI.ACORES,'Atlantic/Azores',13)]:
            for data in (date(2024,2,29),date(2024,3,30),date(2024,3,31),date(2024,10,26),date(2024,10,27)):
                with self.subTest(territorio=territorio,data=data):
                    obs = self.preparar(data,territorio)
                    self.assertEqual(obs.instante_referencia_utc.hour,hora)
                    self.assertEqual(obs.precipitacao_24h,24)
                    civil = obs.instante_referencia_utc.astimezone(ZoneInfo(zona))
                    self.assertEqual(civil.hour,13 if civil.dst() else 12)
                    r = calcular_fwi_diario(obs,replace(inicial(),data_referencia=data-timedelta(days=1)))
                    self.assertTrue(math.isfinite(r.fwi))

    def test_precipitacao_zero_janela_e_observacao_exata(self):
        data = date(2024,3,31)
        t = instante_referencia(data,TerritorioFWI.CONTINENTE)
        amostras = [AmostraHorariaFWI(t-timedelta(hours=i),0,1,1,1) for i in range(25)]
        amostras[0] = AmostraHorariaFWI(t,0,0,0,0)
        amostras[-1] = AmostraHorariaFWI(t-timedelta(hours=24),99,99,99,99)
        obs = self.preparar(data,TerritorioFWI.CONTINENTE,amostras)
        self.assertEqual((obs.temperatura,obs.humidade,obs.vento,obs.precipitacao_24h),(0,0,0,0))
        for incompletas in (amostras[1:],amostras+[amostras[0]],
                            [replace(amostras[0],precipitacao_hora=None)]+amostras[1:]):
            with self.assertRaises(DadosFWIInvalidos):
                self.preparar(data,TerritorioFWI.CONTINENTE,incompletas)


class PersistenciaDiariaTests(unittest.TestCase):
    def setUp(self):
        url = os.getenv('VIGA_FWI_TEST_DATABASE_URL','sqlite://')
        self.engine = create_engine(url)
        self.addCleanup(self.engine.dispose)
        if self.engine.dialect.name == 'sqlite':
            @event.listens_for(self.engine,'connect')
            def configurar(conn,_):
                conn.isolation_level = None
                conn.execute('PRAGMA foreign_keys=ON')
            @event.listens_for(self.engine,'begin')
            def iniciar(conn):
                conn.exec_driver_sql('BEGIN')
        else:
            self.assertTrue(self.engine.url.database.startswith('viga_fwi_test_'))
        with self.engine.begin() as conn:
            conn.execute(text('CREATE TABLE regioes (id_regiao INTEGER PRIMARY KEY)'))
            conn.execute(text('INSERT INTO regioes VALUES (1)'))
        preparar_tabela_fwi(self.engine)
        self.addCleanup(self.limpar)
        self.db = Session(self.engine)
        self.addCleanup(self.db.close)

    def limpar(self):
        FWIDiario.__table__.drop(self.engine)
        with self.engine.begin() as conn:
            conn.execute(text('DROP TABLE regioes'))

    def test_idempotencia_commit_e_conflito_preserva_original(self):
        preparar_tabela_fwi(self.engine)
        r = calcular_fwi_diario(observacao(),inicial())
        primeiro = guardar_resultado_fwi(self.db,r)
        self.db.commit()
        self.assertEqual(guardar_resultado_fwi(self.db,r).id_fwi,primeiro.id_fwi)
        self.db.commit()
        self.assertEqual(self.db.query(FWIDiario).count(),1)
        outro = calcular_fwi_diario(replace(observacao(),vento=30),inicial())
        with self.assertRaises(DadosFWIInvalidos):
            guardar_resultado_fwi(self.db,outro)
        self.db.rollback()
        self.assertEqual(self.db.get(FWIDiario,primeiro.id_fwi).vento,25)

    def test_guardar_restaurar_continuidade_e_linhagem(self):
        r = calcular_fwi_diario(observacao(),inicial())
        primeiro = guardar_resultado_fwi(self.db,r)
        self.db.commit()
        id_primeiro = primeiro.id_fwi
        self.db.close()
        with Session(self.engine) as nova:
            estado = restaurar_estado(nova.get(FWIDiario,id_primeiro))
            seguinte = calcular_fwi_diario(observacao(1),estado)
            continuo = calcular_fwi_diario(observacao(1),r.proximo_estado())
            self.assertEqual([getattr(seguinte,k) for k in NOMES],[getattr(continuo,k) for k in NOMES])
            segundo = guardar_resultado_fwi(nova,seguinte)
            nova.commit()
            self.assertEqual(segundo.id_anterior,id_primeiro)
            self.assertEqual(segundo.estado_anterior['ffmc'],r.ffmc)
            self.assertEqual(segundo.estado,'em_inicializacao')

    def test_rollback_e_referencia_inconsistente(self):
        primeiro = guardar_resultado_fwi(self.db,calcular_fwi_diario(observacao(),inicial()))
        self.db.commit()
        anterior = restaurar_estado(primeiro)
        with self.assertRaises(DadosFWIInvalidos):
            guardar_resultado_fwi(self.db,calcular_fwi_diario(observacao(1),replace(anterior,ffmc=50)))
        self.db.rollback()
        guardar_resultado_fwi(self.db,calcular_fwi_diario(observacao(1),anterior))
        self.db.rollback()
        self.assertEqual(self.db.query(FWIDiario).count(),1)

    def test_idempotencia_concorrente_postgresql(self):
        if self.engine.dialect.name != 'postgresql':
            self.skipTest('Concorrência validada no PostgreSQL descartável.')
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        barreira = Barrier(2)
        resultado = calcular_fwi_diario(observacao(),inicial())
        def gravar():
            with Session(self.engine) as db:
                barreira.wait(timeout=10)
                r = guardar_resultado_fwi(db,resultado)
                id_fwi = r.id_fwi
                db.commit()
                return id_fwi
        with ThreadPoolExecutor(max_workers=2) as executor:
            tarefas = [executor.submit(gravar) for _ in range(2)]
            ids = [t.result(timeout=20) for t in tarefas]
        self.assertEqual(ids[0],ids[1])
        self.assertEqual(self.db.query(FWIDiario).count(),1)


if __name__ == '__main__':
    unittest.main()
