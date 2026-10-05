"""Fecho offline: não recolhe meteorologia nem recalcula qualquer índice."""
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import unittest

OUT=Path('/evidencias')
spec=importlib.util.spec_from_file_location('validar7','/workspace/experiments/fwi_fase7/validar.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
suite=unittest.TestSuite(m.Evidencias(n) for n in (
    'test_cobertura_catalogo','test_inputs_todos_dias_e_cadeias','test_ilhas_evidencias_preservadas'))
resultado=unittest.TextTestRunner(verbosity=2).run(suite)
assert resultado.wasSuccessful()

def ler(p):return json.loads(p.read_text(encoding='utf-8-sig'))
falhas=[];total=0;dias_total=horas_total=0
for janela,esperado in ((60,25),(365,26)):
    pasta=OUT/str(janela)
    res=list(pasta.glob('*_resultado.json'));assert len(res)==esperado
    for p in res:
        nome=p.name.removesuffix('_resultado.json')
        for sufixo in ('api.json','api_antes.json','api_historico.json','dias.json','estado.json',
                       'recolha.json','resposta.json','episodios.json','amostra_inputs.csv','referencia.csv','comparacao.json'):
            assert (pasta/f'{nome}_{sufixo}').is_file(),(nome,sufixo)
        r=ler(p);dias_total+=r['dias'];horas_total+=r['horas']
        dias={d['data_referencia']:d for d in ler(pasta/f'{nome}_dias.json')}
        comp=ler(pasta/f'{nome}_comparacao.json')
        assert (comp['atol'],comp['rtol'])==(1e-8,1e-10)
        for c in comp['comparacoes']:
            total+=1
            assert c['xclim']==dias[c['data']][c['indice']]
            erro=abs(c['xclim']-c['referencia'])
            assert erro==c['diferenca_absoluta']
            passou=erro<=1e-8+1e-10*abs(c['referencia'])
            assert passou==c['passou']
            if not passou:
                assert dias[c['data']]['observacao']['humidade']==100
                falhas.append((nome,c['data'],c['indice']))
        assert comp['passou']==all(c['passou'] for c in comp['comparacoes'])
assert (dias_total,horas_total,total,len(falhas))==(10990,263760,6018,56)
registadas=ler(OUT/'divergencias.json')['divergencias']
assert set(falhas)=={(d['regiao'],d['data'],d['indice']) for d in registadas}
sens=ler(OUT/'sensibilidade_janela.json')
for s in sens:
    nome=s['regiao'];curto=OUT/'60'/f'{nome}_dias.json'
    if not curto.exists():curto=Path('/workspace/experiments/fwi_fase6/evidencias')/curto.name
    a,b=ler(curto),ler(OUT/'365'/curto.name)
    for da,db in zip(a,b[-60:]):
        for ha,hb in zip(da['horas'],db['horas']):
            for k in ('instante_utc','temperatura','humidade','vento','precipitacao_hora','latitude_grelha','longitude_grelha'):
                assert ha[k]==hb[k]
    for k,v in s['diferenca_ultimo_dia'].items():assert v==b[-1][k]-a[-1][k]
    for k,v in s['max_diferenca_60dias'].items():assert v==max(abs(db[k]-da[k]) for da,db in zip(a,b[-60:]))
diag=ler(OUT/'diagnostico_rh100.json')
assert diag['passou'] and len(diag['comparacoes'])==108
assert all(c['diferenca_absoluta']<=1e-8+1e-10*abs(c['r_interno_rh100']) for c in diag['comparacoes'])
manifesto={}
for p in sorted(OUT.rglob('*')):
    if not p.is_file() or p.name in ('manifesto_fecho.json','verificacao_fecho.json'):continue
    conteudo=p.read_bytes()
    if p.suffix=='.json':ler(p)
    manifesto[str(p.relative_to(OUT))]=dict(bytes=len(conteudo),sha256=hashlib.sha256(conteudo).hexdigest())
(OUT/'manifesto_fecho.json').write_text(json.dumps(manifesto,ensure_ascii=False,indent=2),encoding='utf-8')
resumo=dict(integridade=True,ficheiros=len(manifesto),dias=dias_total,horas=horas_total,
    comparacoes=total,reprovadas=len(falhas),regioes_com_divergencia=len({r for r,d,i in falhas}),
    dias_regiao_com_divergencia=len({(r,d) for r,d,i in falhas}),
    sensibilidade_confirmada=len(sens),diagnostico_interno_rh100_confirmado=True,
    estado_cientifico='bloqueado',nota='Integridade confirmada; as 56 reprovações originais permanecem. Sem novas recolhas ou reconstruções.')
(OUT/'verificacao_fecho.json').write_text(json.dumps(resumo,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(resumo,ensure_ascii=False,indent=2))
