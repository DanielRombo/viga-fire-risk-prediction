"""Consolida evidência documental e agregados pequenos; sem inferência ML."""
import calendar,csv,hashlib,json
from collections import Counter
from pathlib import Path
P=Path(__file__).resolve().parent; ML=P.parent

def load(path):return json.loads(path.read_text(encoding='utf-8'))
def write(name,obj):(P/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def csvwrite(name,rows):
    with (P/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

# Classificação da evidência disponível, não da capacidade hipotética de um sistema interno.
SOURCES=[
 ('SADO_NORMA','ANEPC','https://prociv.gov.pt/media/d3rjmgs3/don_02_2025.pdf','C','SADO','primária normativa','2025','Contínua prevista; execução não auditada','Não é export','Obrigatoriedade de registo e histórico, secção 8.a, página impressa 42; não prova completude do export público.'),
 ('PROCIV_ABERTAS','ANEPC / dados.gov','https://dados.gov.pt/datasets/prociv-ocorrencias-em-aberto','B','SADO','republicação operacional','corrente','Dinâmica','Metadados 2021; 2025 completo não demonstrado','Dados de ocorrências em curso; não equivalem ao histórico completo.'),
 ('PROCIV_HIST','ANEPC','http://www.prociv.pt/_vti_bin/ARM.ANPC.UI/ANPC_SituacaoOperacional.svc/GetHistoryOccurrencesByLocation','D','SADO','endpoint antigo','não obtido','Não demonstrada','HTTP 200 HTML redirecionado para home','Não foi obtido microdado histórico; não interpretar como lista vazia.'),
 ('SGIF_EXPORT','ICNF','https://fogos.icnf.pt/download/ExportarDadosSGIF/','C','SGIF','primária exportada','2001–24/03/2026 no snapshot anterior','Não garantida; datas de ficheiro','Sem selo público de completude no diretório','Ativos e eliminados existentes; não descarregados novamente.'),
 ('SGIF_DAILY','ICNF','https://fogos.icnf.pt/download/ExportarDadosSGIF/daily_fires_summary.csv','C','SGIF','agregação da mesma fonte','amostra histórica; não inferir intervalo completo','Diária no schema','Amostra 32 KiB; não auditado integralmente','Agregado nacional com NA e métricas pós-evento; não é prova de cobertura municipal.'),
 ('SGIFR_2025','AGIF / SGIFR','https://www.sgifr.gov.pt/relatorios-anuais','C','SGIF e entidades SGIFR/ANEPC','agregação parcialmente relacionada','2025 completo no agregado anual','Anual','Relatório publicado; não certificado municipal','8252 coincidem com PRDF. Relatório PDF p.133 nota38: SGIF ~8% versus SADO 6,4% reacendimentos, harmonização em curso.'),
 ('ICNF_RP7','ICNF','https://www.icnf.pt/api/file/doc/2ddb8ceae473db04','C','SGIF','agregação da mesma fonte','01/01–30/09/2025','Relatório periódico','Provisório em 01/10/2025','Totais mensais permitem comparar versões, não provar cada dia municipal.'),
 ('INE_13512','INE','https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd=0013512&lang=PT','C','ICNF Estatísticas florestais','republicação estatística','2001–2025','Anual municipal','2025 provisório; atualização 30/05/2026','Nova consulta mantém dados anteriores; não é confirmação independente.'),
 ('INE_META','INE','https://www.ine.pt/bddXplorer/htdocs/minfo.jsp?var_cd=0013512&lingua=PT','C','ICNF Estatísticas florestais','metadados','2001–2025','Anual','Metadados consultados','Define fogo não planeado/controlado rural com supressão; não documenta completude diária.'),
 ('EFFIS','Comissão Europeia JRC','https://forest-fire.emergency.copernicus.eu/about-effis/technical-background/rapid-damage-assessment','B','MODIS/Sentinel-2/VIIRS e auxiliares','parcialmente independente','2025 e corrente','Diária/quase tempo real','Produto de área, não censo de alertas','Só fração das ocorrências; pequenos fogos podem faltar; datas não são necessariamente alerta; pode incluir fogo prescrito.'),
 ('FIRMS','NASA','https://forum.earthdata.nasa.gov/viewtopic.php?t=5178','B','MODIS/VIIRS','instrumental, partilhada com EFFIS','2025 e corrente','Passagens de satélite','Não é cadastro de ocorrências','Nuvem, duração entre passagens e intensidade podem impedir deteção. Ausência nunca certifica zero.'),
 ('PRDF','ICNF / autores PRDF','https://zenodo.org/records/21427772','C','SGIF/ICNF','harmonização','2025 até 31/12','Snapshot V2025.1','Auditado anteriormente','Fonte base, não confirmação independente; PBA/FRP auxiliares, METEO centrado no evento.'),
 ('LISBOA_RSB','Município de Lisboa','https://www.lisboa.pt/municipio/organizacao-municipal/gestao-e-avaliacao','D','RSB','potencial registo municipal relacionado','RA2024 encontrado; 2025 não demonstrado','Anual','Sem série rural diária 2025 obtida','Relatório relativo a 2024 não certifica 2025; operações de um corpo não equivalem automaticamente a todas as ocorrências municipais.'),
 ('FARO_MAPA','Município de Faro','https://mapas.cm-faro.pt/geoportal/mapa/floresta','D','Planeamento municipal','cartografia','Planeamento','Não aplicável','Não é diário de ocorrências','Limites e perigosidade não demonstram reporte de ocorrências 2025.'),
 ('VREAL_PORTAL','Município de Vila Real','https://www.cm-vilareal.pt/','B','Município / proteção civil','relato municipal','Notícias agosto 2025','Episódica','Não é censo','Notícias confirmam atividade, não ausência de eventos nem completude mensal.'),
 ('NA_MINHA_RUA','Município de Lisboa','https://dados.gov.pt/en/datasets/ocorrencias-na-minha-rua/','D','Aplicação municipal','primária outro universo','2017 em diante','Trimestral indicada','Outro target','Ocorrências de espaço público; não é censo de incêndios rurais.'),
 ('ICNF_2026','ICNF','https://www.icnf.pt/','C','SGIF','mesma fonte corrente','2026 parcial','Corrente','Provisório','Ano ainda em curso em 14/10/2026; valores dinâmicos de página não usados como contagens.'),
 ('UK_DAILY','Governo britânico / FRS','https://www.gov.uk/government/statistics/fire-statistics-incident-level-datasets/daily-incident-dataset-guidance','A','IRS/FaRDaP','independente de Portugal','2025 sujeito a corte e lacunas documentadas','Registo diário; publicação periódica','Capacidade documental candidata, não certificada aqui','Universo de intervenções definido; lacuna Suffolk documentada. Plano B apenas; unidade/tempo/taxonomia exigem nova auditoria.'),
 ('UK_OUTDOOR','Governo britânico / FRS','https://www.gov.uk/government/statistics/fire-statistics-incident-level-datasets/outdoor-fires-dataset-guidance','C','IRS/FaRDaP','mesma fonte que UK_DAILY','2025 candidato','Anual','Plano B','Outdoor não define wildfire; não substituir target português ou município desconhecido ao encoder.'),
]

def permite_zero(e):
    keys=load(P/'config.json')['condicoes_zero']
    return all(e.get(k) is True for k in keys)

def main():
    config=load(P/'config.json'); fields=['id','entidade','url','utilidade','fonte_primaria','independencia','periodo','frequencia','estado','evidencia_limite']
    sources=[dict(zip(fields,r),acesso_em=config['data_auditoria'],aplicavel_a_negativos_PT=False) for r in SOURCES]
    csvwrite('fontes.csv',sources)
    csvwrite('proveniencia.csv',[{k:r[k] for k in ['id','entidade','fonte_primaria','independencia','frequencia','estado','url','acesso_em']} for r in sources])
    ine=load(P/'evidencias/ine_atual.bin')[0];old=load(ML/'fontes_5b2/ine_13512_meta.bin')[0]
    totals={r['geodsg']:r for r in ine['Dados']['2025'] if r['dim_3']=='T' and r['geodsg'] in ['Lisboa','Faro','Vila Real','Continente']}
    write('ine_verificacao.json',dict(dados_iguais_cache=ine['Dados']==old['Dados'],atualizado_em=ine['DataUltimoAtualizacao'],totais=totals,nota='SHA do JSON muda com DataExtracao; comparar conteúdo estatístico, não só hash.'))
    with (ML/'prdf_auditoria/cobertura_2025.csv').open(encoding='utf-8',newline='') as f:base=[r for r in csv.DictReader(f) if r['municipio'] in config['municipios']]
    matrix=[]
    for r in base:
        evidence={k:False for k in config['condicoes_zero']}
        evidence.update(universo_operacional=True,inclui_rurais=True,municipio_coberto=True)
        assert not permite_zero(evidence)
        matrix.append(dict(municipio=r['municipio'],nome=r['nome'],mes=r['mes'],inicio=f"2025-{int(r['mes']):02d}-01",prdf_ficheiro_ano_disponivel=True,prdf_ocorrencias_mes=int(r['n_ocorrencias']),sgif_snapshot_ano_disponivel=True,sgif_mes_verificado_independentemente=False,anepc_historico_2025_obtido=False,anepc_obrigacao_registo=True,ine_anual_disponivel=True,ine_total_ano=int(totals[r['nome']]['valor']),outra_fonte='SGIFR agregado anual',cobertura_diaria_demonstrada=False,cobertura_mensal_demonstrada=False,estado_fonte='INE provisório; SGIFR anual publicado',inconsistencias='Reacendimentos SGIF/SADO não harmonizados; completude export não demonstrada',decisao='DUVIDOSO',positivos_potenciais=int(r['positivos_potenciais']),negativos_condicionais_potenciais=0,null=int(r['null']),janelas=int(r['janelas']),evidencias='SADO_NORMA;SGIF_EXPORT;SGIFR_2025;INE_13512;PROCIV_HIST'))
    for r in matrix:
        month=int(r['mes']);r['fim']=f"2025-{month:02d}-{calendar.monthrange(2025,month)[1]}"
    csvwrite('matriz_cobertura_2025.csv',matrix)
    summaries=[]
    for code,name in config['municipios'].items():
        rows=[r for r in matrix if r['municipio']==code]
        summaries.append(dict(municipio=code,nome=name,**{k:sum(r[k] for r in rows) for k in ['positivos_potenciais','negativos_condicionais_potenciais','null','janelas']}))
    csvwrite('contagens_municipais.csv',summaries)
    monthly=[dict(mes=m,**{k:sum(r[k] for r in matrix if int(r['mes'])==m) for k in ['positivos_potenciais','negativos_condicionais_potenciais','null','janelas']}) for m in range(1,13)]
    csvwrite('contagens_mensais.csv',monthly)
    write('resultado.json',dict(decisao='NO-GO',regra='Não converter null sem prova de cobertura e compatibilidade',estados=dict(Counter(r['decisao'] for r in matrix)),totais={k:sum(r[k] for r in matrix) for k in ['positivos_potenciais','negativos_condicionais_potenciais','null','janelas']},reducao_null=0,periodos_elegiveis=[]))
    fog=load(ML/'prdf_auditoria/fogos.json')['ano2025']['meses']
    published=[95,32,331,254,444,1179,2121,2285,991]
    csvwrite('reconciliacao_mensal.csv',[dict(mes=m,prdf=int(fog[str(m)]),icnf_provisorio_20251001=n,diferenca_prdf_menos_publicado=int(fog[str(m)])-n,diferenca_percentual=100*(int(fog[str(m)])-n)/n,fonte='ICNF_RP7',causa='Versões/taxonomias não reconciliadas por IDs; não atribuir automaticamente a lacunas') for m,n in enumerate(published,1)])
    csvwrite('reconciliacao_anual.csv',[dict(territorio='Continente',fonte='SGIFR_2025',prdf=8252,oficial=8252,diferenca=0,independente=False),dict(territorio='Continente',fonte='INE_13512',prdf=8252,oficial=int(totals['Continente']['valor']),diferenca=8252-int(totals['Continente']['valor']),independente=False)]+[dict(territorio=name,fonte='INE_13512',prdf=n,oficial=int(totals[name]['valor']),diferenca=n-int(totals[name]['valor']),independente=False) for name,n in [('Lisboa',1),('Faro',32),('Vila Real',68)]])
    inputs=[ML/'prdf_auditoria/cobertura_2025.csv',ML/'prdf_auditoria/fogos.json',P/'config.json',P/'evidencias/ine_atual.bin']
    write('manifesto_inputs.json',[dict(ficheiro=str(f.relative_to(ML)),bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in inputs])

if __name__=='__main__':main()
