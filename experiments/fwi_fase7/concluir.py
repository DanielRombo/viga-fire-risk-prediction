"""Relatórios de investigação rastreáveis, sem alterar qualquer valor calculado."""
import csv
import json
from collections import Counter,defaultdict
from pathlib import Path
from datetime import datetime

OUT=Path('/evidencias')
F6=Path('/workspace/experiments/fwi_fase6/evidencias')
INDICES=('ffmc','dmc','dc','isi','bui','fwi')
def ler(p):return json.loads(p.read_text())
def guardar(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

investigados=[];estatisticas=[];comparacoes=[];grelhas=defaultdict(list)
instantes_recolha=[];instantes_calculo=[];horas_recebidas=0;bytes_recebidos=0
for janela in (60,365):
    pasta=OUT/str(janela)
    cache={}
    for p in pasta.glob('*_comparacao.json'):
        nome=p.name.removesuffix('_comparacao.json');r=ler(p)
        cache[nome]=r['comparacoes'];comparacoes+=r['comparacoes']
    for a in ler(pasta/'alertas.json')['alertas']:
        ref=next(c for c in cache[a['regiao']] if c['data']==a['data'] and c['indice']==a['indice'])
        o=a['inputs'];p=a.get('inputs_anteriores');delta={k:o[k]-p[k] for k in ('temperatura','humidade','vento','precipitacao_24h')} if p else None
        if a['tipo']=='discrepancia_regional':
            contexto='Diferença regional exploratória; não demonstra erro. Rever precipitação, secura acumulada e representatividade da grelha.'
        elif a['indice'] in ('ffmc','dmc','dc','bui') and a['valor']<a['anterior'] and o['precipitacao_24h']>0:
            contexto='Queda com chuva na janela; efeito de humedecimento reproduzido pela referência.'
        elif 'extremo' in a['tipo']:
            contexto='Valor elevado reproduzido pela referência. Examinar conjuntamente estado seco acumulado, humidade e vento; não é uma classe oficial.'
        else:
            contexto='Variação conjunta de meteorologia e estado anterior; os seis índices do dia foram comparados, sem suavizar o salto.'
        if not ref['passou']: contexto='BLOQUEADO: divergência acima da tolerância; consultar divergencias.json.'
        investigados.append(dict(**a,janela_dias=janela,deltas_meteorologia=delta,
            comparacao=ref,conclusao_tecnica=contexto,
            verificacao='Inputs completos e cadeia consecutiva; resultado da referência explícito em comparacao.passou; sem validação meteorológica independente por estação.'))
    for p in pasta.glob('*_resultado.json'):
        nome=p.name.removesuffix('_resultado.json');r=ler(p);rec=ler(pasta/f'{nome}_recolha.json')
        instantes_recolha.append(datetime.fromisoformat(rec['ingerido_em']))
        instantes_calculo.append(datetime.fromisoformat(ler(pasta/f'{nome}_api.json')['calculado_em']))
        horas_recebidas+=len(ler(pasta/f'{nome}_resposta.json')['hourly']['time'])
        bytes_recebidos+=rec['bytes']
        estatisticas.append(dict(regiao=nome,janela=janela,**r))
        if janela==60:grelhas[(rec['latitude_grelha'],rec['longitude_grelha'])].append(nome)
guardar(OUT/'investigacao_alertas.json',investigados)
linhas=['# Investigação dos alertas','',
 'Todos os dias sinalizados foram comparados com cffdrs 1.8.17. Os limites são de triagem, não classes de risco. A confirmação é numérica; não substitui validação da meteorologia em estações locais.','',
 '| Região | Janela | Data | Índice / tipo | Valor | Anterior | Chuva mm | RH % | Vento km/h | Erro absoluto R | Contexto |',
 '|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|']
for a in investigados:
    o=a['inputs'];prev=a.get('anterior');prev=f'{prev:.5g}' if prev is not None else '—'
    linhas.append(f"| {a['regiao']} | {a['janela_dias']} | {a['data']} | {a['indice']} / {a['tipo']} | {a['valor']:.6g} | {prev} | {o['precipitacao_24h']:.4g} | {o['humidade']:.4g} | {o['vento']:.4g} | {a['comparacao']['diferenca_absoluta']:.3g} | {a['conclusao_tecnica']} |")
(OUT/'investigacao_alertas.md').write_text('\n'.join(linhas)+'\n',encoding='utf-8')

sensibilidade=[]
for p in (OUT/'365').glob('*_dias.json'):
    nome=p.name.removesuffix('_dias.json');curto=OUT/'60'/p.name
    if not curto.exists():curto=F6/p.name
    a=ler(curto);b=ler(p);assert len(a)==60
    for da,db in zip(a,b[-60:]):
        assert da['data_referencia']==db['data_referencia']
        for ha,hb in zip(da['horas'],db['horas']):
            for k in ('instante_utc','temperatura','humidade','vento','precipitacao_hora','latitude_grelha','longitude_grelha'):
                assert ha[k]==hb[k],('Revisão da fonte ou dados inconsistentes',nome,da['data_referencia'],k)
    sensibilidade.append(dict(regiao=nome,inputs_sobrepostos_identicos=True,
        diferenca_ultimo_dia={k:b[-1][k]-a[-1][k] for k in INDICES},
        max_diferenca_60dias={k:max(abs(db[k]-da[k]) for da,db in zip(a,b[-60:])) for k in INDICES}))
guardar(OUT/'sensibilidade_janela.json',sensibilidade)
diagnostico=[]
with (OUT/'diagnostico_rh100.csv').open() as f:
    cache_dias={}
    for linha in csv.DictReader(f):
        nome=linha['regiao']
        if nome not in cache_dias:cache_dias[nome]=ler(OUT/'365'/f'{nome}_dias.json')
        dia=cache_dias[nome][int(linha['indice'])]
        for k in INDICES:
            valor=float(linha[k.upper()]);erro=abs(valor-dia[k])
            diagnostico.append(dict(regiao=nome,data=dia['data_referencia'],indice=k,
                xclim=dia[k],r_interno_rh100=valor,diferenca_absoluta=erro,
                passou_mesma_tolerancia=erro<=1e-8+1e-10*abs(valor)))
guardar(OUT/'diagnostico_rh100.json',dict(nota='Diagnóstico das funções internas sem alteração. Não substitui a reprovação da API pública cffdrs.',
    passou=all(d['passou_mesma_tolerancia'] for d in diagnostico),comparacoes=diagnostico))
resumo=dict(regioes_60=25,regioes_365=len(sensibilidade),
    intervalo_real_primeira_recolha_ultimo_calculo_segundos=(max(instantes_calculo)-min(instantes_recolha)).total_seconds(),
    horas_recebidas_com_margens=horas_recebidas,bytes_respostas=bytes_recebidos,
    dias=sum(r['dias'] for r in estatisticas),horas=sum(r['horas'] for r in estatisticas),
    chamadas=sum(r['chamadas_externas'] for r in estatisticas),retries=sum(r['retries'] for r in estatisticas),falhas_fonte=0,
    tempos_execucao={str(j):{m:ler(OUT/str(j)/f'tempo_{m}.json')['segundos'] for m in ('recolher','reconstruir','comparar')} for j in (60,365)},
    soma_segundos_recolha=sum(r['duracao_recolha_segundos'] for r in estatisticas),
    soma_segundos_calculo_persistencia=sum(r['duracao_reconstrucao_segundos'] for r in estatisticas),
    pico_rss_mib=max(r['pico_rss_mib'] for r in estatisticas),
    alertas_por_janela={str(j):len([a for a in investigados if a['janela_dias']==j]) for j in (60,365)},
    tipos_alerta=dict(Counter(a['tipo'] for a in investigados)),
    comparacoes=len(comparacoes),dias_amostrados=len(comparacoes)//6,
    comparacoes_reprovadas=sum(not c['passou'] for c in comparacoes),
    max_erro_absoluto=max(c['diferenca_absoluta'] for c in comparacoes),
    max_erro_relativo=max(c['diferenca_relativa'] or 0 for c in comparacoes),
    grelhas_partilhadas=[dict(latitude=k[0],longitude=k[1],regioes=v) for k,v in grelhas.items() if len(v)>1],
    maximos_fwi=sorted([dict(regiao=r['regiao'],janela=r['janela'],maximo=r['estatisticas']['fwi']['max']) for r in estatisticas],key=lambda r:r['maximo'],reverse=True)[:10])
guardar(OUT/'resumo.json',resumo)
print(json.dumps(resumo,ensure_ascii=False,indent=2))
