import csv
import json
import unittest
from datetime import datetime
from auditar_prdf import OUT, frp_timestamp, rural, ro

def load(name):
    return json.loads((OUT/name).read_text(encoding='utf-8'))

class AuditoriaTests(unittest.TestCase):
    def test_contagens_reconciliadas(self):
        f=load('fogos.json'); c=load('cobertura_resumo.json')
        self.assertEqual(f['n'],824875)
        self.assertEqual(sum(f['ano2025']['meses'].values()),8252)
        self.assertEqual(sum(c['taxonomia2025'].values()),8252)
        self.assertEqual(c['taxonomia2025']['potencial_nova_ocorrencia'],7579)

    def test_taxonomia_nao_depende_area_ou_meios(self):
        r=dict(Tipo='Florestal',DHInicio='2025-06-01T12:00:00Z',CodCausa=0)
        self.assertEqual(rural(r),'potencial_nova_ocorrencia')
        self.assertEqual(rural(dict(r,CodCausa=711)),'reacendimento')
        self.assertEqual(rural(dict(r,Reacendimento_IncendioPai='pai')),'reacendimento')
        self.assertEqual(rural(dict(r,Tipo='Queima')),'tipo_nao_rural')
        self.assertEqual(rural(dict(r,DHInicio=None)),'timestamp_invalido')

    def test_fronteiras_frp(self):
        r=dict(ano='2024',mes='2',dia='29',hora='23',minuto='59',segundo='NA',ACQTIME='1904-02-29')
        self.assertEqual(frp_timestamp(r),datetime(2024,2,29,23,59))
        self.assertIsNone(frp_timestamp(dict(r,ano='2025')))

    def test_cobertura_nao_converte_null(self):
        with (OUT/'cobertura_2025.csv').open(encoding='utf-8',newline='') as f: rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),308*12)
        self.assertEqual(len({(r['municipio'],r['mes']) for r in rows}),len(rows))
        for r in rows:
            self.assertEqual(sum(int(r[k]) for k in ('positivos_potenciais','negativos_condicionais_potenciais','null')),int(r['janelas']))
            if r['coverage_status'] not in ('FORTE','ACEITÁVEL'):
                self.assertEqual(int(r['negativos_condicionais_potenciais']),0)
        s=load('cobertura_resumo.json')['municipios_piloto']
        self.assertEqual(sum(x['positivos_potenciais'] for x in s.values()),73)
        self.assertEqual(sum(x['null'] for x in s.values()),1022)

    def test_meteo_integridade_ligacoes(self):
        m=load('meteo.json'); a=load('meteo_chaves.json')
        self.assertEqual(sum(a['match'].values()),m['n'])
        self.assertEqual(m['n'],3568731)
        self.assertEqual(m['ano2025']['com_meteo'],8252)
        self.assertEqual(m['ano2025']['linhas'],26140)
        self.assertEqual(m['duplicados'],{'id':[0,0],'code,t':[0,0]})

    def test_leakage_campos_evento(self):
        with (OUT/'leakage.csv').open(encoding='utf-8',newline='') as f: rows=list(csv.DictReader(f))
        # Nenhuma variável medida no incêndio futuro é admitida automaticamente.
        for r in rows:
            if r['fonte'] in ('FRP','PBA'):
                self.assertNotEqual(r['categoria'],'SAFE_EM_T')
        self.assertTrue(any(r['campo'].upper()=='FWI' and r['fonte']=='METEO' and r['categoria']=='PROIBIDO' for r in rows))

    def test_originais_integridade(self):
        i=load('integridade_originais.json')
        self.assertTrue(i['originais_inalterados'])
        self.assertEqual(len(i['sha256']),5)

    def test_sql_readonly_e_contagens(self):
        with ro('fogos.gpkg') as db:
            self.assertEqual(db.execute('PRAGMA query_only').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM Fogos WHERE Ano=2025').fetchone()[0],8252)

if __name__=='__main__':unittest.main()
