import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from labels_5b2 import target_24h

class ContratoTests(unittest.TestCase):
    def setUp(self):
        self.t = datetime(2022, 7, 1, 15, tzinfo=timezone.utc)
        self.c = dict(fonte='fonte-simulada', snapshot_sha256='hash-simulado',
                      documento_cobertura='documento-simulado', taxonomia_validada=True,
                      territorio_validado=True, timestamp_validado=True, extracao_integral=True,
                      consolidado=True, sem_ambiguidades=True,
                      inicio=self.t, fim=self.t+timedelta(days=1))

    def test_positivo_nao_exige_completude(self):
        self.assertEqual(target_24h(self.t,[self.t+timedelta(hours=1)],None),1)

    def test_fronteiras(self):
        self.assertEqual(target_24h(self.t,[self.t],self.c),0)
        self.assertEqual(target_24h(self.t,[self.t+timedelta(days=1)],self.c),1)

    def test_sem_cobertura_nao_e_zero(self):
        self.assertIsNone(target_24h(self.t,[],None))
        for k in self.c:
            c=self.c.copy();c.pop(k)
            self.assertIsNone(target_24h(self.t,[],c),k)

    def test_cobertura_parcial_e_ambiguidade(self):
        c=self.c.copy();c['fim']-=timedelta(seconds=1)
        self.assertIsNone(target_24h(self.t,[],c))
        c=self.c.copy();c['sem_ambiguidades']=False
        self.assertIsNone(target_24h(self.t,[],c))

    def test_zero_certificado(self):
        self.assertEqual(target_24h(self.t,[],self.c),0)

    def test_timestamp_sem_fuso(self):
        with self.assertRaises(ValueError):target_24h(self.t.replace(tzinfo=None),[],self.c)
        with self.assertRaises(ValueError):target_24h(self.t,[self.t.replace(tzinfo=None)],self.c)

    def test_24_horas_reais(self):
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try: zona=ZoneInfo('Europe/Lisbon')
        except ZoneInfoNotFoundError:self.skipTest('Base IANA não instalada no ambiente de teste.')
        t=datetime(2022,3,26,15,tzinfo=zona)
        # Mudança de hora: 16h civis no dia seguinte ainda pertence às 24 horas UTC.
        self.assertEqual(target_24h(t,[datetime(2022,3,27,16,tzinfo=zona)],None),1)

    def test_integridade_fontes(self):
        pasta=Path(__file__).resolve().parent/'fontes_5b2'
        for p in pasta.glob('*.json'):
            m=json.loads(p.read_text(encoding='utf-8'))
            dados=p.with_suffix('.bin').read_bytes()
            self.assertEqual(hashlib.sha256(dados).hexdigest(),m['sha256'])
            self.assertEqual(len(dados),m['bytes'])

    def test_catalogo_so_28_ativos(self):
        p=Path(__file__).resolve().parent/'auditoria_5b2/municipios_catalogo.json'
        rows=json.loads(p.read_text(encoding='utf-8'))
        self.assertEqual(len(rows),28)
        self.assertEqual(sum(len(r['codigos_candidatos'])==1 for r in rows),26)
        self.assertTrue(all(not r['cobertura_certificada'] for r in rows))
