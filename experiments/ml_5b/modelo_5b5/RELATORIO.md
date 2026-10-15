# ML 5B.5 — robustez temporal e candidato de desenvolvimento

13/10/2026. **Um candidato congelado, pronto para validação externa futura, mas NÃO validado.** Saída: score experimental. Sem produção, integração, alteração de modelos oficiais, deploy ou commit.

## Separação temporal

Foram usadas exclusivamente as 1095 linhas elegíveis de 2022–2023. O CSV de origem contém 2024; o leitor filtra o ano antes de construir arrays/features/estatísticas. Não se carregaram os resultados nem os modelos de 5B.4. Só foram reutilizadas funções puras de métricas, com hash registado.

Cada fold tem três blocos: ajuste expansivo; bloco seguinte para sigmoid e threshold; avaliação exterior posterior. Excluem-se horizontes que atravessam a fronteira seguinte. Não há random split, SMOTE, early stopping aleatório ou refit depois da calibração. O threshold usa F1 de Vila Real no bloco interno, grelha 0,01–0,99, desempate pelo maior threshold. Sigmoid e threshold partilham esse bloco interno; o seu desempenho nesse bloco não é reportado como avaliação independente.

| Fold | Ajuste até* | Calibração/threshold | Avaliação exterior | n fit / cal / avaliação total | Avaliação Vila Real: n / positivos |
|---|---|---|---|---|---|
| F1 | junho 2022 | julho–setembro 2022 | outubro–dezembro 2022 | 171 / 90 / 110 | 91 / 2 |
| F2 | setembro 2022 | outubro 2022–março 2023 | abril–junho 2023 | 262 / 286 / 178 | 88 / 11 |
| F3 | março 2023 | abril–junho 2023 | julho–setembro 2023 | 549 / 178 / 180 | 91 / 13 |
| F4 | junho 2023 | julho–setembro 2023 | outubro–dezembro 2023 | 729 / 180 / 182 | 91 / 2 |

*Datas exatas após purga em `folds.json`. A calibração e escolha de threshold usam apenas o subconjunto Vila Real dos blocos indicados. Avaliação principal Vila Real; Lisboa é diagnóstico secundário. Faro não tem linhas de desenvolvimento elegíveis. Os períodos de avaliação exteriores não se sobrepõem; um período avaliado num fold pode entrar legitimamente no treino de um fold posterior. Os folds não são independentes porque os treinos se sobrepõem.

2022–2023 já tinham sido usados no desenvolvimento anterior: não são uma nova validação externa. **2024 foi consumido como teste em 5B.4 e não voltou a ser avaliado nem usado para escolher qualquer decisão nesta fase.** Não há comparação pós-hoc com métricas de 2024 neste relatório.

## Experiências e regra de seleção

61 configurações × quatro folds: baseline mais três modelos × cinco conjuntos de features × duas ponderações × duas calibrações. Modelos: logística, HGB, Random Forest. Hiperparâmetros fixos, descritos no README/código; seed 42. Class weighting: None ou balanced, calculado só no fit. Baseline: prevalência do fit, sem class weighting. StandardScaler/one-hot ajustados só no fit; médias conferidas em execução.

A: meteorologia; B: seis índices FWI; C: A+B; D: C+calendário; E: D+município. Município é categoria, não ID numérico ordinal. E testa diferenças de taxa de base na aprendizagem combinada; não demonstra capacidade de extrapolação territorial. Há folds com um só município no fit. Categorias desconhecidas recebem vetor one-hot zero, sem atribuição arbitrária a outro município.

Sigmoid: logística regularizada C=1 sobre logit dos scores (clip 1e−6), ajustada após o fit, no bloco interno de Vila Real. Isotonic não foi executada: poucos positivos por janela para estimar degraus de forma fiável. Não há dados do fold exterior na calibração ou no threshold.

Regra pré-fixada em `config.json`: AP acima do baseline em **todos** os quatro folds de Vila Real e mediana do ganho de Brier positiva. Prioridade: maior pior ganho AP; depois mediana AP e ganho Brier. São critérios de triagem de desenvolvimento, não testes de significância ou garantias científicas. 34 configurações passaram a triagem. A procura entre 61 configurações induz otimismo de seleção; por isso é indispensável novo holdout.

## Estabilidade por modelo

Melhor configuração de cada família pela regra de robustez, não simplesmente pela média. AP = average precision, não integração trapezoidal.

| Família / configuração | AP média | Mediana | Desvio amostral | Pior AP | Melhor AP | Pior ganho AP vs baseline |
|---|---:|---:|---:|---:|---:|---:|
| Prevalência | 0,0780 | 0,0735 | 0,0650 | 0,0220 | 0,1429 | 0 |
| Logística, A, balanced, sigmoid | 0,2332 | 0,1841 | 0,1393 | 0,1270 | 0,4377 | 0,0461 |
| HGB, E, sem pesos, sigmoid | 0,2577 | 0,2861 | 0,0595 | 0,1685 | 0,2900 | 0,1434 |
| RF, B, sem pesos, sem calibração | 0,2629 | 0,2840 | 0,0834 | 0,1484 | 0,3353 | 0,1264 |

RF tem média ligeiramente maior, mas pior margem no fold mais desfavorável. Foi selecionado **HGB E sem pesos, sigmoid**. `estabilidade.json` contém média, mediana, desvio amostral, pior e melhor para AP, ROC-AUC, Brier, precision, recall e F1 de **todas** as configurações. Média e desvio são descritivos; não constituem intervalos de confiança com quatro folds autocorrelacionados.

## Resultados do candidato nos folds exteriores

| Fold | Threshold interno | AP | ROC-AUC | Brier | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| F1 | 0,21 | 0,1685 | 0,8652 | 0,04146 | 0,1250 | 0,5000 | 0,2000 |
| F2 | 0,36 | 0,2859 | 0,5832 | 0,10954 | 0,3750 | 0,2727 | 0,3158 |
| F3 | 0,27 | 0,2862 | 0,7110 | 0,11475 | 0,1818 | 0,1538 | 0,1667 |
| F4 | 0,16 | 0,2900 | 0,8652 | 0,02074 | 0,1429 | 0,5000 | 0,2222 |

| Métrica | Média | Mediana | Desvio | Pior | Melhor |
|---|---:|---:|---:|---:|---:|
| AP | 0,2577 | 0,2861 | 0,0595 | 0,1685 | 0,2900 |
| ROC-AUC | 0,7562 | 0,7881 | 0,1363 | 0,5832 | 0,8652 |
| Brier | 0,07162 | 0,07550 | 0,04760 | 0,11475 | 0,02074 |
| Precision | 0,2062 | 0,1623 | 0,1150 | 0,1250 | 0,3750 |
| Recall | 0,3566 | 0,3864 | 0,1725 | 0,1538 | 0,5000 |
| F1 | 0,2262 | 0,2111 | 0,0640 | 0,1667 | 0,3158 |

F1/F4 só têm dois positivos: AP/recall podem mudar muito com uma ocorrência. A AP acima do baseline não torna o recall adequado a alertas. Os thresholds internos variam de 0,16 a 0,36, sinal de sensibilidade temporal, e não de um ponto de operação estável certificado.

## Ablação sem confundir troca de modelo com troca de features

Comparação mantendo HGB, ausência de pesos e sigmoid fixos:

| Features | AP média | Pior ganho AP | Mediana ganho Brier vs baseline |
|---|---:|---:|---:|
| A — meteorologia | 0,1614 | 0,0498 | 0,00156 |
| B — FWI | 0,2090 | 0,0519 | 0,00107 |
| C — meteorologia + FWI | 0,2202 | 0,0950 | 0,00519 |
| D — C + calendário | 0,2326 | 0,1266 | 0,00471 |
| E — D + município | 0,2577 | 0,1434 | 0,00496 |

Há sinal nas duas famílias físicas e benefício descritivo ao combiná-las/calendário. O ganho de E não prova efeito causal do município: composição desigual, Lisboa com poucos positivos, e apenas Vila Real na avaliação principal. Não generalizar a Faro ou a municípios sem treino. A ablação completa para os outros modelos/ponderações/calibrações está nos JSON/CSV.

## Drift observado, sem correção artificial

Prevalência global 2022→2023: 13,67%→5,54%. Vila Real: 51/354=14,41%→34/360=9,44%. Lisboa: 0/19 em dezembro→6/362 no ano seguinte. A proporção de Lisboa passa de 5,09% para 50,14%: grande parte do drift global é de composição, não apenas de meteorologia. Faro não está representado. `composicao.json` discrimina meses/municípios; não foi feito reweighting sazonal ou geográfico para ocultar esta mudança.

Vila Real, médias 2022→2023: temperatura 18,48→17,63 °C; humidade 60,06→62,69%; vento 10,15→9,84 km/h; chuva anterior 3,47→4,22 mm; FWI 10,43→8,09 (mediana 3,90→1,49). Estatística KS descritiva FWI=0,1184; diferenças padronizadas em `drift.csv`. Não se reportam p-values como se os dias fossem independentes. A disponibilidade seletiva por convergência FWI/cobertura pode enviesar essas distribuições.

## Calibração e importância

Brier HGB E sem pesos, sem→com sigmoid: F1 0,03072→0,04146 (piora), F2 0,11309→0,10954, F3 0,12539→0,11475, F4 0,02099→0,02074. Brier do baseline: 0,03997 / 0,11322 / 0,12370 / 0,02698. Logo a calibração não melhora uniformemente nem vence sempre o baseline. Reliability bins completos, com número de exemplos e null em bins vazios, em `resultados_folds.json`. Não chamar ao resultado probabilidade calibrada operacional.

Permutation importance apenas no desenvolvimento, dez repetições por fold, AP do pipeline base: ISI, média 0,0337 (−0,0110 a 0,1112); vento 0,0318 (−0,0538 a 0,1329); BUI 0,0133 (−0,0001 a 0,0367); dia do ano 0,0076 (0 a 0,0303). Mudanças de sinal/ordenação mostram importância instável. O ficheiro guarda cada feature/fold e desvio das permutações. Permutar features correlacionadas pode criar meteorologia impossível; não é causalidade. Município é constante na avaliação Vila Real e a sua permutação aí não mede a contribuição do treino combinado.

## Candidato final congelado

`candidato.joblib`: pipeline de preprocessing + HGB, class_weight=None, features E, calibrador sigmoid. Seed 42. HGB: max_iter=100, max_leaf_nodes=7, min_samples_leaf=20, l2_regularization=1, early_stopping=False. Final fit apenas até 29/06/2023 (729 linhas), reservando julho–dezembro de 2023 de Vila Real para sigmoid/threshold. Não refit posterior a essa calibração. Threshold final **0,15**, maximiza F1 nessa reserva; não é a média dos thresholds dos folds nem foi escolhido em 2024. O ajuste final reutiliza desenvolvimento e não cria uma nova métrica externa.

Estado: **GO limitado à preparação de validação externa futura; candidato NÃO validado**. O objetivo deste bloco é encontrar candidato para novo teste, não demonstrar desempenho futuro. Os mesmos quatro folds foram usados para escolher entre 61 variantes; os resultados do vencedor são otimistas. Não repetir afinações depois de ver o futuro teste. A calibragem/threshold permanecem experimentais, sem custos operacionais definidos.

## Novo holdout

Só foram inspecionados metadados INE já guardados (`ine_13512_meta`, atualização 30/05/2026, recolha 12/10/2026). Os totais de Lisboa/Faro/Vila Real em 2025 têm marcador `&`, descrito como **Dado provisório**. `holdout_futuro.json` conserva URL/hash e a limitação. Não foram obtidos novos dados, reconciliados eventos de 2025, construídos labels ou calculadas previsões. Não afirmar que o estado atual remoto é diferente do snapshot: não foi feita nova consulta.

2025 é a primeira opção, mas **não há ainda holdout válido certificado**. Os totais/metadados de 2025 já foram vistos nas fases anteriores: não é informação totalmente desconhecida, embora as previsões/erros do candidato nesse período não tenham sido consultados. Plano: congelar este artefacto/configuração; auditar cobertura/taxonomia/revisões/território de 2025 sem scores do candidato; certificar negativos e período completo; reconstruir features com as mesmas regras; só depois uma avaliação única. Dar preferência inicial à continuidade Vila Real; tratar Faro/Lisboa separadamente. Se a cobertura continuar insuficiente, reservar um período posterior consolidado ou recolha prospetiva, sem reutilizar 2024 como novo teste.

Archive é retrospectivo: valid_time anterior a T não prova publicação em T. Para validação de operação real será preciso registar inputs/instantes de ingestão prospectivamente. Persistem negativos condicionais, confiança territorial média, poucos positivos e enviesamento da seleção de dias.

## Verificação e ficheiros

Seis testes aprovados: anos permitidos, purga/ordem e ausência de sobreposição exterior, baseline/bins/matrizes, 61 configurações com quatro folds, critério da decisão e hashes. `git diff --check` passou. Não foram repetidos treinos/testes de 2024. Nenhuma tabela, serviço ou ficheiro de produção foi alterado.

Nesta pasta: `config.json`, `experimento.py`, `test_temporal.py`, `folds.json`, `resultados_folds.json`, `metricas_folds.csv`, `estabilidade.json`, `decisao.json`, `importancia.json`, `drift.csv`, `composicao.json`, `versoes.json`, `manifesto.json`, `holdout_futuro.json`, README/relatório e artefacto local ignorado. Hashes finais também em `entrega_checksums.json`. Versões mantidas na imagem existente, sem instalar dependências.
