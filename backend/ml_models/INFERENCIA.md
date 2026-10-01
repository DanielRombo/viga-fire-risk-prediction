# Inputs da inferência

O notebook `ml/notebooks/01_exploracao_dados.ipynb` e `feature_names_in_` dos
scalers confirmam estas ordens, que a inferência preserva:

- Kaggle: `temp, RH, wind, rain, FFMC, DMC, DC, ISI, month_num, day_num`.
- ANPC: `mes, hora, dia_semana, ano, distrito_cod, lat, lon`.

A temperatura está em °C, a humidade em %, o vento em km/h e a precipitação
na unidade de altura de água usada pela fonte. O dataset Forest Fires documenta
`rain` como mm/m²: [fonte UCI](https://www.archive.ics.uci.edu/dataset/162/forest%2Bfires).
O notebook não faz conversões. A equivalência temporal das medições de precipitação
exige validação antes de ativar uma fonte futura de inputs completos para Kaggle.

Hoje a BD contém temperatura, humidade, vento, precipitação e timestamp da
observação. A região fornece distrito e coordenadas em graus decimais.
Não existem FFMC, DMC, DC ou ISI observados na BD: o modelo Kaggle fica indisponível.
Os componentes do FWI simplificado não são substitutos destes índices e não são
enviados ao ML. Zero é válido; dados ausentes ou não finitos não recebem defaults.

As datas da BD sem offset são UTC. Para extrair as features do calendário,
usa-se `Europe/Lisbon`: é a interpretação adotada para as datas civis continentais
do treino ANPC, que não documenta um fuso explícito. Nunca se usa a hora atual.
No Kaggle, segunda-feira é 1; no ANPC, é 0. O mês vai de 1 a 12.

O encoder ANPC contém os 18 distritos continentais em maiúsculas. A inferência
remove espaços exteriores e converte para maiúsculas, preservando acentos.
Distrito desconhecido não recebe código 0. Açores e Madeira não estão no encoder:
ANPC fica indisponível nessas regiões. Os dados meteorológicos/FWI continuam
independentes desta disponibilidade.

Cada modelo tem estado e motivo em `ml.disponibilidade`. O resultado ML é `ok`,
`parcial` ou `indisponivel`. Sem modelos válidos, probabilidade e nível são nulos.
O frontend apresenta a mensagem de funcionamento parcial ou indisponibilidade.

O ensemble usa `sum(probabilidade * peso) / sum(pesos disponíveis)`, com pesos
Kaggle 0,4 e ANPC 0,6. Um único modelo mantém a sua probabilidade, sem amplificação.
O arredondamento ocorre só na resposta. Falhas ou probabilidades inválidas excluem
apenas o modelo afetado. As classes e os objetivos científicos não foram alterados.

A validação obrigatória dos cinco artefactos no arranque/build mantém-se.
Disponibilidade parcial de inferência não permite arrancar com ficheiros em falta.
