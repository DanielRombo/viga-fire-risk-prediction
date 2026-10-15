"""Consolidação local e diagnóstico integral SGIF; nenhum acesso à BD VIGA."""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from obter_5b2b import ROOT, sha

def ler(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f,strict=True)
        for n,r in enumerate(reader,2):
            if None in r or any(v is None for v in r.values()):raise ValueError(f'Linha malformada {n}')
            yield n,r

def data(s):
    try:return datetime.fromisoformat(s) if s else None
    except ValueError:return None

def main():
    for nome in ('Data2001_now','Data2001_noweliminados'):
        p=ROOT/(nome+'.csv');m=json.loads(p.with_suffix('.manifesto.json').read_text())
        assert sha(p)==m['sha256'] and p.stat().st_size==m['bytes']
    adm=ROOT.parent/'fontes_5b2/sgif_administracao.bin'
    mapa=defaultdict(set)
    for _,r in ler(adm):mapa[r['INE'].zfill(6)].add((r['DTCC'],r['Distrito'],r['Concelho']))
    excluidos=defaultdict(list);motivos=Counter()
    for n,r in ler(ROOT/'Data2001_noweliminados.csv'):
        excluidos[r['Codigo']].append(r['EstadoRegisto']);motivos[r['EstadoRegisto']]+=1
    enums={k:Counter() for k in ('Tipo','EstadoRegisto','ClassificacaoRegisto','Reacendimentos')}
    anos=Counter();meses=Counter();validos=Counter();mot=Counter();qual=Counter();ids={};sados=Counter();instantes=Counter()
    geograf=Counter();tempor=Counter();amostras=[]
    campos=['linha','Codigo','CodigoSado','DHInicio','municipio','Distrito','Concelho','Tipo','motivo',
            'territory_confidence','Lat_4326','Lon_4326','Reacendimento_IncendioPai']
    with (ROOT/'consolidado.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=campos);writer.writeheader()
        for n,r in ler(ROOT/'Data2001_now.csv'):
            if n%100000==0:print(n,'registos lidos',flush=True)
            for k,c in enums.items():c[r[k]]+=1
            t=data(r['DHInicio']);qual['total']+=1
            if t:
                anos[t.year]+=1;tempor['data_valida']+=1
                tempor['sem_fuso']+=int(t.tzinfo is None)
                tempor['minuto_00']+=int(t.minute==0);tempor['minuto_multiplo_5']+=int(t.minute%5==0)
                tempor['segundo_00']+=int(t.second==0)
                tempor['ano_incoerente']+=int(str(t.year)!=r['Ano'])
                tempor['dia_incoerente']+=int(str(t.day)!=r['Dia'])
                tempor['mes_incoerente']+=int(str(t.month)!=r['Mes'])
                tempor['hora_incoerente']+=int(str(t.hour)!=r['Hora'])
                for campo in ('DH1Intervencao','DHResolucao','DHConclusao','DHFim'):
                    outro=data(r[campo])
                    if outro and outro.tzinfo==t.tzinfo and outro<t:tempor[campo+'_anterior_inicio']+=1
            else:tempor['data_invalida']+=1
            codigo=r['Codigo'];finger=hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()
            repetido=codigo in ids
            if repetido:qual['id_repetido_identico' if ids[codigo]==finger else 'id_repetido_divergente']+=1
            ids[codigo]=finger
            if r['CodigoSado']:sados[r['CodigoSado']]+=1
            matches=mapa.get(r['INE'].zfill(6),set());municipio='';conf='baixa'
            if len(matches)==1:
                municipio,dist,conc=next(iter(matches))
                if conc.casefold()==r['Concelho'].casefold() and dist.casefold()==r['Distrito'].casefold():conf='media'
                else:geograf['codigo_nome_incompativel']+=1
            else:geograf['codigo_ausente_ambiguo']+=1
            try:
                lat=float(r['Lat_4326']);lon=float(r['Lon_4326'])
                if not(math.isfinite(lat) and math.isfinite(lon) and 36.8<=lat<=42.2 and -9.6<=lon<=-6):
                    conf='baixa';geograf['coordenada_invalida_ou_fora_envelope']+=1
            except ValueError:conf='baixa';geograf['coordenada_ausente']+=1
            # Envelope apenas diagnóstico numérico; não certifica fronteira/município.
            motivo='candidato'
            if codigo in excluidos:motivo='export_eliminados'
            elif repetido:motivo='id_repetido'
            elif r['Tipo'] not in ('Florestal','Agrícola'):motivo='tipo_nao_elegivel'
            elif r['Reacendimento_IncendioPai'] or r['Reacendimentos'] not in ('','0') or r['CodCausa']=='711':motivo='reacendimento'
            elif not t:motivo='timestamp_invalido'
            elif conf=='baixa':motivo='territorio_incerto'
            mot[motivo]+=1
            if t:
                meses[(municipio,r['Distrito'],r['Concelho'],t.year,t.month)]+=1
                instantes[(municipio,r['DHInicio'])]+=1
                if motivo=='candidato':validos[(municipio,r['Distrito'],r['Concelho'],t.year,t.month)]+=1
            writer.writerow({**{k:r[k] for k in campos if k in r},'linha':n,'municipio':municipio,'motivo':motivo,'territory_confidence':conf})
    resumo=dict(qualidade=dict(qual),tipos={k:dict(v) for k,v in enums.items()},anos=dict(sorted(anos.items())),
                exclusoes=dict(mot),eliminados=sum(motivos.values()),ids_eliminados=len(excluidos),motivos_eliminados=dict(motivos),
                ids_partilhados_eliminados=len(set(ids)&set(excluidos)),
                codigos_sado_repetidos=sum(v>1 for v in sados.values()),
                timestamps_municipais_repetidos=sum(v>1 for v in instantes.values()),
                temporal=dict(tempor),territorio=dict(geograf))
    (ROOT/'auditoria.json').write_text(json.dumps(resumo,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (ROOT/'mensal.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['municipio','distrito','concelho','ano','mes','total_export','candidatos'])
        for key,n in sorted(meses.items()):w.writerow([*key,n,validos[key]])
    print(json.dumps(resumo,ensure_ascii=True,indent=2),flush=True)

if __name__=='__main__':main()
