Referência científica FWI diário: cffdrs 1.8.17 (variante clássica).

`cffdrs_1_8_17.csv` é uma cópia exata de
`experiments/xclim_062/resultados/cffdrs_classico_40.csv`, produzida pela prova
isolada usando R 4.5.3 e o código oficial sem alterações:
https://github.com/cffdrs/cffdrs_r/tree/9481404cad25387292c1d8692bdb126bbe514d9c

SHA-256: `6d75cfa084f736a6d39281cfaa8b66b58818b9661503b900f03d66a5602cd4ab`.

Inputs: 48 dias de `test_fwi`, de 13/04/1985 a 30/05/1985, latitude 40° N,
temperatura °C, humidade %, vento km/h e precipitação acumulada em 24 h em mm.
Estado inicial explícito FFMC=85, DMC=6, DC=15; ajuste à latitude ativo,
sequência diária contínua. São condições do teste, não política operacional.

Tolerâncias preservadas da prova: `atol=1e-8`, `rtol=1e-10`.
Não usar resultados arredondados como estado do dia seguinte.

A divergência face ao cffdrs 1.9.2 continua documentada em
`experiments/xclim_062/RELATORIO.md`: a constante FFMC 147,2 da variante
clássica difere de 250 × 59,5 / 101. Não se alteram as fórmulas para conciliar
variantes e não se alargam tolerâncias. Proveniência e hashes das fontes R
originais constam da pasta experimental.
