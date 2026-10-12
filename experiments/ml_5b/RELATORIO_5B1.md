# ML 5B.1 — desbloqueio do dataset, 12/10/2026

## Decisão: NO-GO para o dataset completo de previsão

**GO apenas demonstrado para a junção técnica retrospetiva.** Foram obtidas duas
respostas Archive/ECMWF IFS e calculados 60 dias FWI, sem BD nem produção. Não é
possível apresentar as linhas como “features conhecidas em T + label certificado”:
faltam evidência de disponibilidade histórica dos inputs e completude dos eventos.
As duas condições são explícitas no CSV: `features_conhecidas_em_T=false`,
`available_at_historico=null`, `y_certificado=null`. Não foram gerados negativos.

2016–2020 integral também não está disponível com o produto IFS adotado: começa
em 2017; o ANPC local de 2020 acaba em 06/07, e existem lacunas anteriores. Não se
mudou de produto, não se iniciou reconstrução total nem treino.

## 1. Schema, qualidade e cobertura ANPC

Cinco CSV com o mesmo cabeçalho de 15 campos e 910 783 linhas:

| Campos | Interpretação e utilização |
|---|---|
| `Numero` | Identificador candidato a evento; não usar como feature. Verificar revisões e unicidade. |
| `DataOcorrencia` | Data/hora sem offset; mistura dia/mês/ano e ISO, incluindo microssegundos. Sem documentação local que prove ignição versus alerta/registo. |
| `DataFechoOperacional` | Fecho, frequentemente ausente; informação posterior, proibida como feature. |
| `Natureza` | Texto hierárquico “grupo / tipo / subtipo”. Permite taxonomia sem meios mobilizados. Não existe código de natureza separado. |
| `EstadoOcorrencia` | Inclui encerrada, falso alarme/alerta e estados intermédios. Serve para adjudicação posterior do label, nunca feature futura. |
| `Distrito`, `Concelho` | Ligação nominal administrativa candidata, normalizada em conjunto. Sem código municipal oficial. |
| `Freguesia`, `Localidade` | Apoio a desambiguação; não substituem código/território estável. |
| `Latitude`, `Longitude` | Graus decimais, separador vírgula ou ponto; nulos, zero/zero e posições suspeitas. Não assumimos validade geográfica por serem números. |
| Quatro campos `Numero…Envolvidos` | Meios/operacionais terrestres/aéreos; excluídos da taxonomia e das features futuras. |

Resultados guardados em `fase1/auditoria.json` e `fase1/cobertura_diaria.csv`:

- Intervalo observado 09/01/2016–06/07/2020, com **62 dias nacionais inteiramente
  vazios dentro desses extremos**: 61 em 2016 e **17/12/2019**. A lista exata está
  no JSON. Os períodos anteriores/posteriores também constam do CSV, sem certificar zeros.
- Há registos nos restantes dias nacionais, mas isso **não prova completude de
  todos os municípios nem de incêndios rurais**. Dias municipais vazios são
  contagens observadas, não demonstração de falha nem prova de ausência de incêndio.
- Um identificador repetido com linha idêntica em 2016 (linhas lógicas CSV 83935 e
  83938), numa zona de linhas anómalas. Não foi apagado do original. Não se
  encontraram outros IDs repetidos na leitura transversal dos cinco ficheiros.
- **Sete datas não interpretáveis**: cinco vazias e duas com texto semelhante a
  latitude em vez de data. Cinco pares distrito/concelho vazios e dois `0/0`.
  Isto é corrupção semântica de linhas, mesmo sem erro estrutural do CSV.
- Correção à auditoria 5B: três datas de 2020 têm microssegundos válidos; o parser
  inicial não os aceitava. Foram agora reconhecidas, sem alterar os ficheiros de
  origem nem reescrever o relatório histórico da fase anterior.
- Os CSV não incluem manifesto de completude por dia/município, histórico de
  extração, fuso certificado ou garantia de snapshot final. A documentação pública
  consultada não demonstrou que estes cinco ficheiros locais sejam um arquivo total.
  Não se infere a sua origem exata apenas pelo nome das colunas.

### Taxonomia provisória, sem mobilização

Incluir apenas estes valores normalizados de `Natureza`:

1. Riscos Mistos / Incêndios Rurais / Povoamento Florestal;
2. Riscos Mistos / Incêndios Rurais / Mato;
3. Riscos Mistos / Incêndios Rurais / Agrícola.

Excluir queima, gestão de combustível, consolidação de rescaldo, detritos,
transportes, equipamento e incêndios urbanos. Reacendimentos/atendimentos da mesma
ignição precisam de regra de identidade antes dos labels definitivos.

São **61 439 candidatos por natureza**. Excluir explicitamente `Falso Alarme`
(5 174) e `Falso Alerta` (761) deixa **55 504 candidatos**, não 55 504 incêndios
certificados nem dias positivos. Há 32 011 `Encerrada`, 13 982 `Conclusão` e
9 511 candidatos em outros estados. Encerramento, por si só, não prova ignição.
O estado final pode ser usado como ground truth após confirmação semântica, mas
nunca como feature no instante T. Excluir um falso alerta não torna a sua janela
um negativo certificado: a cobertura dos restantes eventos continua desconhecida.

## 2. Unidade territorial

Recomendação: **município × emissão diária**, com município definido por código e
limite CAOP versionado. Cada um dos 28 pontos tem um município homónimo candidato;
26 encontram correspondência `Distrito+Concelho` nos CSV e dois não têm qualquer
registo correspondente (Funchal e Ponta Delgada). Isso não significa zero incêndios
nas ilhas. Funchal foi excluído da recolha piloto pela condição pedida.

A tabela dos 28 pontos e respetivas contagens está em `territorios_5b1.md`.
Há 280 pares nominais não vazios; um é `0/0`. Restam **279 pares candidatos**,
dos quais **253 não têm ponto do catálogo**. Não se declara que sejam 279 municípios
oficiais distintos: é preciso reconciliar grafias/códigos e incoerências distritais.
Exemplos sem ponto: Águeda, Albergaria-a-Velha, Anadia, Arouca, Espinho, Ílhavo.

Todos os pontos são localizações meteorológicas, não polígonos. Lisboa, Vila Real,
Funchal, etc. podem fornecer uma feature pontual para o município, mas não medem a
variabilidade do território inteiro. Não se deve estender Faro a todo o Algarve,
Funchal à Madeira ou Ponta Delgada aos Açores. Não unir distritos e municípios.

Polígonos não são indispensáveis para uma **junção provisória pelo concelho declarado**;
são necessários para verificar coordenadas, fronteiras e a representação espacial,
ou para resolver eventos sem código/nome fiável. O GeoJSON local de 20 distritos e
agrupamentos insulares não serve para esta validação municipal. Fonte oficial:
[DGT, CAOP2019](https://www.dgterritorio.gov.pt/Carta-Administrativa-Oficial-de-Portugal-CAOP2019),
com versões históricas e catálogo de entidades. Não foi descarregado nenhum polígono.
Resolver fronteiras com código confirmado e geometria versionada; casos ambíguos
ficam em quarentena, nunca atribuídos à região mais próxima silenciosamente.

## 3. Prova técnica realizada

**01/07/2019–30/07/2019, 30 dias por ponto.** Pedidos de 30/06 a 30/07 para incluir
a chuva antecedente. Dois pedidos HTTP bem-sucedidos, **1 488 horas recebidas** e
**1 440 utilizadas**. As 48 horas adicionais resultam da resposta por dias civis;
não são duplicados nem foram usadas indevidamente.

| Município | Coordenadas pedidas | Coordenadas da grelha devolvida | Dias com candidatos / sem candidatos | Eventos rurais candidatos nas janelas |
|---|---|---|---|---:|
| Lisboa | 38.7169, -9.1399 | 38.69947, -9.196167 | 6 / 24 | 7 |
| Vila Real | 41.3006, -7.7457 | 41.300526, -7.7474976 | 7 / 23 | 11 |

“Sem candidatos” **não é negativo**. Todos os 60 labels certificados permanecem
null. Associação pelo município declarado, ainda sem validação poligonal.

Temperatura °C, RH %, vento 10 m km/h, chuva mm; timezone GMT confirmado na resposta.
Foram exigidas 24 horas consecutivas `(referência−24h, referência]` por cálculo;
referência 12:00 UTC, emissão experimental T=15:00 UTC. Todas as horas usadas têm
`valid_time <= referência < T`. Horizonte `(T,T+24h]`. Datas ANPC são interpretadas
**provisoriamente** como Europe/Lisbon (UTC+1 em julho), sem alegar fuso certificado.
Eventos até ao dia seguinte são lidos só para o label, nunca como features.

Semente explícita 85/6/15 em 30/06; cálculo cronológico pelo adaptador existente,
xclim 0.62.0, variante clássica validada contra cffdrs 1.8.17, RH=100% preservado.
Cada dia recebe FFMC/DMC/DC do anterior. **30 dias não demonstram convergência**;
resultados permanecem `em_inicializacao`, `operacional=false`, sem promoção.
Os IDs 1/2 usados pelo adaptador nesta prova são identificadores experimentais
locais, não IDs de produção. A junção usa nomes do catálogo e coordenadas.

| Índice | Lisboa: mínimo–máximo | Vila Real: mínimo–máximo |
|---|---:|---:|
| FFMC | 74,2425–92,6963 | 63,3111–91,4699 |
| DMC | 8,2170–74,0823 | 8,5752–78,7329 |
| DC | 22,7540–259,3740 | 23,0960–259,7263 |
| ISI | 1,7429–13,4716 | 0,7095–8,4255 |
| BUI | 8,6367–86,4413 | 8,8945–87,4674 |
| FWI | 4,7231–35,7994 | 0,7062–25,0264 |

Precisão completa nos ficheiros; arredondamento apenas nesta tabela. Zero gaps,
duplicados horários/dia ou valores não finitos/inválidos nos inputs utilizados e
resultados. Os JSON originais, parâmetros, timestamps de recolha, SHA-256, sequência
de estados anteriores e CSV de 60 linhas estão em `prova_5b1/`.

A primeira tentativa de rede foi bloqueada pelo sandbox (`WinError 10013`), não
pela fonte. Depois da autorização de rede, ambos os pedidos passaram. O registo
`Lisboa_falha.json` é preservado como evidência dessa tentativa; o resultado final
está em `resumo.json`. A seleção inicial apenas por natureza foi revista para
excluir falsos alarmes/alertas; repetiu-se só a junção/cálculo local, **sem novos
downloads**. Vila Real passou de 13 para 11 eventos candidatos; os resultados FWI
não dependem dessa seleção de labels.

## 4. Critério objetivo para negativos

Uma janela só poderá receber `y=0` quando todas estas condições forem satisfeitas:

1. Fonte e taxonomia documentadas, território/código inequívocos e timestamp/fuso
   com significado conhecido; target denominado ignição ou notificação conforme a fonte.
2. Exportação consolidada com intervalo de cobertura explícito, sem paginação perdida,
   extrações truncadas, indisponibilidades ou revisões pendentes nessa região/janela.
3. Horizonte terminado e latência de notificação/consolidação documentada já decorrida.
4. Reconciliação de contagens e completude com o fornecedor; fluxo de outras naturezas
   é diagnóstico auxiliar, nunca certificação automática de cobertura rural.
5. Duplicados, falsos alarmes, reacendimentos e conflitos de território resolvidos.
   Registos potencialmente relevantes em quarentena bloqueiam as janelas afetadas.
6. Nenhum evento elegível no horizonte completo após essas verificações.

Os CSV atuais não satisfazem essas condições. Os 62 vazios nacionais, o final parcial
de 2020 e os snapshots intermédios impedem afirmar “totalidade das ocorrências”.
Interrompida **a geração de negativos**, não escondida a falha com zeros ou imputação.

## 5. Disponibilidade no instante T

| Utilização do Archive/ECMWF IFS reconstruído | Decisão |
|---|---|
| A — estudo retrospetivo | Sim, com proveniência, cobertura e limitações de semente declaradas. |
| B — simulação realista de previsão em T | Não demonstrado com esta fonte reconstruída. |
| C — ambos | Não, sem arquivo de emissão/disponibilização e desenho equivalente ao operacional. |

O Archive contém análise histórica montada de runs; não é uma medição pontual nem
um arquivo que, nesta resposta, forneça `issued_at/available_at` de cada valor. Ler
apenas horas anteriores a T evita leakage por data de validade, **mas não prova
ausência de leakage por assimilação, revisão ou disponibilização posterior**.
FWI calculado retrospetivamente herda esta limitação. `ingerido_em` em 2026 não é
substituto de disponibilidade em 2019. O número FWI atual não deve ser retroativamente
tratado como uma previsão disponível à época.

Para previsão real: preservar runs/observações com emissão e publicação anteriores
a T, incluindo revisões, latência e produto, ou executar recolha prospectiva com
snapshots imutáveis. [Open-Meteo Archive](https://open-meteo.com/en/docs/historical-weather-api)
documenta IFS desde 2017; [Previous Runs](https://open-meteo.com/en/docs/previous-runs-api)
e [Historical Forecast](https://open-meteo.com/en/docs/historical-forecast-api) devem
ser avaliados quanto ao histórico específico disponível. Não assumimos que essas
APIs forneçam agora todas as emissões de 2016–2020.

## 6. Volume estimado e próximos passos

Estimativas aritméticas, sem excluir lacunas e **sem** warm-up adicional:

| Âmbito | Dias/ponto | Linhas diárias | Horas mínimas de cálculo |
|---|---:|---:|---:|
| 26 municípios, 01/01/2017–05/07/2020 | 1 282 | 33 332 | 799 968 |
| 28 pontos, mesmo intervalo (hipotético, faltam labels insulares) | 1 282 | 35 896 | 861 504 |
| 26 municípios, 2016–2020 completos (não suportado pelo IFS/CSV atuais) | 1 827 | 47 502 | 1 140 048 |
| 28 pontos, 2016–2020 completos (hipotético) | 1 827 | 51 156 | 1 227 744 |

O limite 05/07 conserva o horizonte até 06/07 às 15 UTC apenas sob a hipótese de
hora civil adotada; não certifica cobertura do último dia. Incluir também a chuva
antecedente e uma política explícita de estado inicial. O IFS não permite warm-up
antes de 2017, pelo que os primeiros dias desse ano não podem ser apresentados
como sequência estabelecida. Número de pedidos e bytes dependerão dos lotes e do
produto; não se extrapolou latência ou RAM da prova.

**Resposta objetiva:** 26 municípios candidatos podem ser investigados; **zero
municípios têm ainda um dataset de positivos/negativos certificado nesta auditoria**.
Há evidência de viabilidade computacional para 2019, não de validade experimental
para treinar uma probabilidade futura. A ausência de Funchal não autoriza extrapolar
o continente para as ilhas.

Prioridade: obter origem/manifesto e exportação consolidada ANEPC/ICNF, investigar
17/12/2019 e lacunas de 2016, confirmar taxonomia/fuso/semântica, resolver códigos
municipais e adquirir apenas os limites oficiais necessários. Depois definir a
estratégia de disponibilidade em T e voltar ao gate de dados. **Não iniciar a
reconstrução completa ou treino antes disso.**

## 7. Reprodução e segurança

- `python -B experiments/ml_5b/auditar_5b1.py`
- `python -B experiments/ml_5b/prova_5b1.py recolher` — reutiliza respostas existentes apenas após verificar parâmetros e hash.
- Cálculo executado com `projeto_final_curso-backend:latest`, Python 3.11/xclim 0.62.0,
  em `docker run --rm --network none`; repositório só de leitura, único volume
  gravável `experiments/ml_5b/prova_5b1`, URL de BD inacessível. Nenhum serviço arrancado.
- `python -B experiments/ml_5b/prova_5b1.py calcular` nesse ambiente.
- `python -B -m unittest discover -s experiments/ml_5b -p test_5b1.py -v`
- `python -B experiments/ml_5b/verificar.py`; `git diff --check`.

Nenhuma alteração de produção, API, frontend, modelos ou fórmulas; nenhuma promoção,
treino, commit ou deploy. Hashes dos CSV originais verificados antes/depois da leitura.
