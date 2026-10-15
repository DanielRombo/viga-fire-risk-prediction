"""Verificações dirigidas após deteção de séries longas e chaves secundárias."""
import csv
from collections import Counter,defaultdict
from auditar_prdf import DATA,ro,guardar,dt,epoch,rural

def main():
    c=ro('fogos.gpkg');c.row_factory=__import__('sqlite3').Row
    y25={r['Codigo']:dict(r) for r in c.execute('SELECT Codigo,DHInicio,DHFim,DHFimEstimado,DuracaoHoras,Concelho,Tipo,TipoCausa,CodCausa,Reacendimento_IncendioPai FROM Fogos WHERE Ano=2025')}
    sado=Counter(r[0] for r in c.execute('SELECT CodigoSado FROM Fogos WHERE CodigoSado IS NOT NULL'))
    code_set={r[0] for r in c.execute('SELECT Codigo FROM Fogos')};c.close()
    st={};cont=Counter()
    with (DATA/'METEO.csv').open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            event=y25.get(r['codigo'])
            if event is None:continue
            t=epoch(r['DHMeteo']);b=epoch(event['DHInicio']);e=epoch(event['DHFim'])
            s=st.setdefault(r['codigo'],[0,t,t]);s[0]+=1;s[1]=min(s[1],t);s[2]=max(s[2],t)
            cont['mais24h_apos_alerta']+=t-b>86400;cont['mais48h_apos_alerta']+=t-b>172800
            if e is not None:cont['apos_extincao_declarada']+=t>e
    longest=[]
    for code,s in sorted(st.items(),key=lambda kv:kv[1][2]-kv[1][1],reverse=True)[:10]:
        r=y25[code];longest.append(dict(**r,linhas=s[0],span_horas=(s[2]-s[1])/3600,primeira_hora_apos_alerta=(s[1]-epoch(r['DHInicio']))/3600,ultima_hora_apos_alerta=(s[2]-epoch(r['DHInicio']))/3600))
    valid={k for k,r in y25.items() if rural(r)=='potencial_nova_ocorrencia'}
    c=ro('PBA.gpkg');pba=Counter()
    for code,ane,best in c.execute('SELECT Cod_SGIF,Cod_ANEPC,BEST_Codigo FROM PBA'):
        if code in code_set:pba['match_sgif_exato']+=1;continue
        if ane is not None and sado[ane]==1:pba['sem_sgif_com_ane_exato_univoco']+=1
        elif ane is not None and sado[ane]>1:pba['sem_sgif_ane_ambiguo']+=1
        else:pba['sem_sgif_sem_ane_match']+=1
        if best in code_set:pba['sem_sgif_best_codigo_encontrado_nao_oficial']+=1
    c.close()
    guardar('complementos.json',dict(meteo2025=dict(contagens=dict(cont),series_mais_longas=longest,potenciais_rurais=len(valid),potenciais_rurais_com_meteo=len(valid&set(st))),
        pba_chaves_secundarias=dict(pba),nota='Cod_ANEPC só unívoco aceito como ligação textual secundária; BEST_Codigo é estimado, não match oficial.'))

if __name__=='__main__':main()
