"""Diagnóstico após bloqueio: regista falhas, nunca as converte em aprovação."""
import importlib.util
import json
from pathlib import Path
spec=importlib.util.spec_from_file_location('analise6','/workspace/experiments/fwi_fase6/analisar.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.OUT=Path('/evidencias/365')
falhas=[]
for p in sorted(m.OUT.glob('*_referencia.csv')):
    nome=p.name.removesuffix('_referencia.csv')
    try:m.comparar(nome)
    except AssertionError:
        r=json.loads((m.OUT/f'{nome}_comparacao.json').read_text())
        dias={d['data_referencia']:d for d in json.loads((m.OUT/f'{nome}_dias.json').read_text())}
        for c in r['comparacoes']:
            if not c['passou']:falhas.append(dict(regiao=nome,**c,observacao=dias[c['data']]['observacao'],estado_anterior=dias[c['data']]['estado_anterior']))
(m.OUT.parent/'divergencias.json').write_text(json.dumps(dict(estado='bloqueado' if falhas else 'aprovado',
    divergencias=falhas,nota='Diagnóstico completo; nenhuma tolerância, input ou cálculo alterado.'),ensure_ascii=False,indent=2),encoding='utf-8')
print('Diagnóstico concluído; comparações REPROVADAS:',len(falhas))
