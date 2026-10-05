# Fase 7 — validação geográfica real, 05/10/2026

**Resultado: recolha, persistência e continuidade aprovadas; equivalência
numérica integral da amostra REPROVADA no limite de humidade de 100%.
Não recomendar ainda integração operacional.**

Não houve alteração de produção, frontend, endpoints, scheduler, fórmulas,
modelos ou dependências. Não houve promoção nem commit. Apenas foram
criados scripts e evidências nesta pasta. Método, comandos e reprodução:
[METODO.md](METODO.md).

## A. Regiões testadas

O catálogo tem 30 pontos, incluindo 28 com recolha automática. As 25 regiões
restantes receberam 60 dias: Porto, Braga, Coimbra, Aveiro, Setúbal, Viseu,
Leiria, Évora, Castelo Branco, Guarda, Beja, Portalegre, Santarém, Bragança,
Viana do Castelo, Sintra, Cascais, Loures, Almada, Amadora, Vila Nova de Gaia,
Matosinhos, Gondomar, Guimarães e Barcelos. Gondomar/Barcelos foram incluídos
apesar de não terem recolha automática, para cobrir o catálogo completo.

Não se repetiram os 60 dias de Lisboa, Faro, Vila Real, Funchal e Ponta Delgada.
Amostra anual planeada: Porto (litoral norte), Bragança (interior norte),
Coimbra (centro), Castelo Branco (interior centro), Évora (Alentejo) e Faro
(único ponto algarvio no catálogo). Faro recebeu só a extensão anual.

A triagem dos 60 dias sinalizou eventos nas 25 regiões. Após examinar o
contexto meteorológico e comparar os dias sinalizados, ampliaram-se todas
essas regiões para 365 dias. Assim, a Fase 7 contém **25 ensaios de 60 dias
e 26 ensaios anuais**. Os IDs foram obtidos da BD inicializada pelo catálogo,
sem assumir IDs da produção. Coordenadas e IDs: `evidencias/60/regioes.json`
e `evidencias/365/regioes.json`.

## B–C. Períodos e volume

| Conjunto | Período de referência | Dias por região | Regiões | Dias calculados | Horas utilizadas |
|---|---|---:|---:|---:|---:|
| Curto | 02/08/2026–30/09/2026 | 60 | 25 | 1500 | 36 000 |
| Anual | 01/10/2025–30/09/2026 | 365 | 26 | 9490 | 227 760 |
| Total dos ensaios | — | — | 51 sequências | **10 990** | **263 760** |

As janelas sobrepõem-se: o total conta horas usadas em sequências distintas,
não 263 760 instantes únicos após unir os históricos de cada região.
As respostas brutas incluíram margens de dias civis: 264 984 horas recebidas,
9 667 725 bytes de respostas HTTP. Nenhuma margem entrou indevidamente na
precipitação diária.

Fonte: Open-Meteo Archive, `ecmwf_ifs`, sem fallback; cinco variáveis de
estrutura (`time` e os quatro campos meteorológicos). °C, %, km/h a 10 m,
mm, GMT/UTC, exatamente 24 intervalos `(t-24h,t]` e valores instantâneos em t.
Produto explicitamente pedido, sem identificação independente do modelo
na resposta JSON. Parâmetros, resposta integral, coordenadas de grelha,
timestamps e SHA-256 estão em cada `*_recolha.json`/`*_resposta.json`.

Semente explícita 85/6/15 no dia anterior à janela; nenhum estado estabelecido.
As 51 sequências terminaram `reconstruido`, com idempotência verificada e
zero registos na tabela operacional `fwi_diario`. O texto da origem da semente
mantém a designação «Ensaio Fase 6» do helper experimental reutilizado;
a execução desta fase é identificada pelos diretórios, bases e timestamps
da Fase 7. A semente numérica e a qualidade convencional são as pedidas.

## D. Estatísticas por região e comparação nacional

Tabela completa dos seis índices, com mínimo, mediana, P95 e máximo:

- [Tabela legível](evidencias/estatisticas_nacionais.md)
- [CSV](evidencias/estatisticas_nacionais.csv)
- Precisão completa e percentis adicionais: `60/*_resultado.json` e `365/*_resultado.json`.

A tabela inclui as cinco evidências anteriores, identificadas como Fase 6,
e distingue sempre janelas de 60/365 dias. Não cria um índice nacional agregado.

Maiores FWI anuais nesta fase: Castelo Branco 72,3350; Guarda 68,9915;
Beja 67,4844; Portalegre 63,7421; Évora 63,5239; Leiria 63,2323;
Santarém 62,1265; Faro 61,5308; Coimbra 60,7758; Bragança 60,1949.
Estes são valores numéricos, não classificações oficiais de risco.

## E. Alertas e investigação

Foram gerados **64 alertas nos 60 dias e 484 no ano**, total 548:
399 saltos, 144 valores FWI>50, cinco simultaneamente salto e FWI>50.
Nenhum máximo excedeu o critério regional Q3+3×IQR na respetiva janela.
Isto não prova ausência de toda e qualquer discrepância geográfica.

Os limiares exploratórios estão documentados no método e não foram usados
para corrigir, truncar ou aprovar automaticamente valores. Cada alerta tem
inputs, estado anterior, diferenças meteorológicas e comparação independente:

- [Investigação por alerta](evidencias/investigacao_alertas.md)
- [Dados completos da investigação](evidencias/investigacao_alertas.json)
- `60/alertas.json` e `365/alertas.json` conservam a triagem original.

Exemplos examinados:

- Quedas de FFMC/FWI em 23–24/08 e 30/09 coincidem frequentemente com chuva
  e subida de humidade. Beja teve queda de DMC após 9,7 mm em 29/09.
- Castelo Branco atingiu FWI 72,3350 em 07/07/2026 com 36 °C, RH 16%,
  vento 14,8 km/h e chuva zero. Guarda atingiu 68,9915 com 30,2 °C,
  RH 27%, vento 20,4 km/h e chuva zero. Estes extremos passaram na referência.
- Porto, Matosinhos e Vila Nova de Gaia têm a mesma célula devolvida:
  41.159927/-8.626617. A igualdade dos inputs e resultados é explicável pela
  resolução da fonte, não por IDs confundidos. Não são observações locais
  independentes de três estações. A latitude regional continua explícita.
- A divergência RH=100 identificada na comparação científica está descrita
  abaixo; não foi ocultada pelo facto de outras verificações passarem.

**Sensibilidade ao estado inicial:** os inputs dos 60 dias comuns foram
comparados hora a hora e são idênticos nas janelas curta/anual. Mesmo assim,
o DC no último dia difere (anual menos curto): Faro +770,4756; Setúbal
+624,9498; Évora +617,8186; Beja +613,9239; Loures +519,5350. O FFMC final
coincide nestes exemplos. Não se pode inferir convergência do DC apenas
porque o FFMC estabilizou. Ver `sensibilidade_janela.json`. Um ano também
não constitui, por definição, garantia científica de estabelecimento.

## F. Falhas e lacunas

**Zero erros da fonte, retries, lacunas, duplicados, null/NaN/infinitos ou
negativos inválidos nos inputs usados e resultados persistidos.** Foram
verificados todos os dias, ligações ao anterior, snapshots e somas horárias.
Não houve saltos de dias nem reinicializações ocultas.

A falha encontrada é científica/de contrato da referência no limite RH=100,
não uma falha de recolha ou corrupção da BD. Todos os dados e resultados
originais foram preservados, sem aumentar tolerâncias.

## G. Comparação cffdrs 1.8.17 — bloqueio explícito

Amostra: **1003 dias/região/janela, 6018 comparações dos seis índices**.
Inclui extremos, maiores saltos e todos os dias sinalizados. Usa o estado
anterior persistido por dia; não é uma segunda reconstrução integral em R.

**5962 comparações passaram; 56 reprovaram**, em 18 dias de 12 regiões.
Tolerâncias mantidas: `atol=1e-8`, `rtol=1e-10`. Maior erro absoluto:
0,00029191273074502533. Erro relativo máximo 1, porque existem zeros xclim
comparados com valores positivos muito pequenos da referência.

Causa confirmada: em
`experiments/xclim_062/referencia_1_8_17/fwi.r:181`, a função pública aplica:

```r
rh[k] <- ifelse(rh[k] >= 100, 99.9999, rh[k])
```

O VIGA/xclim recebe RH=100 da fonte sem essa substituição. Todas as 56
reprovações desta amostra ocorreram precisamente com RH=100.

Exemplo Porto, 09/02/2026: T=13,8 °C; RH=100%; vento=15,1 km/h;
precipitação=15,3 mm; FFMC/DMC/DC anteriores=36,321056903429536 /
0,69107325 / 2,008.

| Índice | xclim | cffdrs público | Erro absoluto |
|---|---:|---:|---:|
| FFMC | 4,6897671513331645 | 4,68997509648213 | 0,00020794514896582683 |
| DMC | 0 | 0,00000211654500007026 | 0,00000211654500007026 |
| BUI | 0 | 0,00000423307976304751 | 0,00000423307976304751 |

Diagnóstico separado: foram chamadas as **funções internas originais** de R
com RH=100, sem modificar o seu código e sem o pré-processamento da função
pública. As 108 comparações desse diagnóstico passaram; maior erro absoluto
4,44×10⁻¹⁴. Isto localiza a causa, **não substitui nem aprova a comparação
original reprovada**. Não se alterou a humidade, fórmula ou biblioteca do VIGA.

Evidências: `divergencias.json`, `diagnostico_rh100.csv/.json`,
`365/*_comparacao.json`, inputs CSV e outputs R. O primeiro comparador
parou no Porto com código 1. Depois só se concluiu o diagnóstico offline
dos resultados já recolhidos. Nenhuma nova reconstrução foi iniciada após
essa falha. A discrepância conhecida com cffdrs 1.9.2 continua fora do alvo.

## H. Continente e ilhas

Nos novos ensaios continentais, todas as referências são 12:00 UTC e todas
as chuvas incluem exatamente os 24 intervalos terminados nessa hora.

As evidências da Fase 6 foram revalidadas offline:

- **Funchal/Madeira:** 60 dias, 1440 horas, 12:00 UTC.
- **Ponta Delgada/Açores:** 60 dias, 1440 horas, 13:00 UTC.

Checksums, cada intervalo horário e cada soma de precipitação passaram;
não se repetiu a recolha. Resultado: `evidencias/ilhas.json`.
São **pontos representativos do catálogo atual**, não cobertura integral
dos arquipélagos. Não se generalizam resultados a outras ilhas/altitudes.

## I. Desempenho medido

- 51 pedidos externos reais, sem retries ou falhas.
- 10 990 dias e 263 760 intervalos horários processados nas 51 sequências.
- Soma dos tempos internos de recolha: **23,099 s**.
- Soma dos tempos internos de inicialização/cálculo/persistência: **352,407 s**.
- Tempos dos runners completos: recolha curta 9,373 s; curta com API,
  idempotência, exportação e análise 64,684 s; recolha anual 15,597 s;
  anual com essas verificações 349,286 s. Soma desses quatro runners:
  **438,939 s**, cerca de 7 min 19 s, sem comparação R e diagnóstico posterior.
- Intervalo real da primeira ingestão ao último cálculo persistido:
  **1641,531 s**, cerca de 27 min 22 s, incluindo pausas entre etapas.
- Pico RSS máximo registado: **456,504 MiB**, do processo Python Linux.
  Não inclui BD, Docker ou consumo incremental exclusivo do xclim.

Os processos de várias regiões reutilizam imports/compilação. A medição
não equivale a iniciar um container por dia/região nem à recolha remota
diária do scheduler. Não se extrapola para o Dell Wyse. Métricas completas:
`evidencias/resumo.json` e `*/tempo_*.json`. O tempo `comparar` anual
regista só a execução bloqueada inicial, não o diagnóstico completo.

## J–K. Recomendação e investigação pendente

**Não avançar ainda para integração operacional.** A validação alargada
encontrou um caso-limite que não estava demonstrado pelos casos anteriores.
É necessária uma decisão explícita sobre o contrato científico para RH=100:
preservar o input físico no xclim e documentar a diferença perante a função
pública cffdrs, ou estudar outra opção compatível. Esta fase não escolhe nem
implementa essa alteração e não relaxa tolerâncias.

Regiões com reprovação nesta amostra: **Braga, Cascais, Coimbra, Gondomar,
Guarda, Guimarães, Loures, Matosinhos, Portalegre, Porto, Viana do Castelo e
Vila Nova de Gaia**. RH=100 pode ocorrer em qualquer região; esta lista não
garante que as restantes nunca enfrentem o mesmo caso.

Também requerem validação adicional:

- Faro, Setúbal, Évora, Beja e Loures: forte memória do DC ao comparar janelas;
  definir um critério de estabelecimento/convergência em vez de contar dias.
- Porto/Gaia/Matosinhos: representatividade espacial de uma célula partilhada.
- Madeira/Açores: só dois pontos do catálogo, sem cobertura de todo o arquipélago.
- Extremos continentais: comparação numérica passou, mas validação por
  estações meteorológicas ou outra fonte independente continua fora deste ensaio.

## Testes executados

`validar.py`: quatro testes; **três passaram e um reprovou**. Passaram
cobertura do catálogo, todas as cadeias/inputs e revalidação das ilhas.
O teste da comparação científica permanece reprovado, refletindo o bloqueio;
não foi alterado para aceitar a divergência. O comando terminou com código 1.
O diagnóstico RH=100 é separado e não altera esse resultado.

Não se repetiram provas ML, browser, build ou toda a ciência da Fase 1:
nenhum código de produção foi alterado. `git diff --check` e verificação
dos scripts e documentos novos concluídos; sem commit. As saídas brutas
de psql são preservadas literalmente, incluindo espaços de formatação.

### Conferência final offline

`verificar_fecho.py` confirmou a completude e integridade de **637 ficheiros
de evidência**, com manifesto de bytes/SHA-256 em
`evidencias/manifesto_fecho.json`. Resultado: `evidencias/verificacao_fecho.json`.
Não fez chamadas externas, não acedeu a qualquer BD e não recalculou FWI.

Passaram novamente os três controlos de integridade/cobertura/ilhas.
Foram conferidas as 6018 comparações guardadas, os seus erros e decisões
face às tolerâncias originais: **as mesmas 56 reprovações permanecem**,
em 18 dias de 12 regiões. Os inputs horários sobrepostos e as diferenças
guardadas das 26 comparações de janelas também foram confirmados.
O diagnóstico separado das 108 comparações internas RH=100 foi verificado;
não substitui a reprovação perante a função pública cffdrs.

`git diff --check` passou. Os scripts e documentos novos foram verificados
separadamente. A primeira tentativa de verificar todos os ficheiros novos
com `core.autocrlf=false` assinalou CRLF como whitespace e tratou incorretamente
o código de saída 1 de `diff --no-index` como falha geral; essa verificação
não era evidência de corrupção. Não se normalizaram respostas brutas ou
saídas de BD para esconder esses avisos. Nenhum ficheiro de produção mudou.

## L. Isolamento e produção

Container `viga-fwi-phase7-db`, PostGIS 15/3.3, rede `none`, sem portas,
com bases `viga_fwi_test_phase7_60` e `viga_fwi_test_phase7_365`.
Containers runners efémeros com `--rm`, imagem backend existente e imagem
R existente, sem build/deploy. Não foram usados volumes de produção.

No fim foram confirmadas 25/26 reconstruções com estado `reconstruido`
e zero linhas operacionais nas duas bases. O container/BDs descartáveis
foram removidos; inputs e snapshots continuam preservados nesta pasta.

Os IDs, imagens, instantes de arranque e RestartCount dos quatro containers
de produção foram comparados antes/depois, sem diferenças. Não se acedeu
à BD ou à API de produção. Os seus jobs habituais continuam independentes;
não se afirma que a BD de produção ficou congelada.

Ficheiros adicionais ao método: `auditar_divergencias.py` e
`diagnostico_rh100.R`, exclusivamente para documentar a reprovação,
e `verificar_fecho.py`, para a conferência offline final.
Nenhum texto público da aplicação foi criado ou alterado.
