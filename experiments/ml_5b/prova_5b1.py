"""Prova RETROSPETIVA de 30 dias. Nenhum label certificado, treino ou BD.

python -B experiments/ml_5b/prova_5b1.py recolher
python -B experiments/ml_5b/prova_5b1.py calcular  # ambiente xclim 0.62.0
"""
import csv
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/'prova_5b1'
INICIO=date(2019,7,1); ND=30
INDICES=('ffmc','dmc','dc','isi','bui','fwi')


def digest(b):return hashlib.sha256(b).hexdigest()


def guardar(nome,d):
    (OUT/nome).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False,default=str)+'\n',encoding='utf-8')


def regioes():
    return [r for r in json.loads((ROOT/'backend/data/regioes_principais.json').read_text(encoding='utf-8')) if r['nome'] in ('Lisboa','Vila Real')]


def params(r):
    return {'latitude':r['latitude'],'longitude':r['longitude'], 'models':'ecmwf_ifs',
        'hourly':'temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation',
        'temperature_unit':'celsius','wind_speed_unit':'kmh','precipitation_unit':'mm',
        'timezone':'GMT','timeformat':'iso8601','start_date':'2019-06-30','end_date':'2019-07-30'}


def recolher():
    OUT.mkdir(exist_ok=True)
    for r in regioes():
        nome=r['nome']; raw=OUT/f'{nome}_archive.json'; meta=OUT/f'{nome}_pedido.json'
        if raw.exists() or meta.exists():
            m=json.loads(meta.read_text(encoding='utf-8'))
            assert m['sha256']==digest(raw.read_bytes()) and m['params']==params(r)
            print(nome,'reutilizado após checksum');continue
        url='https://archive-api.open-meteo.com/v1/archive?'+urlencode(params(r))
        try:
            with urlopen(url, timeout=60) as resp:
                corpo=resp.read();status=resp.status
            d=json.loads(corpo)
            if status != 200 or 'hourly' not in d:raise ValueError('Resposta Archive inválida')
        except Exception as exc:
            guardar(f'{nome}_falha.json',{'estado':'erro_fonte','tipo':type(exc).__name__,'mensagem':str(exc),'url':url})
            raise
        raw.write_bytes(corpo)
        guardar(meta.name,{'url':url,'params':params(r),'recolhido_em':datetime.now(timezone.utc),
            'status':status,'sha256':digest(corpo),'bytes':len(corpo), 'regiao':r,
            'produto':'open-meteo-archive-ecmwf-ifs-horario-v1',
            'nota':'Produto atribuído pelo pedido; resposta não certifica run/available_at histórico.'})
        print(nome,len(d['hourly']['time']),'horas guardadas',flush=True)


def janela(evento,T):
    # Hipótese explícita só para a prova. O fuso ANPC não está certificado.
    naive=datetime.fromisoformat(evento['data_local_sem_fuso_confirmado'])
    local=naive.replace(tzinfo=ZoneInfo('Europe/Lisbon'))
    instante=local.astimezone(timezone.utc)
    assert local.fold==0 and local.utcoffset()==timedelta(hours=1)  # julho, fora de transições
    return T < instante <= T+timedelta(hours=24)


def calcular():
    sys.path.insert(0,str(ROOT/'backend'))
    from services.open_meteo_fwi import interpretar_resposta
    from services.meteorologia_fwi import (AmostraHorariaFWI, TerritorioFWI, UNIDADES_FWI, preparar_observacao_diaria)
    from services.fwi_diario import EstadoFWI, QualidadeEstado, calcular_fwi_diario, VERSAO_FWI
    eventos=json.loads((OUT.parent/'fase1/ocorrencias_piloto.json').read_text(encoding='utf-8'))
    linhas=[];resumos=[]
    for id_experimental,r in enumerate(regioes(),1):
        nome=r['nome'];raw=(OUT/f'{nome}_archive.json').read_bytes()
        meta=json.loads((OUT/f'{nome}_pedido.json').read_text(encoding='utf-8'))
        assert digest(raw)==meta['sha256'] and meta['params']==params(r)
        inicio=datetime(2019,6,30,13,tzinfo=timezone.utc)
        fim=datetime(2019,7,30,12,tzinfo=timezone.utc)
        horas=interpretar_resposta(json.loads(raw),r['latitude'],r['longitude'],inicio,fim,datetime.fromisoformat(meta['recolhido_em']))
        assert len(horas)==ND*24 and all(h.qualidade=='valido' for h in horas)
        assert [h.instante_utc for h in horas]==[inicio+timedelta(hours=i) for i in range(ND*24)]
        anterior=EstadoFWI(id_experimental,INICIO-timedelta(days=1),85,6,15,QualidadeEstado.CONVENCIONAL,'semente explícita experimental 85/6/15')
        sequencia=[]
        for i in range(ND):
            grupo=horas[i*24:(i+1)*24]
            o=preparar_observacao_diaria(id_regiao=id_experimental,data_referencia=INICIO+timedelta(days=i),
                territorio=TerritorioFWI.CONTINENTE,latitude=r['latitude'],unidades=UNIDADES_FWI,origem=meta['produto'],
                amostras=[AmostraHorariaFWI(h.instante_utc,h.precipitacao_hora,h.temperatura,h.humidade,h.vento) for h in grupo])
            resultado=calcular_fwi_diario(o,anterior)
            T=o.instante_referencia_utc+timedelta(hours=3)
            assert all(h.instante_utc<=o.instante_referencia_utc<T for h in grupo)
            candidatos={e['id_hash'] for e in eventos if e['municipio']==nome and janela(e,T)}
            indices={k:getattr(resultado,k) for k in INDICES}
            linhas.append({'municipio':nome,'T_utc':T.isoformat(),'fim_horizonte_utc':(T+timedelta(hours=24)).isoformat(),
                'data_referencia':o.data_referencia.isoformat(),'max_valid_time':o.instante_referencia_utc.isoformat(),
                'temperatura':o.temperatura,'humidade':o.humidade,'vento':o.vento,'precipitacao_24h':o.precipitacao_24h,
                **indices,'eventos_rurais_registados_horizonte':len(candidatos),
                'y_certificado':None,'available_at_historico':None,'features_conhecidas_em_T':False,
                'estado':'em_inicializacao','operacional':False,'uso':'retrospetivo_apenas',
                'motivo_label_ausente':'cobertura, fuso e semântica do evento não certificados'})
            sequencia.append({'observacao':asdict(o),'estado_anterior':asdict(anterior),'indices':indices,
                               'horas': [h.instante_utc.isoformat() for h in grupo]})
            anterior=resultado.proximo_estado()
        guardar(f'{nome}_sequencia.json',sequencia)
        sub=[l for l in linhas if l['municipio']==nome]
        resumos.append({'municipio':nome,'latitude_pedido':r['latitude'],'longitude_pedido':r['longitude'],
            'latitude_grelha':horas[0].latitude_grelha,'longitude_grelha':horas[0].longitude_grelha,
            'horas_recebidas':len(json.loads(raw)['hourly']['time']),'horas_utilizadas':len(horas),'dias':ND,
            'dias_com_evento_registado':sum(l['eventos_rurais_registados_horizonte']>0 for l in sub),
            'dias_sem_evento_registado_nao_negativos':sum(l['eventos_rurais_registados_horizonte']==0 for l in sub),
            'total_eventos_registados_horizontes':sum(l['eventos_rurais_registados_horizonte'] for l in sub),
            'indices_min_max':{k:[min(l[k] for l in sub),max(l[k] for l in sub)] for k in INDICES},
            'sha256_input':meta['sha256'],'gaps':0,'duplicados':0,'negativos_certificados':None})
    with (OUT/'linhas_retrospetivas.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(linhas[0]));w.writeheader();w.writerows(linhas)
    guardar('resumo.json',{'versao':VERSAO_FWI,'regioes':resumos,'labels_certificados':0,
        'sha256_eventos_piloto':digest((OUT.parent/'fase1/ocorrencias_piloto.json').read_bytes()),
        'sha256_adaptador':digest((ROOT/'backend/services/fwi_diario.py').read_bytes()),
        'funchal':'não recolhido: sem cobertura ANPC demonstrada','seed':[85,6,15],
        'janela':['2019-07-01','2019-07-30'],'convergencia_demonstrada':False})
    print(json.dumps(resumos,ensure_ascii=True,indent=2))


if __name__=='__main__':
    {'recolher':recolher,'calcular':calcular}[sys.argv[1]]()
