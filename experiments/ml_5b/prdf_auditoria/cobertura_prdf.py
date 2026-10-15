"""Reconciliação e estimativas agregadas, sem dataset final ou previsões."""
import bisect
import csv
import hashlib
import json
from collections import Counter,defaultdict
from datetime import datetime,date,timedelta,timezone
from zoneinfo import ZoneInfo
from auditar_prdf import OUT,ML,DATA,ro,guardar,csvout,rural,municipio,dt

def main():
    ine=json.loads((ML/'fontes_5b2/ine_13512_meta.bin').read_text(encoding='utf-8'))[0]
    oficiais={r['geocod'][-4:]:r for r in ine['Dados']['2025'] if len(r['geocod'])==7 and r.get('dim_3')=='T'}
    adm=defaultdict(set);municipios=set()
    with (ML/'fontes_5b2/sgif_administracao.bin').open(encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):adm[r['INE'].zfill(6)].add((r['DTCC'],r['Concelho'],r['Distrito']));municipios.add(r['DTCC'])
    c=ro('fogos.gpkg');c.row_factory=__import__('sqlite3').Row
    raw=[dict(r) for r in c.execute('SELECT Codigo,Tipo,TipoCausa,CodCausa,Reacendimento_IncendioPai,DHInicio,DH1Intervencao,DHResolucao,DHConclusao,DHFim,INE,Concelho,Distrito,Lat_4326,Lon_4326 FROM Fogos WHERE Ano=2025 OR substr(DHInicio,1,10)=\'2026-01-01\'')]
    months=Counter();annual=Counter();names={};quality=Counter();candidates=defaultdict(list);tax=Counter();blocks=defaultdict(list)
    conflicts={}
    if (OUT/'territorio_2025_amostra.csv').exists():
        with (OUT/'territorio_2025_amostra.csv').open(encoding='utf-8') as f:
            for r in csv.DictReader(f):
                if r['coerente']=='False':conflicts[r['codigo']]=set(filter(None,[r['municipio'],*r['municipios_poligono'].split('|')]))
    lis=ZoneInfo('Europe/Lisbon');utc=timezone.utc;times=defaultdict(lambda:[[],[]])
    for r in raw:
        d=dt(r['DHInicio']);cod=municipio(r['INE']);names[cod]=r['Concelho'];is2025=d.year==2025
        if is2025:annual[cod]+=1;months[cod,d.month]+=1;tax[rural(r)]+=1
        try:key=str(int(r['INE'])).zfill(6)
        except (ValueError,TypeError):key=''
        matches=adm.get(key,set())
        territorial=len(matches)==1 and next(iter(matches))==(cod,r['Concelho'],r['Distrito'])
        if is2025:
            quality['codigo_nome_incompativel']+=not territorial
            for k in ('DH1Intervencao','DHResolucao','DHConclusao','DHFim'):
                o=dt(r[k]);quality[k+'_null']+=o is None
                if o:quality[k+'_dia_anterior_alerta']+=o.date()<d.date()
        local=d.replace(tzinfo=lis,fold=0).astimezone(utc);u=d.replace(tzinfo=utc)
        ambiguous=d.replace(tzinfo=lis,fold=0).utcoffset()!=d.replace(tzinfo=lis,fold=1).utcoffset()
        if not territorial or ambiguous or r['Codigo'] in conflicts:
            for cc in conflicts.get(r['Codigo'],{cod}):blocks[cc].extend([local,u])
            continue
        if rural(r)!='potencial_nova_ocorrencia':continue
        times[cod][0].append(local);times[cod][1].append(u)
    for rr in times.values():rr[0].sort();rr[1].sort()
    for arr in blocks.values():arr.sort()
    reconcile=[];coverage=[];summary=defaultdict(Counter)
    for cod in sorted(set(oficiais)|municipios):
        off=oficiais.get(cod);total=int(off['valor']) if off and off.get('valor','').isdigit() else None
        provisional=off.get('sinal_conv','') if off else None
        if cod not in municipios or total is None:status='SEM_EVIDÊNCIA'
        elif provisional or total!=annual[cod]:status='DUVIDOSO'
        else:status='ACEITÁVEL'
        reconcile.append(dict(municipio=cod,nome=names.get(cod,off.get('geodsg','') if off else ''),prdf=annual[cod],ine=total,
            diferenca=None if total is None else annual[cod]-total,marcador=provisional,coverage_status=status))
        for day in range(365):
            t=datetime(2025,1,1,15,tzinfo=utc)+timedelta(days=day);fim=t+timedelta(days=1)
            n1,n2=[bisect.bisect_right(arr,fim)-bisect.bisect_right(arr,t) for arr in times[cod]]
            uncertain=bisect.bisect_right(blocks[cod],fim+timedelta(hours=2))-bisect.bisect_right(blocks[cod],t-timedelta(hours=2))>0
            k=(cod,t.month);a=summary[k];a['janelas']+=1
            if n1 and n2:a['positivos_potenciais']+=1
            elif n1!=0 or n2!=0 or uncertain:a['null']+=1
            elif status in ('FORTE','ACEITÁVEL') and fim.year==2025:a['negativos_condicionais_potenciais']+=1
            else:a['null']+=1
        for month in range(1,13):
            s=summary[cod,month]
            coverage.append(dict(municipio=cod,nome=reconcile[-1]['nome'],mes=month,coverage_status=status,n_ocorrencias=months[cod,month],
                positivos_potenciais=s['positivos_potenciais'],negativos_condicionais_potenciais=s['negativos_condicionais_potenciais'],null=s['null'],janelas=s['janelas'],
                motivo='Universo não demonstrado' if status=='SEM_EVIDÊNCIA' else 'INE provisório ou divergência; sem certificação mensal independente' if status=='DUVIDOSO' else 'Reconciliação anual não provisória; carece revisão mensal'))
    csvout('reconciliacao_2025.csv',reconcile);csvout('cobertura_2025.csv',coverage)
    old=json.loads((ML/'cobertura_5b2b/auditoria.json').read_text(encoding='utf-8'))
    subgroup={}
    for cod in ('1106','0805','1714'):
        subgroup[cod]=dict(nome=names.get(cod),ocorrencias=annual[cod],**{k:sum(r[k] for r in coverage if r['municipio']==cod) for k in ('positivos_potenciais','negativos_condicionais_potenciais','null','janelas')})
    guardar('cobertura_resumo.json',dict(n_municipios=len(reconcile),estados=dict(Counter(r['coverage_status'] for r in coverage)),
        totais={k:sum(r[k] for r in coverage) for k in ('positivos_potenciais','negativos_condicionais_potenciais','null','janelas')},
        municipios_piloto=subgroup,qualidade2025=dict(quality),taxonomia2025=dict(tax),
        comparacao_sgif_global=dict(sgif2025=old['anos']['2025'],prdf2025=sum(annual.values()),nota='Total previamente auditado; não recarregado export nem demonstrada identidade linha a linha de 2025.'),
        reconciliacao=dict(iguais=sum(r['diferenca']==0 for r in reconcile),divergentes=sum(r['diferenca'] is not None and r['diferenca']!=0 for r in reconcile)),
        decisao='NO-GO: sem blocos com cobertura não provisória demonstrada para negativos',
        nota='Apenas estimativas agregadas; não guarda labels diários. Existência positiva não certifica completude.'))
    c.close();print(subgroup,flush=True)

if __name__=='__main__':main()
