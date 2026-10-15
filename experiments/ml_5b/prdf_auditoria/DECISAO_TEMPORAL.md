# Verificação metodológica dirigida — 14/10/2026

**Decisão posterior aprovada pelo utilizador:** adotar “Existência de uma nova ocorrência rural registada no município durante (T,T+24h], usando como referência temporal o timestamp operacional de alerta.” Preservar a convenção dupla e null em casos ambíguos. A auditoria integral foi autorizada a prosseguir; não há autorização para avaliar o candidato. As menções abaixo a decisão pendente/paragem descrevem a conclusão histórica da verificação dirigida, não um bloqueio atual.

## Conclusão

**COMPATÍVEL — caso A para o timestamp operacional registado, com ressalva obrigatória sobre fuso.** Há identidade exata de IDs e valores de relógio entre o DHInicio SGIF efetivamente usado e o DHInicio PRDF em 2022–2024. Não existe evidência de que o desenvolvimento tenha usado um timestamp físico de ignição separado. A documentação PRDF chama ao mesmo campo data/hora do alerta. A conclusão é sobre compatibilidade com o alvo observável anterior, não certificação do instante físico da ignição nem da cobertura de 2025.

Recomendação para decisão do utilizador: descrever o alvo como **existência de pelo menos uma nova ocorrência de incêndio rural registada no município, com timestamp de alerta em (T,T+24h]**, excluindo reacendimentos segundo taxonomia validada. Não transformar o campo em data de inserção na BD, chamada ou ignição física: esses conceitos não estão demonstrados. O candidato pode ser preservado, pois a evidência não exige mudar os labels classificados; a adoção desta descrição e a política de fuso continuam a carecer de decisão explícita. Nenhum candidato, label ou relatório antigo foi alterado.

## Rastreio do desenvolvimento

1. Fonte original: `cobertura_5b2b/Data2001_now.csv`, coluna `DHInicio`, chave `Codigo` (SGIF). Hash conferido contra o manifesto original.
2. `auditar_5b2b.py` copia essa string para `consolidado.csv`, sem ajustar hora/minuto. Foram verificadas as 24170 linhas de 2022–2024: todas inalteradas.
3. `labels_5b2b.py`, funções `variantes`, `contar` e `decidir`: interpreta a string sem fuso em Europe/Lisbon (fold=0), transforma em UTC e repete a contagem tratando a string como UTC. Não estima ignição a partir de duração/intervenção/área. Horas ambíguas e conflitos territoriais recebem proteção; presença diferente entre convenções produz null.
4. Emissão T às 15:00 UTC, janela `(T,T+24h]`; limite esquerdo aberto e direito fechado. Um evento exatamente às 15:00 pertence à janela iniciada no dia anterior.
5. `construir_5b3.py` copia o target de `labels.csv` e aplica elegibilidade, sem substituir o timestamp do evento. ML 5B.4/5B.5 usam esse target e não o recalculam.

Significado documental anterior: o CSV SGIF tem cabeçalhos, mas não foi encontrada nos artefactos locais consultados uma definição de DHInicio que comprove **ignição física**. As páginas guardadas de exportação/catálogos não fornecem essa definição; metadata INE define a ocorrência rural, não o significado preciso deste timestamp. `RELATORIO_5B2B.md` já declarava explicitamente que essa equivalência e o fuso não estavam demonstrados. Logo não se deve apresentar a expressão anterior “nova ignição” como prova do conceito da fonte.

Significado PRDF: `fogos-metadata.csv`, linha DHINICIO, identifica data/hora do alerta; ANO refere-se ao ano do alerta, e TEMPO1INTERVENCAO é intervalo do alerta à primeira intervenção. É documentação positiva do conceito de alerta, corroborada pela identidade dos valores comuns. Essa identidade é forte evidência empírica, mas não um dicionário independente da fonte SGIF.

## Cruzamento exato, sem gastar 2025

Consulta SQLite só de leitura: `SELECT Codigo,DHInicio,DH1Intervencao,DHResolucao,DHFim FROM Fogos WHERE Ano IN (2022,2023,2024)`.

| Ano | SGIF | PRDF | IDs comuns únicos | Diferenças de relógio |
|---|---:|---:|---:|---:|
| 2022 | 10390 | 10390 | 10390 | 0 |
| 2023 | 7525 | 7525 | 7525 | 0 |
| 2024 | 6255 | 6255 | 6255 | 0 |
| Total | 24170 | 24170 | 24170 | 0 |

Sem IDs duplicados, exclusivos de um dos lados ou timestamps inválidos neste cruzamento. Não foram usados matching aproximado, geometria ou CodigoSado para forçar correspondências. 2024 foi consultado apenas como dados de origem para semântica temporal, conforme pedido; não houve avaliação, seleção ou métricas de modelos. 2025 foi excluído das análises.

### Distribuição PRDF − SGIF: valores de relógio

Global e em cada ano: média, mediana, P25, P75, P90, P95, mínimo e máximo **0 minutos**. Percentagens com diferença absoluta ≤5, ≤15, ≤30 e ≤60 minutos: **100% em todos os casos**. Não existem extremos diferentes de zero.

Isto compara componentes de calendário/relógio, **não afirma equivalência de instantes UTC com fuso comprovado**. Por exemplo, `2022-01-03 18:45:00` no SGIF torna-se `2022-01-03T18:45:00Z` no PRDF.

### Distribuição se o Z do PRDF for interpretado literalmente

Todos os 24170 valores PRDF têm offset zero; o SGIF original não tem fuso. Comparar PRDF UTC literal com a hipótese SGIF Europe/Lisbon produz:

| Ano | Média (min) | Mediana | P25 / P75 / P90 / P95 | Min / max | ≤5 / ≤15 / ≤30 min | ≤60 min |
|---|---:|---:|---|---|---:|---:|
| 2022 | 48,7449 | 60 | 60 / 60 / 60 / 60 | 0 / 60 | 18,7584% cada | 100% |
| 2023 | 48,6140 | 60 | 60 / 60 / 60 / 60 | 0 / 60 | 18,9767% cada | 100% |
| 2024 | 54,3693 | 60 | 60 / 60 / 60 / 60 | 0 / 60 | 9,3845% cada | 100% |
| Global | 50,1597 | 60 | 60 / 60 / 60 / 60 | 0 / 60 | 16,4005% cada | 100% |

Diferença sempre não negativa: 0 ou +60 minutos, coerente com horário de verão. Não mede atraso entre ignição e alerta. Não é o caso B de dois eventos físicos próximos; é sensibilidade à interpretação do mesmo relógio. O Z pode resultar da serialização sem conversão ou pode representar UTC efetivo; os dados coincidentes não decidem qual. Não ignorar nem aceitar esse Z silenciosamente como solução do fuso.

## Efeito nas janelas e labels

Mantendo a convenção dupla anterior e substituindo apenas o valor SGIF pelo valor de relógio correspondente PRDF: **zero alterações**, pois todos os timestamps comparados coincidem. Esta afirmação isola timestamp, mantendo população/taxonomia/território/cobertura; não afirma equivalência integral de todos os outros campos PRDF.

Se se trocar a hipótese Europe/Lisbon pela leitura UTC literal, 2025 eventos brutos mudam de janela (836 em 2022, 641 em 2023, 548 em 2024). São contagens de eventos, não número de labels alterados. Nos três municípios há 222 candidatos anteriores às exclusões temporais/territoriais finais; 20 mudam de janela sob essa troca.

Comparação de presença já guardada em `n_local`/`n_utc` no inventário ML 5B.3:

| Município | 2022 | 2023 | 2024 | Janelas com presença diferente |
|---|---:|---:|---:|---:|
| Lisboa | 4 | 2 | 0 | 6 |
| Faro | 4 | 5 | 5 | 14 |
| Vila Real | 1 | 4 | 7 | 12 |
| Total | 9 | 11 | 12 | 32 |

As **32/3288 janelas já são null**, não entraram nos 1693 exemplos elegíveis. **Zero labels classificados 0/1 mudam de presença entre as duas hipóteses.** Se se abandonasse a proteção dupla e escolhesse só UTC, esses 32 null seriam candidatos a revisão, não zeros/positivos automaticamente autorizados: cobertura, território e restantes critérios continuariam necessários. Não foram gerados novos labels.

Exemplos de eventos que mudam de janela e janelas afetadas estão em `amostras_temporais.json`. A percentagem pequena não dispensa tratamento: um erro de uma hora pode atravessar exatamente a fronteira às 15h UTC.

## Outros timestamps e limites

Layer Fogos: DHInicio, DH1Intervencao, DHResolucao, DHConclusao, DHFim e DHFimEstimado. **Não existe DHAlerta separado**, nem DHPrimeiraIntervencao com esse nome. Não é possível comparar início vs alerta dentro da mesma linha; o metadata dá significado de alerta a DHInicio. DH1Intervencao é declarado DATE no GeoPackage e as amostras só contêm data, enquanto no SGIF original têm hora: não é alternativa adequada para corrigir o relógio do evento. Resolução, conclusão e extinção são posteriores e não substituem a referência do target.

Não foi demonstrada independência de fonte PRDF/SGIF: pelo contrário, a correspondência integral de IDs/relógios reforça a reutilização da mesma informação. Um futuro holdout poderá ser temporalmente externo, não automaticamente independente em proveniência. Esta verificação não certifica cobertura, negativos, taxonomia PRDF ou 2025.

## Recomendação e paragem

É defensável prosseguir a auditoria de cobertura PRDF como fonte do **mesmo timestamp operacional de alerta registado**, documentando a limitação e preservando a política temporal anterior até esclarecer o fuso. Não é defensável afirmar que agora conhecemos a ignição física nem mudar para UTC literal sem revisão metodológica.

Paragem após esta comparação, conforme pedido. Sem continuação da auditoria completa, treino, carga de joblib, previsões, métricas do candidato, alteração do threshold 0,15, API/produção ou commit.

Reprodução: `python -B experiments/ml_5b/prdf_auditoria/comparar_timestamps.py`; testes `python -B experiments/ml_5b/prdf_auditoria/test_temporal.py -v`; `git diff --check`. SHA-256 de ambas as fontes, metadata, script de labels e inventário em `comparacao_temporal.json`; GeoPackage em mode=ro/query_only. Quatro testes: cruzamento e igualdade, preservação dos null, fronteiras de 24h e estatísticas com sinal/limites absolutos.
