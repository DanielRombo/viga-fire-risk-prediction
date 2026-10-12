"""Cobertura observada não é cobertura certificada. Não gera negativos."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from auditar import ROOT, OUT, data, norm, numero, sha

INCLUIR = {'riscos mistos / incendios rurais / povoamento florestal',
           'riscos mistos / incendios rurais / mato',
           'riscos mistos / incendios rurais / agricola'}


def dias(inicio, fim):
    while inicio <= fim:
        yield inicio
        inicio += timedelta(days=1)


def main():
    destino = OUT/'fase1'; destino.mkdir(exist_ok=True)
    cat = [r for r in json.loads((ROOT/'backend/data/regioes_principais.json').read_text(encoding='utf-8')) if r['recolha_automatica']]
    chave = {(norm(r['distrito']), norm(r['nome'])): r for r in cat}
    distritos_validos = {norm(r['distrito']) for r in cat if r['distrito'] not in ('Madeira','Açores')}
    diario, rural, nacional = Counter(), Counter(), Counter()
    municipios, natureza, estados, formatos = Counter(), Counter(), Counter(), Counter()
    geo = defaultdict(Counter)
    vistos, duplicados, fontes, invalidas = {}, [], [], []
    piloto = []
    total = elegiveis = sem_municipio = divergencia_nome_distrito = 0
    estados_rurais = Counter()
    rurais_excluidos_falso = 0
    for p in sorted((ROOT/'ml/notebooks').glob('anpc-*.csv')):
        digest = sha(p)
        with p.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for linha, r in enumerate(reader, 2):
                total += 1
                identificador = r['Numero']
                assinatura = hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()
                if identificador:
                    if identificador in vistos:
                        duplicados.append({'ficheiro': p.name, 'linha': linha, 'anterior': vistos[identificador][1],
                                           'identico': vistos[identificador][0] == assinatura})
                    else:
                        vistos[identificador] = assinatura, {'ficheiro': p.name, 'linha': linha}
                try:
                    dt = datetime.fromisoformat(r['DataOcorrencia'])
                except ValueError:
                    dt = data(r['DataOcorrencia'])
                if dt is None:
                    invalidas.append({'ficheiro': p.name, 'linha': linha, 'data_texto': r['DataOcorrencia']})
                else:
                    nacional[dt.date()] += 1
                formatos['ISO' if 'T' in r['DataOcorrencia'] else 'civil_sem_offset'] += 1
                k = (norm(r['Distrito']), norm(r['Concelho']))
                municipios[k] += 1
                if not all(k): sem_municipio += 1
                nat = norm(r['Natureza'])
                natureza[r['Natureza']] += 1
                estados[r['EstadoOcorrencia']] += 1
                if nat in INCLUIR: estados_rurais[r['EstadoOcorrencia']] += 1
                falso = norm(r['EstadoOcorrencia']) in ('falso alarme','falso alerta')
                rurais_excluidos_falso += nat in INCLUIR and falso
                selecionada = nat in INCLUIR and not falso
                elegiveis += selecionada
                if k in chave and dt:
                    diario[k,dt.date()] += 1
                    rural[k,dt.date()] += selecionada
                elif k[1] in {norm(x['nome']) for x in cat}:
                    divergencia_nome_distrito += 1
                lat, lon = numero(r['Latitude']), numero(r['Longitude'])
                if lat is None or lon is None:
                    geo[k]['ausentes_ou_nao_numericas'] += 1
                elif not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat,lon)==(0,0):
                    geo[k]['invalidas_ou_zero_zero'] += 1
                elif not (36 <= lat <= 43 and -10 <= lon <= -6):
                    geo[k]['fora_caixa_continente_apenas_triagem'] += 1
                else:
                    geo[k]['na_caixa_sem_validacao_poligonal'] += 1
                if k in chave and chave[k]['nome'] in ('Lisboa','Vila Real') and selecionada and dt and date(2019,7,1) <= dt.date() <= date(2019,8,1):
                    piloto.append({'municipio': chave[k]['nome'], 'data_local_sem_fuso_confirmado': dt.isoformat(),
                                   'natureza': r['Natureza'], 'origem': p.name, 'linha': linha,
                                   'id_hash': hashlib.sha256(identificador.encode()).hexdigest()})
        assert sha(p) == digest
        fontes.append({'ficheiro': p.relative_to(ROOT).as_posix(), 'sha256': digest, 'campos': reader.fieldnames})
    inicio, fim = date(2016,1,1), date(2020,12,31)
    with (destino/'cobertura_diaria.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['data_civil_naive','ponto','ocorrencias_todas','rurais_provisorias','cobertura_certificada'])
        for d in dias(inicio,fim):
            w.writerow([d,'NACIONAL',nacional[d],'','nao'])
            for k,r in chave.items():w.writerow([d,r['nome'],diario[k,d],rural[k,d],'nao'])
    territorios=[]
    for k,r in chave.items():
        datas=[d for (kk,d),n in diario.items() if kk==k and n]
        territorios.append({**r,'municipio_proposto':r['nome'],'associacao':'distrito+concelho normalizados; sem código municipal nem validação poligonal',
            'registos_todas_naturezas':municipios[k], 'rurais_provisorios_com_data':sum(n for (kk,d),n in rural.items() if kk==k),
            'primeiro_dia':min(datas).isoformat() if datas else None,'ultimo_dia':max(datas).isoformat() if datas else None,
            'dias_com_algum_registo':len(datas),'coordenadas_ocorrencias':dict(geo[k]),'negativos_certificados':None})
    resultado={'total':total,'rurais_provisorios':elegiveis,'taxonomia_incluida':sorted(INCLUIR),
        'rurais_estados_antes_exclusao_falsos':dict(estados_rurais),'rurais_excluidos_falso_alarme_alerta':rurais_excluidos_falso,
        'naturezas':dict(natureza),'estados':dict(estados),'formatos':dict(formatos),'fontes':fontes,
        'datas_invalidas':invalidas,'duplicados':duplicados,'sem_municipio_ou_distrito':sem_municipio,
        'nome_catalogo_com_distrito_divergente_ou_data_invalida':divergencia_nome_distrito,
        'municipios_observados_distintos':len([k for k in municipios if all(k)]),
        'pares_distrito_concelho_suspeitos':[{'distrito':k[0],'concelho':k[1],'registos':n} for k,n in municipios.items() if k[0] not in distritos_validos or k[1] in ('','0')],
        'municipios_observados_sem_ponto':[{'distrito':k[0],'concelho':k[1],'registos':n} for k,n in sorted(municipios.items()) if all(k) and k not in chave],
        'dias_nacionais_sem_registos':[d.isoformat() for d in dias(inicio,fim) if not nacional[d]],
        'dias_nacionais_vazios_dentro_extremos':[d.isoformat() for d in dias(min(nacional),max(nacional)) if not nacional[d]],
        'pontos':territorios, 'cobertura_certificada':False}
    for nome,obj in [('auditoria.json',resultado),('ocorrencias_piloto.json',piloto)]:
        (destino/nome).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'total':total,'rurais_provisorios':elegiveis,'eventos_piloto':len(piloto),
                      'municipios_observados':resultado['municipios_observados_distintos'],
                      'dias_nacionais_vazios_internos':len(resultado['dias_nacionais_vazios_dentro_extremos']),
                      'duplicados':duplicados},ensure_ascii=True,indent=2))


if __name__=='__main__': main()
