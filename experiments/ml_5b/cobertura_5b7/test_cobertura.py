import csv,hashlib,json,unittest
from consolidar import P,ML,load,permite_zero

def rows(name):
    with (P/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))

class CoverageTests(unittest.TestCase):
    def test_norma_e_total_nao_certificam_zero(self):
        self.assertFalse(permite_zero(dict(universo_operacional=True,inclui_rurais=True,municipio_coberto=True)))

    def test_cada_condicao_obrigatoria(self):
        complete={k:True for k in load(P/'config.json')['condicoes_zero']}
        self.assertTrue(permite_zero(complete))
        for k in complete:
            self.assertFalse(permite_zero(dict(complete,**{k:False})),k)
            self.assertFalse(permite_zero(dict(complete,**{k:None})),k)

    def test_cobertura36_sem_duplicados(self):
        data=rows('matriz_cobertura_2025.csv')
        self.assertEqual(len(data),36)
        self.assertEqual(len({(r['municipio'],r['mes']) for r in data}),36)
        self.assertEqual({r['decisao'] for r in data},{'DUVIDOSO'})
        for r in data:
            self.assertEqual(int(r['negativos_condicionais_potenciais']),0)
            self.assertEqual(sum(int(r[k]) for k in ['positivos_potenciais','negativos_condicionais_potenciais','null']),int(r['janelas']))

    def test_estimativas_preservadas(self):
        r=load(P/'resultado.json')
        self.assertEqual(r['totais'],dict(positivos_potenciais=73,negativos_condicionais_potenciais=0,null=1022,janelas=1095))
        self.assertEqual(r['reducao_null'],0)
        self.assertEqual(r['periodos_elegiveis'],[])
        old={ (r['municipio'],r['mes']):r for r in csv.DictReader((ML/'prdf_auditoria/cobertura_2025.csv').read_text(encoding='utf-8').splitlines())}
        for row in rows('matriz_cobertura_2025.csv'):
            prev=old[row['municipio'],row['mes']]
            for k in ['positivos_potenciais','null']:self.assertEqual(row[k],prev[k])

    def test_ine_republicacao_provisoria(self):
        r=load(P/'ine_verificacao.json')
        self.assertTrue(r['dados_iguais_cache'])
        for total in r['totais'].values():self.assertEqual(total['sinal_conv'],'&')
        sources={r['id']:r for r in rows('fontes.csv')}
        self.assertEqual(sources['INE_13512']['fonte_primaria'],'ICNF Estatísticas florestais')
        self.assertTrue(all(r['aplicavel_a_negativos_PT']=='False' for r in sources.values()))

    def test_http200_nao_confundido_com_export(self):
        r=load(P/'evidencias/anepc_historico.json')
        self.assertIn('text/html',r['content_type'])
        self.assertNotEqual(r['url'],r['url_final'])
        source=next(r for r in rows('fontes.csv') if r['id']=='PROCIV_HIST')
        self.assertEqual(source['utilidade'],'D')

    def test_amostra_nao_e_ficheiro_completo(self):
        r=load(P/'evidencias/sgif_diario_amostra.json')
        self.assertTrue(r['amostra']);self.assertEqual(r['status'],206)
        self.assertLessEqual(r['bytes'],32768)
        self.assertIn('/10793142',r['content_range'])

    def test_inputs_identicos(self):
        for r in load(P/'manifesto_inputs.json'):
            f=ML/r['ficheiro']
            self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(),r['sha256'])

    def test_fontes_e_reconciliacao(self):
        source_ids={r['id'] for r in rows('fontes.csv')}
        for r in rows('matriz_cobertura_2025.csv'):
            self.assertTrue(set(r['evidencias'].split(';'))<=source_ids)
        for r in rows('reconciliacao_mensal.csv'):
            self.assertEqual(int(r['prdf'])-int(r['icnf_provisorio_20251001']),int(r['diferenca_prdf_menos_publicado']))
        self.assertEqual(len(rows('contagens_mensais.csv')),12)

if __name__=='__main__':unittest.main()
