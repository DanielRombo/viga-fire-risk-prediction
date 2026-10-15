# ML 5B.4 — treino experimental e avaliação temporal

13/10/2026. Quatro modelos experimentais treinados em isolamento; nenhum modelo oficial substituído. Sem treino adicional após consulta do teste, sem produção, API, frontend, deploy ou commit.

## Estratégia congelada

Treino combinado Lisboa/Vila Real em 2022; seleção principal em Vila Real/2023; teste longitudinal Vila Real/2024 e avaliação separada de transferência Faro/2024. Lisboa não tem linhas elegíveis em 2024. Não houve random split ou ajuste com 2024. Mantivemos os modelos ajustados apenas em 2022, sem refit em treino+validação, para preservar a escala em que o threshold foi escolhido.

| Split | Linhas | Positivos | Negativos | Prevalência |
|---|---:|---:|---:|---:|
| Treino 2022 | 373 | 51 | 322 | 13,67% |
| Validação 2023 | 722 | 40 | 682 | 5,54% |
| Teste 2024 | 598 | 41 | 557 | 6,86% |

O treino contém 354 linhas de Vila Real (51 positivas) e 19 de Lisboa (todas negativas). Validação: Vila Real 360/34 positivas, Lisboa 362/6. Teste: Vila Real 328/30, Faro 270/11. Lisboa no teste e Faro na validação são explicitamente indisponíveis, não zeros. A seleção dos dias por convergência FWI e cobertura altera a distribuição entre anos e municípios.

## Modelos

Seed 42. Baseline constante = 51/373 = 0,136729. Logística L2, C=1, máximo 2000 iterações. HistGradientBoosting com 100 iterações, 7 folhas, mínimo 20 amostras/folha, regularização L2=1 e early stopping desligado (sem split aleatório interno). Random Forest com 200 árvores, profundidade 5, mínimo 10 amostras/folha e max_features=sqrt. Sem pesquisa de hiperparâmetros.

Todos usam pipeline ajustado só no treino: standardização numérica e one-hot de município/época do ano. A standardização não é necessária para árvores mas não acrescenta ajuste fora do treino. Sem class_weight para avaliar primeiro scores naturais; o desequilíbrio é tratado na avaliação e no threshold, sem otimizar accuracy. Sem SMOTE/oversampling. Faro é categoria desconhecida, codificada em zeros municipais; não é convertido para Lisboa ou Vila Real.

Features: temperatura, humidade, vento, precipitação passada, FFMC/DMC/DC/ISI/BUI/FWI, município, mês, dia do ano, dia da semana e época do ano. Ficheiros de metadados/ocorrências não entram no estimador. Não foram adicionadas dependências.

## Seleção e thresholds

PR-AUC neste relatório significa **average precision (AP)**, integração em degraus da curva precision-recall, não área trapezoidal. O baseline constante tem AP igual à prevalência do conjunto avaliado; não à prevalência usada para o seu score constante.

Critério declarado antes do teste: maior AP em Vila Real/2023; desempate por menor Brier. Threshold escolhido na grelha 0,01–0,99 pelo maior F1, com desempate pelo maior threshold. F1 é um critério experimental, não uma função de custos aprovada para alertas de incêndio. As 396 combinações/modelo-threshold estão em `thresholds_validacao.csv`.

| Modelo | AP validação Vila Real | Threshold | Precision validação | Recall validação | F1 validação |
|---|---:|---:|---:|---:|---:|
| Prevalência | 0,0944 | 0,13 | 0,0944 | 1,0000 | 0,1726 |
| Logística | 0,2206 | 0,20 | 0,2178 | 0,6471 | 0,3259 |
| HistGradientBoosting | 0,3039 | 0,28 | 0,4054 | 0,4412 | 0,4225 |
| Random Forest | 0,2780 | 0,24 | 0,2625 | 0,6176 | 0,3684 |

**Selecionado antes do teste: HistGradientBoosting, threshold 0,28.** O baseline prevê todos como positivos no seu threshold otimizado; não é um erro de execução. Não se escolheu threshold 0,5 por conveniência.

## Teste 2024 — Vila Real, avaliação principal

| Modelo | ROC-AUC | AP | Precision | Recall | F1 | Brier |
|---|---:|---:|---:|---:|---:|---:|
| Prevalência | 0,5000 | 0,0915 | 0,0915 | 1,0000 | 0,1676 | 0,08515 |
| Logística | 0,7915 | 0,2919 | 0,2083 | 0,5000 | 0,2941 | 0,07600 |
| HistGradientBoosting, selecionado | 0,7153 | 0,1630 | 0,1944 | 0,2333 | 0,2121 | 0,09314 |
| Random Forest | 0,8020 | 0,2857 | 0,2545 | 0,4667 | 0,3294 | 0,07499 |

O modelo selecionado tem AP 1,78× o baseline mas cai de 0,3039 para 0,1630. A ordenação entre modelos muda. Não trocámos para logística/Random Forest depois de consultar 2024: esses resultados são comparações descritivas do benchmark, não uma segunda seleção válida. Balanced accuracy do selecionado: 0,5680. Matriz `[[TN,FP],[FN,TP]]`: **[[269,29],[23,7]]**. Deteta apenas 7 dos 30 positivos no threshold congelado: insuficiente para um sistema de alerta.

## Resultados municipais e globais do selecionado

| Âmbito | ROC-AUC | AP | Precision | Recall | F1 | Brier | Balanced accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Global 2024 | 0,6535 | 0,1075 | 0,1262 | 0,3171 | 0,1806 | 0,08498 | 0,5777 |
| Vila Real 2024 | 0,7153 | 0,1630 | 0,1944 | 0,2333 | 0,2121 | 0,09314 | 0,5680 |
| Faro 2024 | 0,6841 | 0,0971 | 0,0896 | 0,5455 | 0,1538 | 0,07508 | 0,6550 |
| Lisboa 2023, apenas validação | 0,7495 | 0,0396 | 0,0482 | 0,6667 | 0,0899 | 0,06475 | 0,7224 |

Matrizes: global [[467,90],[28,13]], Faro [[198,61],[5,6]], Lisboa/2023 [[277,79],[2,4]]. Lisboa/2024: não calculável, sem linhas. Resultados de todos os modelos por município, incluindo bins e ausências, em `metricas_validacao.json`, `metricas_teste.json` e `metricas.csv`.

## Calibração e explicabilidade

Não interpretar os scores como probabilidades calibradas. Em Vila Real, o Brier do selecionado é pior que o baseline (0,09314 vs 0,08515). O bin [0;0,1[ tem score médio 0,0209 mas frequência observada 0,0628 (239 amostras); em [0,6;0,7[ o score médio é 0,6326, com zero positivos em apenas cinco amostras. Bins altos são escassos e não sustentam uma curva estável. `fiabilidade.svg` e bins JSON permitem revisão; bins vazios são null, nunca zero.

Decisão prévia: não ajustar Platt/isotonic nesta primeira experiência, porque a pequena validação já serve a seleção de modelo/threshold e não há bloco de calibração reservado. Não usar 2024 para o fazer. Uma experiência futura de calibração requer partição temporal própria e novo período de teste intocado; não reutilizar repetidamente 2024 como holdout independente.

Permutation importance do selecionado foi calculada apenas na validação Vila Real, dez repetições, queda de AP: FWI 0,0575±0,0414; dia do ano 0,0540±0,0280; humidade 0,0394±0,0315; temperatura 0,0274±0,0153; dia da semana 0,0136±0,0139. Coeficientes logísticos padronizados incluem FFMC +1,124, temperatura +0,554, humidade −0,485 e FWI −0,798. O sinal negativo de FWI não prova efeito protetor: há forte correlação com os seus componentes e sazonalidade, amostra pequena e possíveis efeitos de seleção. Permutações isoladas também podem criar combinações fisicamente improváveis; não são causalidade nem ablação independente do benefício do FWI.

## Leakage, reprodutibilidade e limitações

Checks: seleção explícita de features; nenhum ano de 2024 passado ao fit; scaler comparado diretamente com médias de 2022; encoder só contém municípios vistos em 2022; thresholds verificados contra a grelha de 2023; modelos/scripts/config/dataset com hashes congelados antes do teste. Sem calibração no teste. `avaliar.py` recusa sobrescrever uma avaliação já existente. O teste foi executado uma vez para os quatro modelos com as decisões congeladas.

Estas garantias são de separação algorítmica. Não resolvem disponibilidade histórica: Archive é retrospectivo e pode ter assimilação/revisões posteriores a T. A cobertura também foi avaliada retrospectivamente. Não afirmar ausência total de leakage operacional. O alvo é ocorrência rural registada, os negativos são condicionais, a confiança territorial é média, e a população selecionada por convergência/cobertura pode não representar todos os dias. As 30 ignições positivas de Vila Real no teste e 11 em Faro dão elevada incerteza; não foram demonstradas significância estatística nem robustez plurianual. Não apresentar diferenças pequenas entre modelos como conclusivas.

Versões efetivamente usadas: Python 3.11.17, NumPy 2.4.4, pandas 3.0.6, scikit-learn 1.8.0, joblib 1.5.3, SciPy 1.17.1. Mantida a imagem existente; nenhum pacote instalado ou atualizado. Os joblib ficam apenas nesta pasta, ignorados pelo Git.

## Decisão

**NO-GO para considerar o modelo selecionado validado e avançar à sua utilização.** A AP temporal supera o baseline e há sinal que justifica continuar a investigação; contudo, a degradação, o recall baixo, a calibração fraca e a mudança de ordenação dos modelos não satisfazem uma interpretação robusta do critério de estabilidade pedido. Este NO-GO não significa abandonar o projeto: significa que esta experiência não valida um modelo final. Não há GO para integração, alertas ou probabilidade operacional.

Designação recomendada: **score experimental de ocorrência rural registada nas próximas 24 horas, em estudo retrospetivo**. Próximo passo: ampliar avaliação temporal e preservar um novo holdout, analisar representatividade/seleção e reservar dados para calibração. Não promover o melhor resultado descritivo de 2024 a modelo vencedor sem nova avaliação independente.

Validação final: **7/7 testes aprovados** em contentor isolado, repositório só para leitura. Testam splits, hashes, scaler/encoder só no treino, thresholds congelados, baseline, casos sem classes e totais das matrizes/bins. `git diff --check` sem erros. O sucesso dos testes de implementação não altera o NO-GO científico.
