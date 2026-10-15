"""Fecho documental: hashes e métricas já guardadas; sem bibliotecas de treino."""
import argparse,csv,hashlib,json,os,subprocess
from collections import defaultdict
from pathlib import Path
OUT=Path(__file__).resolve().parent; ML=OUT.parent; ROOT=ML.parents[1]

def load(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def csvsave(name,rows):
    with (OUT/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def verificar():
    cfg=load(OUT/'config.json');dec=load(ML/'modelo_5b5/decisao.json');errors=[];checked=[]
    for phase in ['modelo_5b4','modelo_5b5']:
        manifest=load(ML/phase/'manifesto.json')
        for name,expected in manifest['checksums'].items():
            p=ML/phase/name;actual=sha(p) if p.exists() else None
            checked.append(dict(ficheiro=str(p.relative_to(ML)),esperado=expected,atual=actual))
            if actual!=expected:errors.append(str(p.relative_to(ML)))
    assert not errors,'PARAR: divergência histórica: '+str(errors)
    assert sha(ML/'modelo_5b5/candidato.joblib')==cfg['sha256_candidato']
    assert dec['candidato']==cfg['candidato']
    assert dec['final']['threshold']==cfg['threshold']
    assert dec['final']['calibracao']=='sigmoid'
    assert dec['checks']['anos_desenvolvimento']==[2022,2023]
    assert dec['checks']['random_split'] is False
    assert dec['final']['features']==load(ML/'modelo_5b5/config.json')['features']['E_municipio']
    q=load(ML/'dataset_5b3/qualidade.json')
    assert q['completo']['linhas']==3288 and q['elegivel']['linhas']==1693
    assert q['elegivel']['positivos']==132 and q['elegivel']['negativos_condicionais']==1561
    assert q['completo']['null']==467
    assert load(ML/'cobertura_5b7/resultado.json')['totais']['null']==1022
    return checked

PHASES=[
 ('5B','Auditar viabilidade inicial','ANPC sem cobertura/overlap adequados','NO-GO','Negativos não demonstrados','RELATORIO.md'),
 ('5B.1','Prova de junção espaciotemporal','Junção retrospetiva tecnicamente viável','GO técnico / NO-GO dataset','Disponibilidade em T e cobertura não certificadas','RELATORIO_5B1.md'),
 ('5B.2','Encontrar fonte oficial','Export SGIF individual identificado','NO-GO certificado','Dicionário/completude por demonstrar','RELATORIO_5B2.md'),
 ('5B.2B','Reconciliação empírica e labels','Três municípios; 177/2644/467','GO condicionado retrospetivo','Negativos condicionais; Lisboa2024 null','RELATORIO_5B2B.md'),
 ('5B.3','Dataset reproduzível','1693 elegíveis;132 positivos;1561 negativos condicionais','GO treino experimental','Exclusões seletivas; fonte retrospetiva','dataset_5b3/RELATORIO.md'),
 ('5B.4','Benchmark temporal 2024','Sinal; degradação HGB escolhido em 2023','Sinal experimental / sem validação operacional','2024 consumido; Brier/recall insuficientes','modelo_5b4/RELATORIO.md'),
 ('5B.5','Robustez temporal e congelamento','HGB E sigmoid threshold0.15','GO apenas para preparar validação externa','Seleção em61 variantes; poucos positivos','modelo_5b5/RELATORIO.md'),
 ('PRDF','Auditar holdout2025 e compatibilidade','73 positivos potenciais/0 negativos/1022 null','NO-GO holdout','Cobertura insuficiente para zeros; mesma linhagem SGIF','prdf_auditoria/RELATORIO.md'),
 ('5B.7','Certificar cobertura adicional2025','36 blocos DUVIDOSO; redução null0','NO-GO holdout','Divergência reacendimentos; sem histórico público verificável','cobertura_5b7/RELATORIO.md'),
 ('5B.8','Fecho científico','Candidato preservado e resultados consolidados','ENCERRADO EXPERIMENTAL','Sem validação externa/operacional','fecho_5b8/RELATORIO_FINAL.md')]

def gerar():
    checked=verificar();cfg=load(OUT/'config.json');dec=load(ML/'modelo_5b5/decisao.json')
    save('integridade_historica.json',dict(inalterado=True,ficheiros=checked,metodo='SHA-256 sem desserializar joblib; comparado com manifestos históricos'))
    save('estado_modelo.json',dict(**cfg,modelo='HistGradientBoosting',features=dec['final']['features'],calibracao='sigmoid',class_weight=None,seed=42,fit_end_exclusivo=dec['final']['fit_end'],cal_end_exclusivo=dec['final']['cal_end'],versoes=load(ML/'modelo_5b5/versoes.json'),artefacto='../modelo_5b5/candidato.joblib'))
    csvsave('linha_temporal.csv',[dict(zip(['fase','objetivo','resultado','decisao','limitacao','relatorio'],r)) for r in PHASES])
    metrics=load(ML/'modelo_5b4/metricas_teste.json');table=[]
    for model,regions in metrics.items():
        r=regions['1714'];table.append(dict(modelo=model,ambito='Vila Real/2024; experiência5B.4',**{k:r[k] for k in ['n','positivos','threshold','pr_auc_ap','roc_auc','precision','recall','f1','brier','matriz']}))
    csvsave('resultados_5b4_2024.csv',table)
    selected=next(r for r in load(ML/'modelo_5b5/estabilidade.json') if r['id']==dec['candidato'])
    stats=[dict(metrica=k,**v) for k,v in selected['estatisticas'].items()]
    csvsave('resultados_5b5_rolling.csv',stats)
    q=load(ML/'dataset_5b3/qualidade.json');csvsave('dataset_resumo.csv',[dict(conjunto=k,**q[k]) for k in ['completo','elegivel','excluidos']])
    # Enumeração de metadados, sem ler os datasets raw/cache; excluir dependências locais.
    tracked=set(subprocess.check_output(['git','ls-files','experiments/ml_5b'],cwd=ROOT,text=True).splitlines())
    inv=[];small=defaultdict(list);skipped=[]
    for folder,dirs,files in os.walk(ML):
        for d in list(dirs):
            if d in ['_deps','__pycache__','.venv','venv']:
                skipped.append(str((Path(folder)/d).relative_to(ML)));dirs.remove(d)
        if Path(folder)==OUT:continue
        for name in sorted(files):
            f=Path(folder)/name;rel=f.relative_to(ML).as_posix();size=f.stat().st_size
            policy='manter_local_rever'
            if f.suffix in ['.joblib','.bin','.gpkg','.zip','.pdf','.pyc'] or size>2_000_000:policy='fora_raw_modelo_cache'
            elif f.suffix in ['.py','.md'] or name=='.gitignore':policy='candidato_versionar_codigo_documentacao'
            else:policy='rever_artefacto_resumido'
            inv.append(dict(ficheiro=rel,bytes=size,politica=policy,versionado='experiments/ml_5b/'+rel in tracked))
            if f.suffix in ['.py','.md'] and size<250_000:small[sha(f)].append(rel)
    csvsave('inventario_artefactos.csv',inv)
    save('inventario_resumo.json',dict(ficheiros=len(inv),bytes=sum(r['bytes'] for r in inv),diretorios_omitidos=skipped,duplicados_codigo_docs=[v for v in small.values() if len(v)>1],nota='Não inclui saídas autorreferentes de fecho_5b8; raw apenas stat, sem scan/conteúdo.'))
    # Allowlist concreta para revisão: não selecionar todo experiments/ml_5b recursivamente.
    safe_names={'config.json','manifesto.json','checksums.json','schema.json','qualidade.json','decisao.json','decisao_congelada.json','estabilidade.json','folds.json','composicao.json','versoes.json','metricas_teste.json','metricas_validacao.json','metricas.csv','metricas_folds.csv','drift.csv','importancia.json','coeficientes_logistica.json','importancia_validacao.json','resultado.json','holdout_futuro.json','fiabilidade.svg','entrega_checksums.json','thresholds_validacao.csv'}
    safe_dirs={'dataset_5b3','modelo_5b4','modelo_5b5'}
    review=[];excluded=[]
    for r in inv:
        rel=r['ficheiro'];parts=Path(rel).parts;name=parts[-1]
        allowed=r['politica']=='candidato_versionar_codigo_documentacao'
        if parts[0] in safe_dirs and len(parts)==2 and name in safe_names:allowed=True
        if parts[0] in {'prdf_auditoria','cobertura_5b7'} and len(parts)==2 and Path(name).suffix in {'.json','.csv'} and name!='amostras_temporais.json':allowed=True
        if r['politica']=='fora_raw_modelo_cache':allowed=False
        if allowed and not r['versionado']:review.append('experiments/ml_5b/'+rel)
        elif not allowed:excluded.append(dict(ficheiro='experiments/ml_5b/'+rel,motivo=r['politica']))
    final=['config.json','validar_fecho.py','test_fecho.py','RELATORIO_FINAL.md','README.md','limitacoes.md','estado_modelo.json','linha_temporal.csv','integridade_historica.json','resultados_5b4_2024.csv','resultados_5b5_rolling.csv','dataset_resumo.csv','inventario_artefactos.csv','inventario_resumo.json','commit_recomendado.txt','fora_commit.csv']
    review+=['experiments/ml_5b/fecho_5b8/'+n for n in final]
    (OUT/'commit_recomendado.txt').write_text('\n'.join(sorted(set(review)))+'\n',encoding='utf-8')
    csvsave('fora_commit.csv',excluded)
    return table,stats

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--gerar',action='store_true');args=p.parse_args()
    if args.gerar:gerar()
    else:print(json.dumps(dict(ficheiros_verificados=len(verificar()),estado='inalterado'),ensure_ascii=False))
