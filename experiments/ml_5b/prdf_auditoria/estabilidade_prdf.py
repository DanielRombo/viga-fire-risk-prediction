"""Triagem mensal descritiva; nunca certifica negativos pela distribuição."""
from collections import Counter
from statistics import median
from auditar_prdf import ro, municipio, csvout, guardar

def main():
    counts=Counter(); names={}; years=Counter(); represented={y:set() for y in range(2022,2026)}
    with ro('fogos.gpkg') as db:
        for year,month,ine,name,n in db.execute("SELECT Ano,substr(DHInicio,6,2),INE,Concelho,count(*) FROM Fogos WHERE Ano BETWEEN 2022 AND 2025 GROUP BY Ano,substr(DHInicio,6,2),INE,Concelho"):
            code=municipio(ine); y=int(year); counts[code,y,int(month)]+=n; names[code]=name
            years[y]+=n; represented[y].add(code)
    rows=[]
    for code in sorted(names):
        for month in range(1,13):
            past=[counts[code,y,month] for y in range(2022,2025)]
            ref=median(past); now=counts[code,2025,month]
            flag='zero_com_mediana_historica_5' if now==0 and ref>=5 else ('pico_5x_mediana_minimo_20' if now>=20 and now>5*max(ref,1) else '')
            rows.append(dict(municipio=code,nome=names[code],mes=month,n2022=past[0],n2023=past[1],n2024=past[2],n2025=now,mediana_anterior=ref,alerta=flag))
    csvout('estabilidade_2025.csv',rows)
    guardar('estabilidade.json',dict(anos=dict(years),municipios_presentes={y:len(v) for y,v in represented.items()},alertas=[r for r in rows if r['alerta']],nota='Limiares de triagem descritiva, não de certificação. Frequência de incêndios varia com meteorologia; um alerta não prova falha de reporte.'))

if __name__=='__main__':main()
