"""Dataset retrospetivo isolado. Apenas ficheiros locais; sem rede, treino ou BD."""
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO/'backend'), str(REPO/'experiments/fwi_fase8')]
from convergencia import calcular, SEMENTES, INDICES, ATOL, RTOL
from services.meteorologia_fwi import (
    AmostraHorariaFWI, TerritorioFWI, UNIDADES_FWI, preparar_observacao_diaria,
)

BASE = REPO/'experiments/ml_5b'
OUT = BASE/'dataset_5b3'
FONTES = REPO/'experiments/fwi_fase8/evidencias'
PONTOS = [('1106','Lisboa',38.7169,-9.1399), ('0805','Faro',37.0194,-7.9322),
          ('1714','Vila Real',41.3006,-7.7457)]
INICIO = date(2021,10,1)
FIM = date(2024,12,31)


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def json_out(nome, valor):
    (OUT/nome).write_text(json.dumps(valor,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def csv_out(nome, rows):
    assert rows, nome
    with (OUT/nome).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def resumo(rows):
    c=Counter(str(r['target_24h']) if r['target_24h']!='' else 'null' for r in rows)
    return dict(linhas=len(rows),positivos=c['1'],negativos_condicionais=c['0'],null=c['null'],
                prevalencia=c['1']/(c['1']+c['0']) if c['1']+c['0'] else None)


def motivos_exclusao(row):
    motivos=[]
    if row['target_24h']=='':motivos.append('target_null')
    if row['coverage_status'] not in ('aceitavel','forte'):motivos.append('cobertura_nao_aceitavel')
    if row['territory_confidence'] not in ('alta','media'):motivos.append('territorio_incerto')
    if not row['fwi_sementes_convergentes']:motivos.append('sensibilidade_semente')
    # Nenhum horizonte de treino atravessa a fronteira do ano/split seguinte.
    if (datetime.fromisoformat(row['data_T'])+timedelta(days=1)).year != int(row['ano']):
        motivos.append('horizonte_atravessa_split')
    return motivos


def main():
    OUT.mkdir(exist_ok=True)
    fontes={}
    def registar(p):
        fontes[str(p.relative_to(REPO))]=dict(bytes=p.stat().st_size,sha256=sha(p))
    # O dataset depende do conteúdo exato da auditoria anterior, não apenas do nome.
    anterior=BASE/'cobertura_5b2b'
    for m in json.loads((anterior/'integridade_final.json').read_text(encoding='utf-8')):
        p=anterior/m['nome'];assert p.stat().st_size==m['bytes'] and sha(p)==m['sha256'],str(p)
    for nome in ('labels.csv','consolidado.csv','matriz_mensal.csv','territorio_piloto.csv',
                 'Data2001_now.csv','Data2001_noweliminados.csv','amostra_contraprova.json'):
        registar(anterior/nome)
    for nome in ('sgif_administracao','ine_2018_2024','dgt_1106','dgt_0805','dgt_1714'):
        p=BASE/'fontes_5b2'/f'{nome}.bin'
        m=json.loads(p.with_suffix('.json').read_text(encoding='utf-8'))
        assert sha(p)==m['sha256'] and p.stat().st_size==m['bytes'];registar(p)
    with (anterior/'labels.csv').open(encoding='utf-8') as f:
        labels={(r['municipio'],r['data_T'][:10]):r for r in csv.DictReader(f)}
    rows=[];meteorologia=[];conv=SEMENTES.index((85.,6.,15.))
    for cod,nome,lat,lon in PONTOS:
        meta=json.loads((FONTES/f'{nome}_recolha.json').read_text(encoding='utf-8'))
        bruto=FONTES/f'{nome}_extensao_resposta.json';assert sha(bruto)==meta['sha256']
        raw=json.loads(bruto.read_text(encoding='utf-8'));params=meta['parametros']
        assert params['models']=='ecmwf_ifs' and (params['latitude'],params['longitude'])==(lat,lon)
        assert raw['utc_offset_seconds']==0
        assert raw['hourly_units']=={'time':'iso8601','temperature_2m':'°C','relative_humidity_2m':'%',
                                     'wind_speed_10m':'km/h','precipitation':'mm'}
        for p in (bruto,FONTES/f'{nome}_recolha.json',FONTES/f'{nome}_horas.json',FONTES/f'{nome}_5anos.npz'):
            registar(p)
        hraw=raw['hourly'];lookup={t:i for i,t in enumerate(hraw['time'])}
        assert len(lookup)==len(hraw['time'])
        horas=json.loads((FONTES/f'{nome}_horas.json').read_text(encoding='utf-8'))
        obs=[];n=(FIM-INICIO).days+1
        for k in range(n):
            d=INICIO+timedelta(days=k);hs=horas[k*24:(k+1)*24];assert len(hs)==24
            for h in hs:
                t=datetime.fromisoformat(h['instante_utc']);i=lookup[t.strftime('%Y-%m-%dT%H:%M')]
                assert (h['latitude_consultada'],h['longitude_consultada'])==(lat,lon)
                for hk,rk in [('temperatura','temperature_2m'),('humidade','relative_humidity_2m'),
                              ('vento','wind_speed_10m'),('precipitacao_hora','precipitation')]:
                    assert h[hk]==hraw[rk][i] and np.isfinite(h[hk])
                assert -90<=h['temperatura']<=60 and 0<=h['humidade']<=100
                assert h['vento']>=0 and h['precipitacao_hora']>=0
            o=preparar_observacao_diaria(id_regiao=meta['regiao']['id_regiao'],data_referencia=d,
                territorio=TerritorioFWI.CONTINENTE,latitude=lat,
                amostras=[AmostraHorariaFWI(datetime.fromisoformat(h['instante_utc']),h['precipitacao_hora'],
                    h['temperatura'],h['humidade'],h['vento']) for h in hs],
                unidades=UNIDADES_FWI,origem='open-meteo-archive-ecmwf-ifs-horario-v1')
            ob=asdict(o);ob['data_referencia']=d.isoformat();ob['instante_referencia_utc']=o.instante_referencia_utc.isoformat();obs.append(ob)
        valores=calcular(obs,SEMENTES)
        assert np.isfinite(valores).all() and (valores>=0).all()
        # Controlo causal: prefixo sem dados posteriores vs sequência previamente validada.
        antigo=np.load(FONTES/f'{nome}_5anos.npz')
        assert np.array_equal(antigo['sementes'],np.array(SEMENTES))
        assert np.allclose(valores,antigo['valores'][:n],atol=ATOL,rtol=RTOL)
        spread=np.ptp(valores,axis=1);scale=np.max(np.abs(valores),axis=1)
        convergentes=np.all(spread<=ATOL+RTOL*scale,axis=1)
        for k,o in enumerate(obs):
            if o['data_referencia']<'2022-01-01':continue
            lab=labels[cod,o['data_referencia']];t=datetime.fromisoformat(lab['data_T'])
            ref=datetime.fromisoformat(o['instante_referencia_utc']);assert ref<=t
            # Labels não são features: listas explícitas no schema, sem inferência automática.
            row={**lab,'ano':t.year,'latitude':lat,'longitude':lon,
                 **{f:o[f] for f in ('temperatura','humidade','vento','precipitacao_24h')},
                 **dict(zip(INDICES,map(float,valores[k,conv]))),
                 'mes':t.month,'dia_do_ano':t.timetuple().tm_yday,'dia_da_semana':t.weekday(),
                 'epoca_ano':('inverno' if t.month in (12,1,2) else 'primavera' if t.month in (3,4,5) else 'verao' if t.month in (6,7,8) else 'outono'),
                 'instante_referencia_utc':ref.isoformat(),
                 'precipitacao_inicio_exclusivo_utc':(ref-timedelta(days=1)).isoformat(),
                 'available_at_historico':'','tipo_estudo':'retrospetivo',
                 'estado_fwi':'reconstruido','fwi_metodo':'xclim-0.62.0-cffdrs-1.8.17-classico',
                 'semente':'85/6/15','inicio_sequencia':'2021-10-01','dias_anteriores_fwi':k,
                 'fwi_sementes_convergentes':bool(convergentes[k]),
                 **{f'{indice}_spread_sementes':float(spread[k,j]) for j,indice in enumerate(INDICES)},
                 'weather_sha256':meta['sha256'],'origem':'open-meteo-archive-ecmwf-ifs-horario-v1',
                 'sgif_sha256':fontes[str((anterior/'Data2001_now.csv').relative_to(REPO))]['sha256'],
                 'regra_target':'5b2b-v2-tipo-rural-sem-pai-marcador-ou-causa711',
                 'provenance':f'manifesto.json#municipios/{cod}',
                 'split_proposto':{2022:'treino',2023:'validacao',2024:'teste'}[t.year]}
            motivos=motivos_exclusao(row);row['elegivel']=not motivos;row['motivos_exclusao']='|'.join(motivos)
            rows.append(row)
        meteorologia.append(dict(municipio=cod,nome=nome,latitude=lat,longitude=lon,
            latitude_grelha=raw['latitude'],longitude_grelha=raw['longitude'],horas_verificadas=n*24,
            dias_calculados=n,primeiro_dia=str(INICIO),ultimo_dia=str(FIM),
            erro_prefixo=float(np.max(abs(valores-antigo['valores'][:n])))))
    rows.sort(key=lambda r:(r['municipio'],r['data_T']))
    assert len(rows)==3288 and len({(r['municipio'],r['data_T']) for r in rows})==3288
    for c,_,_,_ in PONTOS:
        dias=[datetime.fromisoformat(r['data_T']) for r in rows if r['municipio']==c]
        assert len(dias)==1096 and all(b-a==timedelta(days=1) for a,b in zip(dias,dias[1:]))
    elegiveis=[r for r in rows if r['elegivel']];excluidos=[r for r in rows if not r['elegivel']]
    csv_out('dataset_completo.csv',rows);csv_out('dataset_elegivel.csv',elegiveis);csv_out('exclusoes.csv',excluidos)
    grupos=defaultdict(list)
    for r in rows:
        for g in ('municipio','ano','mes','split_proposto'):
            grupos[g,str(r[g])].append(r)
        grupos['municipio_ano_mes',f"{r['municipio']}/{r['ano']}/{r['mes']:02d}"].append(r)
    qualidade=dict(completo=resumo(rows),elegivel=resumo(elegiveis),excluidos=resumo(excluidos),
        motivos=dict(Counter(m for r in excluidos for m in r['motivos_exclusao'].split('|'))),
        grupos=[dict(dim=g,valor=v,completo=resumo(rr),elegivel=resumo([r for r in rr if r['elegivel']])) for (g,v),rr in sorted(grupos.items())],
        gaps=0,duplicados=0,features_invalidas=0,meteorologia=meteorologia,chamadas_externas=0)
    json_out('qualidade.json',qualidade)
    features=['municipio','temperatura','humidade','vento','precipitacao_24h',*INDICES,'mes','dia_do_ano','dia_da_semana','epoca_ano']
    json_out('schema.json',dict(colunas=list(rows[0]),features_permitidas=features,target='target_24h',
        null_csv='campo vazio',tipos={**{k:type(v).__name__ for k,v in rows[0].items()},'target_24h':'nullable integer enum 0/1','municipio':'string de quatro algarismos','data_T':'datetime ISO8601 UTC'},
        unidades=dict(temperatura='degC',humidade='%',vento='km/h a 10 m',precipitacao_24h='mm',indices='adimensionais'),
        proibidas_como_features=[k for k in rows[0] if k not in features],
        regra='Lista explícita: nunca selecionar automaticamente todas as colunas numéricas.'))
    for p in (Path(__file__),BASE/'validar_5b3.py',BASE/'labels_5b2b.py',BASE/'auditar_5b2b.py',REPO/'experiments/fwi_fase8/convergencia.py',REPO/'backend/services/meteorologia_fwi.py'):
        registar(p)
    json_out('manifesto.json',dict(versao='5b3-v1',fontes=fontes,municipios=meteorologia,semente=[85,6,15],
        sementes_sensibilidade=SEMENTES,atol=ATOL,rtol=RTOL,
        criterio='Concordância numérica das 27 trajetórias no próprio T, não estabelecimento científico nem prova universal.',
        estudo='retrospetivo; disponibilidade em T não demonstrada',periodo=['2022-01-01','2024-12-31']))
    json_out('checksums.json',{p.name:sha(p) for p in sorted(OUT.iterdir()) if p.suffix in ('.csv','.json') and p.name!='checksums.json'})
    print(json.dumps({k:v for k,v in qualidade.items() if k not in ('grupos','meteorologia')},ensure_ascii=True),flush=True)


if __name__=='__main__':main()
