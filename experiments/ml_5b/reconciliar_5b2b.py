"""Reconciliação empírica; acordo anual não é certificação diária independente."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from obter_5b2b import ROOT

FONTES=ROOT.parent/'fontes_5b2'

def gravar(nome,rows):
    if not rows:return
    with (ROOT/nome).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def classificar(total,oficial,flag,anual_anomalo=False):
    if oficial is None:return 'sem evidencia'
    if flag or anual_anomalo:return 'duvidosa'
    if total==oficial:return 'aceitavel'
    # Sem razão documentada ao nível do bloco, não absorver divergência numa tolerância.
    return 'duvidosa'

def main():
    ine=json.loads((FONTES/'ine_2018_2024.bin').read_text(encoding='utf-8'))[0]
    oficiais={};nomes={};nacionais={}
    for ano,rows in ine['Dados'].items():
        for r in rows:
            geo=r['geocod']
            if geo=='1' and r['dim_3']=='T':nacionais[int(ano)]=int(r['valor'])
            if len(geo)!=7:continue
            cod=geo[-4:];nomes[cod]=r['geodsg']
            key=(cod,int(ano),r['dim_3'])
            assert key not in oficiais
            oficiais[key]=(int(r['valor']) if r.get('valor','').isdigit() else None,r.get('sinal_conv',''))
    anuais=Counter();mensais=Counter();candidatos=Counter();exclusoes=Counter();nacion=Counter();problemas=Counter()
    with (ROOT/'consolidado.csv').open(encoding='utf-8') as f:
        for r in csv.DictReader(f):
            y=int(r['DHInicio'][:4]);m=int(r['DHInicio'][5:7]);cod=r['municipio']
            if not 2018<=y<=2024:continue
            anuais[cod,y]+=1;mensais[cod,y,m]+=1;nacion[y]+=1
            if r['motivo']=='candidato':candidatos[cod,y,m]+=1
            elif r['motivo'] not in ('reacendimento','tipo_nao_elegivel'):problemas[cod,y]+=1
            exclusoes[cod,y,r['motivo']]+=1
    anu=[];matriz=[]
    adm=set()
    with (FONTES/'sgif_administracao.bin').open(encoding='utf-8-sig') as f:
        adm={r['DTCC'] for r in csv.DictReader(f)}
    for cod in sorted(nomes):
        for y in range(2018,2025):
            oficial,flag=oficiais.get((cod,y,'T'),(None,''))
            outros=[anuais[cod,z] for z in range(2018,2025) if z!=y]
            quebra=anuais[cod,y]==0 and median(outros)>=5
            estado=classificar(anuais[cod,y],oficial,flag or problemas[cod,y],quebra)
            if cod not in adm:estado='sem evidencia'
            delta=None if oficial is None else anuais[cod,y]-oficial
            anu.append(dict(municipio=cod,nome=nomes[cod],ano=y,total_export=anuais[cod,y],total_ine=oficial,
                            diferenca=delta,diferenca_absoluta=None if delta is None else abs(delta),
                            diferenca_percentual=None if not oficial else 100*delta/oficial,
                            reacendimentos_export=exclusoes[cod,y,'reacendimento'],
                            reacendimentos_ine=oficiais.get((cod,y,'4'),(None,''))[0],
                            anomalia_ano_vazio=quebra,problemas=problemas[cod,y],coverage_status=estado))
            for m in range(1,13):
                hist=[mensais[cod,z,m] for z in range(2018,2025) if z!=y]
                base=median(hist);n=mensais[cod,y,m]
                alerta=''
                if n==0 and base>=5:alerta='zero_contra_mediana_historica_5_ou_mais'
                if n>=20 and n>5*max(base,1):alerta='pico_acima_5x_mediana_e_20_eventos'
                # Alertas são triagem, não prova de ausência/falha. Retêm null até revisão.
                e='duvidosa' if alerta else estado
                matriz.append(dict(municipio=cod,nome=nomes[cod],ano=y,mes=m,total_export=n,
                                   candidatos=candidatos[cod,y,m],total_oficial_mensal=None,
                                   coverage_status=e,base_cobertura='reconciliacao_anual_INE',
                                   anomalia=alerta,mediana_outros_anos=base))
    gravar('reconciliacao_anual.csv',anu);gravar('matriz_mensal.csv',matriz)
    gravar('reconciliacao_nacional.csv',[dict(ano=y,total_export=nacion[y],total_ine=nacionais[y],
        diferenca=nacion[y]-nacionais[y],diferenca_percentual=100*(nacion[y]-nacionais[y])/nacionais[y]) for y in range(2018,2025)])
    cat=json.loads((ROOT.parent/'auditoria_5b2/municipios_catalogo.json').read_text(encoding='utf-8'))
    codes={r['codigos_candidatos'][0] for r in cat if len(r['codigos_candidatos'])==1}
    resumo=dict(anos_estados=dict(Counter(r['coverage_status'] for r in anu)),
                meses_estados=dict(Counter(r['coverage_status'] for r in matriz)),
                catalogo_anos=dict(Counter(r['coverage_status'] for r in anu if r['municipio'] in codes)),
                alertas=sum(bool(r['anomalia']) for r in matriz),
                nota='INE republica fonte ICNF: controlo externo de publicação, não captura independente de eventos.')
    (ROOT/'reconciliacao_resumo.json').write_text(json.dumps(resumo,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(resumo,indent=2))
    print([r for r in anu if r['municipio'] in ('1106','0805','1714','0303','0603')])

if __name__=='__main__':main()
