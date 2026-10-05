"""Verificações offline da recolha real; não consulta a fonte nem recalcula FWI."""
import hashlib
import json
import math
import unittest
from datetime import datetime, timedelta
from pathlib import Path

OUT = Path(__file__).parent/'evidencias'
REGIOES = ('Lisboa', 'Faro', 'Vila Real', 'Funchal', 'Ponta Delgada')


def ler(nome):
    return json.loads((OUT/nome).read_text(encoding='utf-8'))


class EvidenciasTests(unittest.TestCase):
    def test_integridade_inputs_reais_e_unidades(self):
        for nome in REGIOES:
            with self.subTest(regiao=nome):
                r=ler(f'{nome}_recolha.json')
                bruto=(OUT/f'{nome}_resposta.json').read_bytes()
                self.assertEqual(hashlib.sha256(bruto).hexdigest(), r['sha256'])
                dados=json.loads(bruto)
                self.assertEqual(dados['utc_offset_seconds'],0)
                self.assertEqual(dados['hourly_units'],dict(time='iso8601', temperature_2m='°C',
                    relative_humidity_2m='%', wind_speed_10m='km/h', precipitation='mm'))
                self.assertEqual(r['parametros']['models'],'ecmwf_ifs')
                self.assertEqual(r['estado'],'validado')
                self.assertEqual(r['horas_utilizadas'],r['janela_dias']*24)

    def test_dias_precipitacao_e_cadeia(self):
        for nome in REGIOES:
            with self.subTest(regiao=nome):
                dias=ler(f'{nome}_dias.json')
                self.assertEqual(len(dias),365 if nome=='Lisboa' else 60)
                anterior=None
                for d in dias:
                    o=d['observacao']; horas=d['horas']; t=datetime.fromisoformat(o['instante_referencia_utc'])
                    self.assertEqual(t.hour,13 if nome=='Ponta Delgada' else 12)
                    self.assertEqual(len(horas),24)
                    self.assertEqual([datetime.fromisoformat(h['instante_utc']) for h in horas],
                        [t-timedelta(hours=23-i) for i in range(24)])
                    self.assertEqual(o['precipitacao_24h'],math.fsum(h['precipitacao_hora'] for h in horas))
                    for k in ('temperatura','humidade','vento'):
                        self.assertEqual(o[k],horas[-1][k])
                    if anterior:
                        self.assertEqual(d['id_anterior'],anterior['id_dia'])
                        for k in ('ffmc','dmc','dc'):
                            self.assertEqual(d['estado_anterior'][k],anterior[k])
                    for k in ('ffmc','dmc','dc','isi','bui','fwi'):
                        self.assertTrue(math.isfinite(d[k]) and d[k]>=0)
                    anterior=d

    def test_api_nao_operacional_historico_e_null(self):
        for nome in REGIOES:
            with self.subTest(regiao=nome):
                self.assertIsNone(ler(f'{nome}_api_antes.json')['fwi'])
                atual=ler(f'{nome}_api.json')
                self.assertFalse(atual['operacional'])
                self.assertFalse(atual['estabelecido'])
                self.assertEqual(atual['estado_inicializacao'],'reconstruido')
                self.assertEqual(atual['data_referencia'],'2026-09-30')
                self.assertIsInstance(atual['fwi'],float)
                historico=ler(f'{nome}_api_historico.json')['resultados']
                datas=[d['data_referencia'] for d in historico]
                self.assertEqual(datas,sorted(set(datas)))
                self.assertTrue(all(not d['operacional'] for d in historico))

    def test_referencia_e_idempotencia(self):
        for nome in REGIOES:
            with self.subTest(regiao=nome):
                r=ler(f'{nome}_comparacao.json')
                self.assertEqual((r['atol'],r['rtol']),(1e-8,1e-10))
                self.assertTrue(r['passou'])
                self.assertTrue(ler(f'{nome}_resultado.json')['idempotencia'])


if __name__=='__main__': unittest.main(verbosity=2)
