# ML 5B.8 — fecho científico da linha experimental

14/10/2026. **ML 5B encerrado como linha experimental, sem validação operacional.**

O ML 5B demonstrou sinal preditivo experimental em avaliação temporal. Não existe evidência suficiente para considerar o modelo validado ou operacional. O candidato permanece congelado; nenhuma avaliação nova foi executada neste fecho. Os números abaixo foram transcritos dos JSONs históricos, sem recalcular métricas, gerar previsões ou retreinar.

## 1. Linha temporal e âmbito dos GO/NO-GO

| Fase | Resultado | Decisão e alcance |
|---|---|---|
| 5B | ANPC local insuficiente para target/cobertura | NO-GO inicial |
| 5B.1 | Junção meteorologia/FWI/eventos tecnicamente possível | GO técnico, NO-GO dataset completo |
| 5B.2 | Fonte individual SGIF/ICNF identificada | NO-GO certificado |
| 5B.2B | Três municípios com cobertura empírica e exclusões | GO condicionado retrospetivo |
| 5B.3 | Dataset elegível reproduzível | GO para treino experimental |
| 5B.4 | Benchmark temporal com sinal e degradação em 2024 | Sem validação operacional; teste consumido |
| 5B.5 | Robustez/ablação e candidato congelado | GO apenas para preparar futura validação externa |
| PRDF | Compatibilidade temporal; 2025 sem negativos certificados | NO-GO holdout |
| 5B.7 | Fontes adicionais não desbloqueiam cobertura | NO-GO holdout |
| 5B.8 | Consolidação e preservação de evidências | Encerramento experimental |

`linha_temporal.csv` liga cada fase ao relatório original. `inventario_artefactos.csv` enumera ficheiros/tamanhos/política de versionamento, sem ler datasets raw. Dependências, caches Python e ambientes são omitidos explicitamente no resumo. Artefactos de entrada, resultados e documentação histórica não foram alterados.

## 2. Target definitivo

**“Existência de uma nova ocorrência rural registada no município durante (T,T+24h], usando como referência temporal o timestamp operacional de alerta.”**

DHInicio não representa necessariamente o momento físico da ignição. Nos 24 170 eventos comuns SGIF/PRDF de 2022–2024, os valores de relógio coincidem exatamente. A descrição documental PRDF é alerta; não há evidência de que o treino tenha usado outro timestamp físico. Esta decisão corrige a interpretação, não reescreve labels históricos.

T=15:00 UTC. Conserva-se a análise Europe/Lisbon versus UTC: onde a presença na janela muda ou a interpretação temporal é ambígua, o resultado permanece null. O sufixo Z do PRDF não resolve retroativamente o fuso SGIF. A comparação anterior identificou 32 janelas sensíveis já tratadas como null.

## 3. Dataset consolidado

Origem: export SGIF/ICNF, registos ativos/eliminados, relações administrativas, reconciliação INE e verificação DGT. Municípios: Lisboa1106, Faro0805, Vila Real1714. Período candidato 2022–2024. Confiança territorial média; um ponto meteorológico por município não representa toda a sua área.

| Conjunto | Linhas | Positivos | Negativos condicionais | null |
|---|---:|---:|---:|---:|
| Completo | 3288 | 177 | 2644 | 467 |
| Elegível | 1693 | 132 | 1561 | 0 |
| Excluído, preservado para auditoria | 1595 | 45 | 1083 | 467 |

Prevalência elegível: 7,7968%. Não confundir 467 null do inventário com linhas usadas no treino. Lisboa/2024 contém 366 null e não entra no teste. Motivos sobrepostos: 1174 dias sensíveis à semente, 467 target null, 431 cobertura não aceite e nove horizontes que atravessam o limite anual. Não somar motivos como se fossem exclusivos.

Taxonomia: Florestal/Agrícola; exclusão de eliminados, duplicados identificados, reacendimentos por marcadores/parentesco/causa711 e eventos não equivalentes. Mantêm-se as regras versionadas em 5B.2B/5B.3; não se deduz nova ocorrência por área ardida ou meios. Negativos são condicionais à cobertura empírica aprovada nesse subconjunto, não ausência física de incêndio garantida.

O inventário completo tem zero gaps/duplicados/features inválidas conforme `dataset_5b3/qualidade.json`. Lacunas no elegível são exclusões deliberadas. Nenhuma tabela foi reconstruída neste fecho.

## 4. Features, FWI e leakage

Features finais, na ordem da configuração: temperatura, humidade, vento, precipitação_24h, FFMC, DMC, DC, ISI, BUI, FWI, mês, dia do ano, dia da semana, época do ano e município. Município e época são categorias/contexto, não ordens numéricas nem relações causais.

Meteorologia/FWI têm referência continental às 12:00 UTC, hora padrão mesmo no verão; emissão T às15:00 UTC. Precipitação agrega os24 intervalos terminados entre13:00 UTC do dia anterior e12:00 UTC do próprio dia. O pipeline FWI usa xclim0.62.0, variante clássica validada contra cffdrs1.8.17, RH100% preservada e estado anterior cronológico. Divergência conhecida com cffdrs1.9.2 não foi corrigida artificialmente.

Prefixo a partir de01/10/2021, semente85/6/15. Os92 dias antes de2022 não foram considerados automaticamente suficientes. O dataset conservou apenas dias insensíveis às27 combinações testadas sob a tolerância experimental existente; não é uma certificação universal de estabelecimento. O relatório5B.3 documenta comparação do prefixo com erro máximo0. Este fecho não repetiu o cálculo.

Proibidos como features: área/perímetro final PBA, duração, resolução/extinção, estado final, causa final, meios mobilizados depois do evento, FRP futuro, meteorologia durante/depois do incêndio e qualquer informação posterior aT. A classificação retrospectiva do evento serve ao target, não às covariáveis.

Confirmação limitada e rastreável: a allowlist em `modelo_5b4/comum.py`, a seleção temporal em `modelo_5b5/experimento.py`, os checks históricos e os manifestos preservados sustentam a separação de features, preprocessing e horizontes. Não se executaram esses pipelines novamente. **valid_time≤T não prova disponibilidade operacional emT:** Archive/IFS pode conter assimilação/revisões posteriores. Portanto, este é estudo retrospetivo, não simulação comprovada de previsão em tempo real.

## 5. Metodologia temporal

5B.4: treino2022=373 linhas/51 positivos; validação2023=722/40; teste2024=598/41. Prevalências13,67%,5,54%,6,86%. Seleção em Vila Real/2023; thresholds na validação, sem ajuste no teste. Lisboa não tem elegíveis2024; Faro só aparece em2024. Não houve random split como avaliação principal nem troca pós-hoc para outro modelo após observar o teste.

5B.5:1095 linhas elegíveis2022–2023, quatro folds rolling-origin. Cada fold separa ajuste expansivo, bloco posterior para calibração/threshold e avaliação exterior seguinte, com purga de horizontes nas fronteiras. Folds exteriores: outubro–dezembro2022, abril–junho2023, julho–setembro2023, outubro–dezembro2023. Os treinos sobrepõem-se; os folds não são independentes.

Foram comparadas61 configurações, incluindo baseline, logística, HGB e RF, ablações meteorologia/FWI/calendário/município, pesos e sigmoid. Isotonic não foi aplicada por amostra insuficiente. Seleção pelo pior ganho AP, seguida de critérios de desenvolvimento predefinidos. Threshold maximiza F1 no bloco interno de Vila Real; não define custos operacionais adequados.

**2024 continua observado e consumido.** A sua transcrição neste relatório é documental, não uma nova avaliação/seleção. O candidato5B.5 nunca foi avaliado externamente; as métricas2024 abaixo pertencem ao artefacto5B.4, não ao atual.

## 6. Resultados históricos consolidados

AP significa average precision, não integração trapezoidal. Valores completos em CSVs pequenos extraídos dos JSONs originais.

### 5B.4 — Vila Real/2024, 328 linhas, 30 positivos

| Modelo | Threshold | AP | ROC-AUC | Precision | Recall | F1 | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prevalência | 0,13 | 0,09146 | 0,50000 | 0,09146 | 1,00000 | 0,16760 | 0,08515 |
| Logística | 0,20 | 0,29187 | 0,79150 | 0,20833 | 0,50000 | 0,29412 | 0,07600 |
| HGB selecionado em2023 | 0,28 | 0,16300 | 0,71532 | 0,19444 | 0,23333 | 0,21212 | 0,09314 |
| Random Forest | 0,24 | 0,28569 | 0,80201 | 0,25455 | 0,46667 | 0,32941 | 0,07499 |

Matriz HGB `[[TN,FP],[FN,TP]]=[[269,29],[23,7]]`. AP superior ao baseline, mas degradação relativamente à validação; Brier pior que baseline e apenas7/30 positivos detetados. Logística/RF melhores em2024 não justificam escolhê-las depois de observar esse teste. Baseline AP≈0,0915 é prevalência do conjunto avaliado; o score constante foi ajustado à prevalência do treino≈0,1367.

### 5B.5 — candidato nos folds de desenvolvimento, Vila Real

| Métrica | Média | Pior | Melhor |
|---|---:|---:|---:|
| AP | 0,25765 | 0,16848 | 0,29000 |
| ROC-AUC | 0,75615 | 0,58323 | 0,86517 |
| Brier | 0,07162 | 0,11475 | 0,02074 |
| Precision | 0,20617 | 0,12500 | 0,37500 |
| Recall | 0,35664 | 0,15385 | 0,50000 |
| F1 | 0,22617 | 0,16667 | 0,31579 |

Em Brier, menor é melhor. AP supera baseline nos quatro folds, mas dois têm apenas2 positivos. Thresholds internos0,21/0,36/0,27/0,16 variam; não são o threshold final0,15. Sigmoid piora Brier no primeiro fold e não melhora uniformemente todos os cenários. Selecionar o vencedor entre61 variantes usando estes folds introduz otimismo. Não são métricas externas do artefacto final.

## 7. Candidato congelado e interpretação

Confirmação final (15/10/2026): as métricas de 2024 do HGB selecionado no ML 5B.4 correspondem ao threshold **0,28**. O candidato congelado posteriormente no ML 5B.5 usa **HistGradientBoosting + sigmoid + threshold 0,15** e **não foi avaliado em 2024 nem em 2025**. As métricas de 2024 não podem, portanto, ser atribuídas ao candidato congelado atual. Mantém-se **NO-GO para validação operacional** e a designação **score experimental**.

**CANDIDATO EXPERIMENTAL CONGELADO**: HistGradientBoosting, featuresE, sem pesos de classe, sigmoid, threshold0,15, seed42. Fit final antes de01/07/2023, após purga até29/06; segundo semestre2023 de Vila Real reservado para calibração/threshold. Não houve refit posterior.

SHA-256 do artefacto: `7c358a2b32fe0360e4250c6240633f418de16a98e7d9d12d3d3d6c21a0b2bd04`. Hash conferido sem desserializar o joblib. `estado_modelo.json` preserva versões, features e configuração; `integridade_historica.json` compara ficheiros com os manifestos de5B.4/5B.5. Todos coincidem.

Linguagem permitida: **score experimental de ocorrência rural registada nas próximas24h**, modelo experimental, sinal preditivo observado em avaliação temporal. Não usar probabilidade de incêndio, modelo validado, previsão operacional ou sistema de alerta ML certificado. Calibração sigmoid não constitui por si certificação probabilística.

## 8. Porque2025 não desbloqueou a validação

PRDF2025 tem8252 ocorrências,7579 novas ocorrências rurais potenciais,668 reacendimentos e5 Queimas. Deriva/harmoniza ICNF/SGIF; não é fonte independente de ocorrências. METEO é centrado no evento e não fornece features ex ante/negativos; FRP apenas apoio a positivos, PBA validação espacial.

Lisboa/Faro/Vila Real:73 positivos potenciais,0 negativos certificados,1022 null. ML5B.7 mantém36 blocos município×mês DUVIDOSO e redução de null0. SADO tem relevância operacional mas não foi obtido histórico público completo verificável; INE2025 permanece provisório/derivado; foi documentada divergência de reacendimentos entre SGIF e SADO. EFFIS/FIRMS não certificam ausência. **NO-GO para construir/avaliar holdout2025 neste momento.**

## 9. Inconsistências documentais esclarecidas, sem reescrever história

- “Ignição” nos relatórios iniciais passa a ser interpretada como ocorrência registada com timestamp operacional de alerta; não se altera o instante nem resultados.
- “2024 nunca avaliado” na nota config5B.5 significa **nessa fase**, não em todo o projeto:5B.4 já o consumiu.
- GO em5B.2B/5B.3/5B.5 tem alcance experimental restrito; não contradiz NO-GO para holdout2025 ou operacionalização.
- Threshold0,28 e matriz2024 pertencem ao modelo5B.4; threshold0,15 pertence ao candidato5B.5. Não misturar avaliações.
- 3288 linhas completas não são1693 elegíveis; 177 positivos brutos não são132 usados. Exclusões sobrepostas não se somam.
- Média de folds é seleção interna descritiva, não validação externa. “Score calibrado” não implica probabilidade operacional.
- A documentação inicial de2016–2020 não é o período final: o estudo utilizável foi restringido a2022–2024.

Não foi encontrada divergência dos resultados/modelos face aos manifestos históricos. Relatórios originais e nomenclatura histórica foram preservados. As limitações restantes estão enumeradas em `limitacoes.md`.

## 10. Condições para retomar

Obter histórico consolidado SADO/ANEPC e documentação oficial de cobertura; reconciliar eliminados/falsos eventos/reacendimentos; esclarecer fuso; construir novo holdout não usado, com positivos e negativos defensáveis; aprovar previamente população, métricas e critérios; avaliar o candidato congelado uma única vez. Só depois de estabilidade e calibração aceitáveis ponderar integração experimental, sem confundir com validação operacional.

Não há autorização implícita para procurar mais dados, voltar a2024, avaliar2025, retreinar ou integrar. Próximo passo no VIGA: revisão deste fecho e do versionamento seletivo, mantendo a aplicação e o FWI fora de alterações desta linha ML.

## 11. Reprodutibilidade, Git e segurança

`validar_fecho.py` verifica hashes/configuração e extrai tabelas de métricas existentes. Não importa joblib/sklearn nem executa treino. O inventário usa apenas tamanho/caminho dos raw; dependências e caches são omitidos. Modelos são apenas lidos como bytes para SHA-256. As dependências originais do treino estão em `estado_modelo.json`; nenhuma foi instalada neste fecho.

`commit_recomendado.txt` é a lista exata de caminhos candidatos, para revisão humana posterior; não é um comando de staging. Inclui código/documentação e pequenos resumos necessários à rastreabilidade, excluindo datasets completos/elegíveis/exclusões, rawPRDF/SGIF, scores por linha, joblib experimentais, caches, PDFs/binários e dependências isoladas. `fora_commit.csv` detalha os ficheiros observados que ficam fora. `.gitignore` global preexistente e `operations/` não fazem parte desta recomendação ML.

Conservar os joblib e dados ignorados num arquivo local/externo com hashes: o Git documental sozinho não contém o candidato nem permite reconstruir os dados sem os originais. Não remover duplicados/caches automaticamente. Referências a artefactos locais nos manifestos são intencionais e não significam que esses dados devam ser publicados.
