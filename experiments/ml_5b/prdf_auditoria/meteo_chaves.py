"""Segunda passagem dirigida: investigar chaves históricas e valores numéricos."""
import csv
import math
from collections import Counter,defaultdict
from auditar_prdf import DATA,ro,guardar,NULLS,epoch

def main():
    c=ro('fogos.gpkg');codes=set();alias=defaultdict(list)
    for code,y in c.execute('SELECT Codigo,Ano FROM Fogos'):
        codes.add(code);prefix=str(int(y))+'_'
        if code.startswith(prefix):alias[code[len(prefix):]].append(code)
    c.close();matches=Counter();codes_seen=set();rem=set();examples=[];invalid=Counter();limits={};n=0;rows2025=Counter()
    with (DATA/'METEO.csv').open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            n+=1;code=r['codigo']
            if code in codes:matches['linhas_exatas']+=1;codes_seen.add(code)
            elif len(alias.get(code,[]))==1:
                matches['linhas_alias_univoco']+=1;codes_seen.add(alias[code][0])
                if len(examples)<10:examples.append(dict(meteo=code,fogos=alias[code][0]))
            elif code in alias:matches['linhas_alias_ambiguo']+=1
            else:matches['linhas_nao_resolvidas']+=1;rem.add(code)
            for k in ('T','HR','V','Prec','Pacum','FFMC','DMC','DC','ISI','BUI','FWI'):
                if r[k] in NULLS:continue
                try:v=float(r[k])
                except ValueError:invalid[k+'_parse']+=1;continue
                if not math.isfinite(v):invalid[k+'_nao_finito']+=1;continue
                mm=limits.setdefault(k,[v,v]);mm[0]=min(mm[0],v);mm[1]=max(mm[1],v)
                if k!='T' and v<0:invalid[k+'_negativo']+=1
                if k=='HR' and v>100:invalid['HR_maior100']+=1
            if n%1000000==0:print('METEO chaves',n,flush=True)
    guardar('meteo_chaves.json',dict(n=n,match=dict(matches),fogos_com_meteo_exato_ou_alias=len(codes_seen),
        fogos_sem_meteo=len(codes-codes_seen),codigos_nao_resolvidos=len(rem),exemplos_alias=examples,
        amostra_nao_resolvidos=sorted(rem)[:10],alias_ambiguos=sum(len(v)>1 for v in alias.values()),
        numeros_invalidos=dict(invalid),limites=limits,
        regra='Apenas remoção de prefixo ANO_ do Codigo Fogos quando presente e alias unívoco. Hipótese de ligação histórica secundária; 2025 já liga por ID exato.'))

if __name__=='__main__':main()
