"""Audita todos os inputs reais, a cadeia persistida e as evidências das ilhas."""
import csv
import hashlib
import json
import math
import unittest
from datetime import datetime,timedelta
from pathlib import Path

ROOT=Path('/workspace')
OUT=Path('/evidencias')
F6=ROOT/'experiments/fwi_fase6/evidencias'
INDICES=('ffmc','dmc','dc','isi','bui','fwi')


def ler(p): return json.loads(p.read_text())


class Evidencias(unittest.TestCase):
    def test_cobertura_catalogo(self):
        catalogo=ler(ROOT/'backend/data/regioes_principais.json')
        esperado={r['nome'] for r in catalogo}-{'Lisboa','Faro','Vila Real','Funchal','Ponta Delgada'}
        feitos={p.name.removesuffix('_resultado.json') for p in (OUT/'60').glob('*_resultado.json')}
        self.assertEqual(feitos,esperado)
        anuais={p.name.removesuffix('_resultado.json') for p in (OUT/'365').glob('*_resultado.json')}
        self.assertTrue({'Porto','Bragança','Coimbra','Castelo Branco','Évora','Faro'}<=anuais)
        self.assertTrue(set(ler(OUT/'ampliar.json'))<=anuais)

    def test_inputs_todos_dias_e_cadeias(self):
        catalogo={r['nome']:r for r in ler(ROOT/'backend/data/regioes_principais.json')}
        for janela in (60,365):
            for p in (OUT/str(janela)).glob('*_dias.json'):
                nome=p.name.removesuffix('_dias.json');pasta=p.parent
                with self.subTest(regiao=nome,janela=janela):
                    recolha=ler(pasta/f'{nome}_recolha.json');bruto=(pasta/f'{nome}_resposta.json').read_bytes()
                    self.assertEqual(hashlib.sha256(bruto).hexdigest(),recolha['sha256'])
                    raw=json.loads(bruto);horario=raw['hourly'];ts=horario['time']
                    self.assertEqual(len(ts),len(set(ts)))
                    self.assertEqual(raw['utc_offset_seconds'],0)
                    self.assertEqual(raw['hourly_units'],dict(time='iso8601',temperature_2m='°C',relative_humidity_2m='%',wind_speed_10m='km/h',precipitation='mm'))
                    self.assertEqual(recolha['parametros']['models'],'ecmwf_ifs')
                    for k in ('latitude','longitude'): self.assertEqual(recolha['regiao'][k],catalogo[nome][k])
                    inicio=datetime.fromisoformat(recolha['inicio_utc'])
                    dias=ler(p);self.assertEqual(len(dias),janela);anterior=None
                    for i,d in enumerate(dias):
                        ref=datetime.fromisoformat(d['observacao']['instante_referencia_utc'])
                        self.assertEqual(ref,inicio+timedelta(hours=23,days=i))
                        self.assertEqual(len(d['horas']),24)
                        for h,hora in enumerate(d['horas']):
                            self.assertEqual(datetime.fromisoformat(hora['instante_utc']),ref-timedelta(hours=23-h))
                            self.assertEqual(hora['qualidade'],'valido')
                            for k in ('temperatura','humidade','vento','precipitacao_hora'): self.assertTrue(math.isfinite(hora[k]))
                        self.assertEqual(d['observacao']['precipitacao_24h'],math.fsum(h['precipitacao_hora'] for h in d['horas']))
                        for k in ('temperatura','humidade','vento'): self.assertEqual(d['observacao'][k],d['horas'][-1][k])
                        if anterior:
                            self.assertEqual(d['id_anterior'],anterior['id_dia'])
                            for k in ('ffmc','dmc','dc'): self.assertEqual(d['estado_anterior'][k],anterior[k])
                        else: self.assertEqual([d['estado_anterior'][k] for k in ('ffmc','dmc','dc')],[85,6,15])
                        for k in INDICES:self.assertTrue(math.isfinite(d[k]) and d[k]>=0)
                        anterior=d
                    api=ler(pasta/f'{nome}_api.json')
                    self.assertFalse(api['operacional']);self.assertFalse(api['estabelecido'])
                    self.assertEqual(api['estado_inicializacao'],'reconstruido')
                    self.assertTrue(ler(pasta/f'{nome}_resultado.json')['idempotencia'])

    def test_alertas_todos_comparados_e_tolerancias(self):
        for janela in (60,365):
            pasta=OUT/str(janela)
            for a in ler(pasta/'alertas.json')['alertas']:
                r=ler(pasta/f"{a['regiao']}_comparacao.json")
                self.assertEqual((r['atol'],r['rtol']),(1e-8,1e-10))
                self.assertTrue(r['passou'])
                self.assertTrue(any(c['data']==a['data'] and c['indice']==a['indice'] and c['passou'] for c in r['comparacoes']))

    def test_ilhas_evidencias_preservadas(self):
        resultados=[]
        for nome,hora in [('Funchal',12),('Ponta Delgada',13)]:
            r=ler(F6/f'{nome}_recolha.json');bruto=(F6/f'{nome}_resposta.json').read_bytes()
            self.assertEqual(hashlib.sha256(bruto).hexdigest(),r['sha256'])
            dias=ler(F6/f'{nome}_dias.json');self.assertEqual(len(dias),60)
            for d in dias:
                ref=datetime.fromisoformat(d['observacao']['instante_referencia_utc'])
                self.assertEqual(ref.hour,hora)
                self.assertEqual([datetime.fromisoformat(h['instante_utc']) for h in d['horas']],
                    [ref-timedelta(hours=23-i) for i in range(24)])
                self.assertEqual(d['observacao']['precipitacao_24h'],math.fsum(h['precipitacao_hora'] for h in d['horas']))
            resultados.append(dict(regiao=nome,horas=1440,dias=60,referencia_utc=hora,sha256=r['sha256'],
                limite='Ponto representativo do catálogo; não cobre todo o arquipélago.',recolha_repetida=False))
        (OUT/'ilhas.json').write_text(json.dumps(resultados,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__': unittest.main(verbosity=2)
