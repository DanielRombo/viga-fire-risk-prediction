"""Contraprova no SGIF original e testes do dataset, sem bibliotecas ML/rede/BD."""
import csv
import hashlib
import json
import math
import unittest
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BASE=Path(__file__).resolve().parent
OUT=BASE/'dataset_5b3'


def ler(nome):
    with (OUT/nome).open(encoding='utf-8') as f:return list(csv.DictReader(f))


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def auditar_amostra():
    rows=ler('dataset_elegivel.csv');completo=ler('dataset_completo.csv');amostra=[]
    # Repartição municipal, distribuída cronologicamente; não escolhe pela meteorologia.
    for c,np,nn in [('1106',3,7),('0805',3,7),('1714',4,6)]:
        for y,n in [('1',np),('0',nn)]:
            pool=[r for r in rows if r['municipio']==c and r['target_24h']==y]
            assert len(pool)>=n
            amostra.extend(pool[round(i*(len(pool)-1)/(n-1))] for i in range(n))
        pool=[r for r in completo if r['municipio']==c and r['target_24h']=='']
        amostra.extend([pool[0],pool[-1]])
    mapa=defaultdict(set)
    with (BASE/'fontes_5b2/sgif_administracao.bin').open(encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):mapa[r['INE'].zfill(6)].add(r['DTCC'])
    with (BASE/'cobertura_5b2b/Data2001_noweliminados.csv').open(encoding='utf-8-sig') as f:
        eliminados={r['Codigo'] for r in csv.DictReader(f)}
    eventos=defaultdict(list)
    with (BASE/'cobertura_5b2b/Data2001_now.csv').open(encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if not '2022'<=r['DHInicio'][:4]<='2025':continue
            codes=mapa.get(r['INE'].zfill(6),set())
            if len(codes)!=1:continue
            c=next(iter(codes))
            if c not in ('1106','0805','1714'):continue
            if r['Codigo'] in eliminados or r['Tipo'] not in ('Florestal','Agrícola'):continue
            if r['Reacendimento_IncendioPai'] or r['Reacendimentos'] not in ('','0') or r['CodCausa']=='711':continue
            eventos[c].append({k:r[k] for k in ('Codigo','DHInicio','Tipo','INE','Lat_4326','Lon_4326')})
    resultados=[]
    for a in amostra:
        t=datetime.fromisoformat(a['data_T']);fim=t+timedelta(days=1);verif={}
        for nome,fuso in [('local',ZoneInfo('Europe/Lisbon')),('utc',timezone.utc)]:
            ordenados=sorted((datetime.fromisoformat(r['DHInicio']).replace(tzinfo=fuso).astimezone(timezone.utc),r['Codigo'],r) for r in eventos[a['municipio']])
            dentro=[r for d,_,r in ordenados if t<d<=fim]
            antes=[r for d,_,r in ordenados if d<=t];depois=[r for d,_,r in ordenados if d>fim]
            if a['target_24h']!='':assert bool(dentro)==(a['target_24h']=='1'),(a,nome,dentro)
            verif[nome]=dict(dentro=dentro,anterior=antes[-1] if antes else None,seguinte=depois[0] if depois else None)
        resultados.append(dict(municipio=a['municipio'],data_T=a['data_T'],target=a['target_24h'],
            coverage_status=a['coverage_status'],motivo=a['motivo'],motivos_exclusao=a['motivos_exclusao'],verificacao=verif))
    (OUT/'amostra_validada.json').write_text(json.dumps(resultados,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for r in resultados:
        print(r['municipio'],r['data_T'][:10],r['target'] or 'null',r['motivo'],
              [(v['Codigo'],v['DHInicio']) for v in r['verificacao']['local']['dentro']])


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=ler('dataset_completo.csv');cls.eligible=ler('dataset_elegivel.csv');cls.excluded=ler('exclusoes.csv')

    def test_inventario_continuo(self):
        self.assertEqual(len(self.rows),3288)
        self.assertEqual(len({(r['municipio'],r['data_T']) for r in self.rows}),3288)
        for c in ('1106','0805','1714'):
            ds=[datetime.fromisoformat(r['data_T']) for r in self.rows if r['municipio']==c]
            self.assertEqual(len(ds),1096)
            self.assertTrue(all(b-a==timedelta(days=1) for a,b in zip(ds,ds[1:])))

    def test_targets_preservados(self):
        self.assertEqual(sum(r['target_24h']=='' for r in self.rows),467)
        self.assertEqual(sum(r['target_24h']=='1' for r in self.rows),177)
        self.assertEqual(sum(r['target_24h']=='0' for r in self.rows),2644)
        self.assertTrue(all(r['target_24h']=='' for r in self.rows if r['municipio']=='1106' and r['ano']=='2024'))

    def test_particao_sem_perdas(self):
        key=lambda r:(r['municipio'],r['data_T'])
        a=set(map(key,self.eligible));b=set(map(key,self.excluded))
        self.assertFalse(a&b);self.assertEqual(a|b,set(map(key,self.rows)))
        self.assertTrue(all(r['motivos_exclusao'] for r in self.excluded))

    def test_elegibilidade(self):
        for r in self.eligible:
            self.assertIn(r['target_24h'],('0','1'));self.assertIn(r['coverage_status'],('aceitavel','forte'))
            self.assertIn(r['territory_confidence'],('alta','media'));self.assertEqual(r['fwi_sementes_convergentes'],'True')
            self.assertEqual((datetime.fromisoformat(r['data_T'])+timedelta(days=1)).year,int(r['ano']))

    def test_features_e_tempo(self):
        for r in self.rows:
            for k in ('temperatura','humidade','vento','precipitacao_24h','ffmc','dmc','dc','isi','bui','fwi'):
                self.assertTrue(math.isfinite(float(r[k])))
                if k!='temperatura':self.assertGreaterEqual(float(r[k]),0)
            self.assertLessEqual(float(r['humidade']),100)
            t=datetime.fromisoformat(r['data_T']);ref=datetime.fromisoformat(r['instante_referencia_utc'])
            self.assertEqual(t-ref,timedelta(hours=3))
            self.assertEqual(ref-datetime.fromisoformat(r['precipitacao_inicio_exclusivo_utc']),timedelta(days=1))
            self.assertEqual(r['available_at_historico'],'')

    def test_convergencia_local(self):
        # Depende só da dispersão no T; não de uma data de convergência vista no futuro.
        for r in self.eligible:
            for k in ('ffmc','dmc','dc','isi','bui','fwi'):
                self.assertLessEqual(float(r[k+'_spread_sementes']),1e-8+1e-10*(abs(float(r[k]))+float(r[k+'_spread_sementes'])))

    def test_schema_sem_leakage_metadata(self):
        s=json.loads((OUT/'schema.json').read_text(encoding='utf-8'))
        for col in ('target_24h','coverage_status','n_local','n_utc','elegivel','motivo','fwi_sementes_convergentes'):
            self.assertNotIn(col,s['features_permitidas'])

    def test_amostra(self):
        a=json.loads((OUT/'amostra_validada.json').read_text(encoding='utf-8'))
        self.assertEqual(sum(r['target']=='1' for r in a),10)
        self.assertEqual(sum(r['target']=='0' for r in a),20)
        self.assertEqual(sum(r['target']=='' for r in a),6)

    def test_checksums(self):
        m=json.loads((OUT/'checksums.json').read_text(encoding='utf-8'))
        for nome,digest in m.items():self.assertEqual(sha(OUT/nome),digest,nome)
        man=json.loads((OUT/'manifesto.json').read_text(encoding='utf-8'))
        for nome,meta in man['fontes'].items():self.assertEqual(sha(BASE.parents[1]/nome),meta['sha256'],nome)


if __name__=='__main__':
    if '--amostra' in __import__('sys').argv:auditar_amostra()
    else:unittest.main()
