import csv
import json
import unittest
from datetime import datetime,timedelta,timezone
from reconciliar_5b2b import classificar
from labels_5b2b import decidir,contar,variantes
from obter_5b2b import ROOT,sha

class CoberturaTests(unittest.TestCase):
    def test_contraprova_e_taxonomia_final(self):
        r=json.loads((ROOT/'revisao_resumo.json').read_text(encoding='utf-8'))
        self.assertEqual((r['positivos'],r['negativos']),(10,20))
        a=json.loads((ROOT/'auditoria.json').read_text(encoding='utf-8'))
        self.assertEqual(a['exclusoes']['reacendimento'],30415)
        self.assertEqual(a['ids_partilhados_eliminados'],0)

    def test_piloto_corresponde_labels_finais(self):
        with (ROOT/'labels.csv').open(encoding='utf-8') as f:
            labels={(r['municipio'],r['data_T']):r['target_24h'] for r in csv.DictReader(f)}
        with (ROOT/'dataset_piloto.csv').open(encoding='utf-8') as f:
            for r in csv.DictReader(f):
                self.assertEqual(r['target_24h'],labels[r['municipio'],r['data_T']])

    def test_ausencia_nao_cria_cobertura(self):
        self.assertEqual(classificar(0,None,''),'sem evidencia')
        self.assertEqual(classificar(10,10,''),'aceitavel')
        self.assertEqual(classificar(10,10,'&'),'duvidosa')
        self.assertEqual(classificar(0,0,'',True),'duvidosa')
        self.assertEqual(classificar(10,11,''),'duvidosa')

    def test_null_nao_e_zero(self):
        self.assertIsNone(decidir(0,0,False)[0])
        self.assertIsNone(decidir(0,0,True,True)[0])
        self.assertEqual(decidir(0,0,True)[0],0)
        self.assertEqual(decidir(1,1,False)[0],1)

    def test_sensibilidade_fuso(self):
        self.assertIsNone(decidir(1,0,True)[0])
        a,b=variantes('2023-07-01 15:30:00')
        self.assertEqual(b-a,timedelta(hours=1))
        self.assertEqual(variantes('2023-01-01 15:30:00')[0],variantes('2023-01-01 15:30:00')[1])

    def test_fronteiras_24h(self):
        t=datetime(2023,1,1,15,tzinfo=timezone.utc);f=t+timedelta(days=1)
        self.assertEqual(contar([t,f,f+timedelta(seconds=1)],t,f),1)

    def test_manifestos_exports(self):
        for nome in ('Data2001_now','Data2001_noweliminados'):
            p=ROOT/(nome+'.csv');m=json.loads(p.with_suffix('.manifesto.json').read_text())
            self.assertEqual(sha(p),m['sha256']);self.assertEqual(p.stat().st_size,m['bytes'])

    def test_labels_sem_duplicados_e_zeros_cobertos(self):
        with (ROOT/'labels.csv').open(encoding='utf-8') as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),len({(r['municipio'],r['data_T']) for r in rows}))
        self.assertEqual(len(rows),26*2557)
        for r in rows:
            if r['target_24h']=='0':
                self.assertEqual(r['coverage_status'],'aceitavel')
                self.assertEqual(r['n_local'],'0');self.assertEqual(r['n_utc'],'0')
                self.assertEqual(r['motivo'],'zero_cobertura_empirica_aceitavel')

    def test_piloto_temporal_e_null(self):
        with (ROOT/'dataset_piloto.csv').open(encoding='utf-8') as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),3*183)
        self.assertEqual(sum(r['target_24h']=='' for r in rows),11)
        for r in rows:
            self.assertLess(datetime.fromisoformat(r['instante_referencia_utc']),datetime.fromisoformat(r['data_T']))
            self.assertEqual(r['available_at_historico'],'')
            self.assertEqual(r['estado_fwi'],'reconstruido')

    def test_amostra_10_20(self):
        rows=json.loads((ROOT/'amostra_revisao.json').read_text(encoding='utf-8'))
        self.assertEqual(sum(r['target_24h']==1 for r in rows),10)
        self.assertEqual(sum(r['target_24h']==0 for r in rows),20)
        self.assertEqual(len({r['municipio'] for r in rows}),3)
