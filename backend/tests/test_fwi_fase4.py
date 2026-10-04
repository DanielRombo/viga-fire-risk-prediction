"""Contrato HTTP do FWI diário; sem repetir cálculos científicos."""
import os
import sys
import unittest
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg2://test@127.0.0.1:1/viga_test')
from config.database import get_db
from models.fwi_diario import FWIDiario
from models.fwi_processamento import FWIHorario, FWIProcessamento
from models.fwi_reconstrucao import FWIReconstrucao, FWIHistoricoDia
from routes.fwi_diario import router
from services.leitura_fwi import representar
from services.reconstrucao_fwi import preparar_estrutura_historica, serializar
from services.meteorologia_fwi import TerritorioFWI, UNIDADES_FWI, instante_referencia, ObservacaoDiariaFWI
from services.fwi_diario import EstadoFWI, QualidadeEstado, ResultadoFWI, VERSAO_FWI
from services.persistencia_fwi import guardar_resultado_fwi

AGORA = datetime(2026,10,4,15,tzinfo=timezone.utc)
HOJE = AGORA.date()


class LeituraAPITests(unittest.TestCase):
    def setUp(self):
        url = os.getenv('VIGA_FWI_TEST_DATABASE_URL', 'sqlite://')
        self.engine = create_engine(url, **({'poolclass': StaticPool, 'connect_args': {'check_same_thread':False}} if url == 'sqlite://' else {}))
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
            conn.execute(text('CREATE TABLE regioes (id_regiao INTEGER PRIMARY KEY, distrito VARCHAR NOT NULL)'))
            conn.execute(text("INSERT INTO regioes VALUES (1,'Lisboa'),(2,'Madeira'),(3,'Açores'),(4,'Desconhecido')"))
        preparar_estrutura_historica(self.engine)
        self.addCleanup(self.limpar)
        self.factory = sessionmaker(self.engine, autoflush=False)
        app = FastAPI()
        app.include_router(router, prefix='/api')
        def sessao():
            with self.factory() as db:
                yield db
        app.dependency_overrides[get_db] = sessao
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.relogio = patch('services.leitura_fwi.agora_utc', return_value=AGORA)
        self.relogio.start()
        self.addCleanup(self.relogio.stop)

    def limpar(self):
        for m in (FWIHistoricoDia, FWIReconstrucao, FWIProcessamento, FWIHorario, FWIDiario):
            m.__table__.drop(self.engine)
        with self.engine.begin() as conn:
            conn.execute(text('DROP TABLE regioes'))

    def operacional(self, data=HOJE, regiao=1, qualidade=QualidadeEstado.ESTABELECIDO, valor=0):
        territorio = {1:TerritorioFWI.CONTINENTE, 2:TerritorioFWI.MADEIRA, 3:TerritorioFWI.ACORES, 4:TerritorioFWI.CONTINENTE}[regiao]
        obs = ObservacaoDiariaFWI(regiao,data,instante_referencia(data,territorio),territorio,
            20,50,0,0,38.7,'open-meteo-forecast-best-match-horario-v1',UNIDADES_FWI)
        anterior = EstadoFWI(regiao,data-timedelta(days=1),85,6,15,qualidade,'Fixture de leitura')
        resultado = ResultadoFWI(obs,anterior,*([valor]*6),calculado_em=AGORA-timedelta(minutes=1))
        with self.factory.begin() as db:
            guardar_resultado_fwi(db,resultado)

    def reconstrucao(self, estado='reconstruido', revisao=1, data=HOJE, com_dia=True,
                     substituida=0, validade='calculado', regiao=1):
        qualidade = 'estabelecido' if estado == 'estabelecido' else 'inicializacao_convencional'
        with self.factory.begin() as db:
            r = FWIReconstrucao(id_regiao=regiao,versao=VERSAO_FWI,revisao=revisao,estado=estado,
                data_inicial=data,data_operacional=data+timedelta(days=1),data_pendente=data+timedelta(days=1) if com_dia else data,
                configuracao={'semente':{'qualidade':qualidade}},assinatura_configuracao='a'*64,
                criado_em=AGORA,substituida=substituida)
            db.add(r)
            db.flush()
            if com_dia:
                territorio = {1:TerritorioFWI.CONTINENTE,2:TerritorioFWI.MADEIRA,3:TerritorioFWI.ACORES}[regiao]
                obs = ObservacaoDiariaFWI(regiao,data,instante_referencia(data,territorio),territorio,
                    20,50,0,0,38.7,'open-meteo-archive-ecmwf-ifs-horario-v1',UNIDADES_FWI)
                db.add(FWIHistoricoDia(id_reconstrucao=r.id_reconstrucao,data_referencia=data,
                    observacao=serializar(asdict(obs)),horas=[],estado_anterior={},assinatura='b'*64,
                    ffmc=0,dmc=0,dc=0,isi=0,bui=0,fwi=0,validade=validade,calculado_em=AGORA-timedelta(minutes=1)))

    def get(self, suffix='1', **params):
        response = self.client.get('/api/fwi-diario/'+suffix, params=params)
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    def test_ok_contrato_zero_e_proveniencia(self):
        self.operacional()
        r = self.get()
        self.assertEqual(r['estado'],'ok')
        self.assertTrue(r['operacional'])
        self.assertEqual([r[k] for k in ('ffmc','dmc','dc','isi','bui','fwi')],[0]*6)
        self.assertEqual(r['data_referencia'],str(HOJE))
        self.assertEqual(r['calculado_em'],(AGORA-timedelta(minutes=1)).isoformat().replace('+00:00','Z'))
        self.assertEqual(r['versao_xclim'],'0.62.0')
        self.assertEqual(r['variante'],'classica_cffdrs_1.8.17')
        self.assertEqual(r['proveniencia']['id_registo'],1)

    def test_inexistente_null_e_regiao_404(self):
        r = self.get()
        self.assertEqual(r['estado'],'indisponivel')
        for campo in ('data_referencia','instante_referencia_utc','calculado_em','ffmc','dmc','dc','isi','bui','fwi','origem'):
            self.assertIsNone(r[campo])
        self.assertFalse(r['operacional'])
        self.assertEqual(self.client.get('/api/fwi-diario/999').status_code,404)

    def test_desatualizado_nao_depende_do_calculo_recente(self):
        self.operacional(HOJE-timedelta(days=2))
        self.assertEqual(self.get()['estado'],'desatualizado')
        self.assertFalse(self.get()['operacional'])

    def test_inicializacao_operacional(self):
        self.operacional(qualidade=QualidadeEstado.CONVENCIONAL)
        r = self.get()
        self.assertEqual(r['estado'],'em_inicializacao')
        self.assertEqual(r['estado_inicializacao'],'inicializado_convencionalmente')
        self.assertFalse(r['estabelecido'])

    def test_estados_da_reconstrucao(self):
        for revisao, (interno, externo) in enumerate([
            ('inicializado_convencionalmente','em_inicializacao'),
            ('em_reconstrucao','em_reconstrucao'),('reconstruido','em_inicializacao'),
            ('falha_reconstrucao','em_reconstrucao'),('estabelecido','ok')],1):
            self.reconstrucao(estado=interno,revisao=revisao)
            r = self.get()
            self.assertEqual(r['estado'],externo)
            self.assertEqual(r['estado_inicializacao'],interno)
            self.assertEqual(r['operacional'],interno=='estabelecido')

    def test_revisao_ativa_sem_dia_nao_reutiliza_antiga(self):
        self.reconstrucao(estado='estabelecido',substituida=1)
        self.reconstrucao(estado='em_reconstrucao',revisao=2,com_dia=False)
        r = self.get()
        self.assertEqual(r['revisao'],2)
        self.assertIsNone(r['fwi'])
        self.assertEqual(r['estado'],'em_reconstrucao')
        self.assertEqual(self.get('1/historico')['resultados'],[])
        antigo = self.get(revisao=1)
        self.assertFalse(antigo['operacional'])
        self.assertEqual(antigo['estado'],'desatualizado')

    def test_historico_ordenado_sem_duplicados_paginacao(self):
        for delta in (0,2,1):
            self.operacional(HOJE-timedelta(days=delta))
        r = self.get('1/historico',limite=2)
        self.assertTrue(r['tem_mais'])
        datas = [linha['data_referencia'] for linha in r['resultados']]
        self.assertEqual(datas,sorted(set(datas)))
        pagina = self.get('1/historico',limite=2,offset=2)
        self.assertEqual(len(pagina['resultados']),1)
        self.assertNotIn(pagina['resultados'][0]['data_referencia'],datas)
        self.assertEqual(len(self.get('1/historico',inicio=str(HOJE),fim=str(HOJE))['resultados']),1)

    def test_series_nao_sao_misturadas(self):
        self.operacional()
        self.reconstrucao()
        self.assertEqual(self.get()['serie'],'operacional')
        self.assertEqual(len(self.get('1/historico')['resultados']),1)
        self.assertEqual(self.get(serie='reconstrucao')['estado'],'em_inicializacao')
        self.assertEqual(self.client.get('/api/fwi-diario/1',params={'serie':'operacional','revisao':1}).status_code,422)

    def test_regioes_e_horarios_continente_madeira_acores(self):
        for regiao in (1,2,3):
            self.operacional(HOJE-timedelta(days=1),regiao=regiao,valor=regiao)
        with self.factory.begin() as db:
            for linha in db.query(FWIDiario):
                linha.calculado_em = AGORA-timedelta(days=1)
        with patch('services.leitura_fwi.agora_utc',return_value=AGORA.replace(hour=13,minute=0)):
            self.assertEqual(self.get('1')['estado'],'desatualizado')
            self.assertEqual(self.get('2')['estado'],'desatualizado')
            self.assertEqual(self.get('3')['estado'],'ok')
            self.assertEqual(self.get('3')['fwi'],3)
        with patch('services.leitura_fwi.agora_utc',return_value=AGORA.replace(hour=14,minute=0)):
            self.assertEqual(self.get('3')['estado'],'desatualizado')

    def test_tolerancia_e_hora_de_verao(self):
        # Timestamp de cálculo é antigo, mas a referência anterior ainda está dentro do prazo.
        self.operacional(HOJE-timedelta(days=1))
        with self.factory.begin() as db:
            db.query(FWIDiario).one().calculado_em = AGORA-timedelta(days=1)
        with patch('services.leitura_fwi.agora_utc',return_value=AGORA.replace(hour=12,minute=59)):
            r = self.get()
            self.assertEqual(r['estado'],'ok')
            self.assertEqual(r['atraso_permitido_minutos'],60)
            self.assertEqual(r['prazo_calculo_utc'],AGORA.replace(hour=13,minute=0).isoformat().replace('+00:00','Z'))

    def test_falhas_processamento_sem_zero(self):
        with self.factory.begin() as db:
            db.add(FWIProcessamento(id_regiao=1,versao=VERSAO_FWI,estado='aguardar_dados',data_pendente=HOJE))
        for codigo, esperado in [('timeout','erro_fonte'),('erro_fonte','erro_fonte'),
                                  ('sem_dados','dados_incompletos'),('dados_incompletos','dados_incompletos'),
                                  ('sem_estado_estabelecido','estado_anterior_ausente')]:
            with self.factory.begin() as db:
                db.query(FWIProcessamento).one().codigo_erro = codigo
            r = self.get()
            self.assertEqual(r['estado'],esperado)
            self.assertIsNone(r['fwi'])

    def test_null_nan_nao_sao_zero_nem_ok(self):
        self.reconstrucao(estado='estabelecido')
        with self.factory() as db:
            r = db.query(FWIReconstrucao).one()
            linha = db.query(FWIHistoricoDia).one()
            for v in (None,float('nan'),float('inf'),-1):
                linha.fwi = v  # Só objeto de leitura; a BD não aceita estes valores.
                resposta = representar(1,linha,TerritorioFWI.CONTINENTE,'reconstrucao',r,True,None,AGORA)
                self.assertEqual(resposta['estado'],'dados_incompletos')
                self.assertIsNone(resposta['fwi'])
                self.assertFalse(resposta['operacional'])

    def test_timestamp_ausente_e_futuro(self):
        self.reconstrucao(estado='estabelecido')
        for valor in (None,'inválido',(AGORA+timedelta(days=1)).isoformat()):
            with self.factory.begin() as db:
                row = db.query(FWIHistoricoDia).one()
                row.observacao = {**row.observacao,'instante_referencia_utc':valor}
            self.assertEqual(self.get()['estado'],'dados_incompletos')

    def test_revisao_desatualizada_e_regiao_isolada(self):
        self.reconstrucao(estado='estabelecido',validade='desatualizado')
        self.assertEqual(self.get()['estado'],'desatualizado')
        self.assertEqual(self.get('2')['estado'],'indisponivel')
        self.assertEqual(self.client.get('/api/fwi-diario/2',params={'revisao':1}).status_code,404)

    def test_validacao_parametros_e_erro_bd(self):
        for params in ({'limite':367},{'limite':0},{'offset':-1},{'revisao':0},{'serie':'inexistente'},
                       {'inicio':'2026-10-05','fim':'2026-10-01'}):
            self.assertEqual(self.client.get('/api/fwi-diario/1/historico',params=params).status_code,422)
        with patch('routes.fwi_diario.ler_fwi',side_effect=SQLAlchemyError('segredo técnico')):
            r = self.client.get('/api/fwi-diario/1')
        self.assertEqual(r.status_code,503)
        self.assertNotIn('segredo',r.text)

    def test_territorio_desconhecido_nao_declara_ok(self):
        self.operacional(regiao=4)
        self.assertEqual(self.get('4')['estado'],'dados_incompletos')

    def test_get_apenas_le_sem_mutacoes(self):
        self.operacional()
        comandos = []
        def registar(conn, cursor, statement, parameters, context, executemany):
            comandos.append(statement.strip().split()[0].upper())
        event.listen(self.engine, 'before_cursor_execute', registar)
        try:
            self.get()
            self.get('1/historico')
        finally:
            event.remove(self.engine, 'before_cursor_execute', registar)
        self.assertFalse(set(comandos) & {'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP'})

    def test_resultado_do_dia_antes_do_prazo_e_aceite(self):
        self.operacional()
        with self.factory.begin() as db:
            db.query(FWIDiario).one().calculado_em = AGORA.replace(hour=12,minute=10)
        with patch('services.leitura_fwi.agora_utc',return_value=AGORA.replace(hour=12,minute=15)):
            r = self.get()
            self.assertEqual(r['estado'],'ok')
            self.assertEqual(r['data_referencia_esperada'],str(HOJE-timedelta(days=1)))

    def test_historico_revisoes_sao_selecoes_distintas(self):
        self.reconstrucao(substituida=1)
        self.reconstrucao(revisao=2)
        ativo = self.get('1/historico')
        arquivo = self.get('1/historico',revisao=1)
        self.assertEqual(len(ativo['resultados']),1)
        self.assertEqual(len(arquivo['resultados']),1)
        self.assertEqual(ativo['revisao'],2)
        self.assertEqual(arquivo['revisao'],1)
        self.assertFalse(arquivo['resultados'][0]['operacional'])


if __name__ == '__main__':
    unittest.main()
