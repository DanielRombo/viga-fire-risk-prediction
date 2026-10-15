"""Verificação poligonal isolada; CAOP2025 é controlo, não geometria histórica certificada."""
import csv
import json
from collections import Counter
from shapely.geometry import shape, Point
from shapely.prepared import prep
from obter_5b2b import ROOT

def main():
    codes=('1106','0805','1714','0303','0603')
    polys={}
    for c in codes:
        obj=json.loads((ROOT.parent/'fontes_5b2'/f'dgt_{c}.bin').read_text(encoding='utf-8'))
        assert obj['properties']['dtmn']==c
        g=shape(obj['geometry']);assert g.is_valid
        polys[c]=prep(g)
    resultados=[];cont=Counter()
    with (ROOT/'consolidado.csv').open(encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if not '2018'<=r['DHInicio'][:4]<='2024':continue
            try:p=Point(float(r['Lon_4326']),float(r['Lat_4326']))
            except ValueError:continue
            encontrados=[c for c,g in polys.items() if g.covers(p)]
            c=r['municipio']
            if c not in codes and not encontrados:continue
            ok=encontrados==[c]
            cont['coerente' if ok else 'conflito']+=1
            resultados.append(dict(Codigo=r['Codigo'],municipio=c,municipios_geometria='|'.join(encontrados),
                                    DHInicio=r['DHInicio'],coerente=ok,
                                    territory_confidence='media' if ok else 'baixa',
                                    motivo=r['motivo'],geometria='DGT_CAOP2025_controle_nao_historico'))
    with (ROOT/'territorio_piloto.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(resultados[0]));w.writeheader();w.writerows(resultados)
    (ROOT/'territorio_resumo.json').write_text(json.dumps(dict(cont),indent=2)+'\n',encoding='utf-8')
    print(dict(cont))

if __name__=='__main__':main()
