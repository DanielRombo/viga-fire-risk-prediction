# Auditoria PRDF — fecho formal

14/10/2026. **Auditoria concluída; NO-GO para usar atualmente 2025 na avaliação do candidato congelado.** O bloqueio é a evidência insuficiente de cobertura para certificar zeros, não a incompatibilidade do timestamp operacional. O PRDF permanece útil como fonte complementar e para futura validação. Este relatório consolida resultados já guardados; o fecho não repetiu análises pesadas.

## Target e decisão temporal

Definição aprovada: **“Existência de uma nova ocorrência rural registada no município durante (T,T+24h], usando como referência temporal o timestamp operacional de alerta.”** Não se afirma que DHInicio represente o instante físico da ignição.

Nos **24 170 eventos comuns entre SGIF e PRDF em 2022–2024**, os valores de relógio coincidem exatamente. Ver `comparacao_temporal.json` e `DECISAO_TEMPORAL.md`. A compatibilidade operacional foi aceite pelo utilizador.

A ressalva de timezone permanece: o sufixo Z do PRDF não demonstra que houve uma conversão histórica correta dos relógios SGIF. Preserva-se T às 15:00 UTC e a comparação das convenções Europe/Lisbon e UTC. Casos que mudam de presença na janela são null, não 0/1. Na comparação anterior, as 32 janelas sensíveis já estavam null. 2024 continua consumido como teste e não pode voltar a ser usado para seleção/afinação.

## Proveniência e integridade

O PRDF é uma harmonização que inclui ocorrências ICNF; **não é uma fonte independente do SGIF/ICNF**. A designação possível é holdout temporal externo ao desenvolvimento, com proveniência de ocorrências partilhada. Os cinco MD5 locais coincidem com os publicados na [versão V2025.1](https://zenodo.org/records/21427772). Evidência em `proveniencia.json`.

Os cinco SHA-256 foram comparados antes/depois da auditoria e mantiveram-se iguais (`integridade_originais.json`). Os originais não foram modificados nem copiados para esta pasta. As leituras usaram SQLite read-only/query_only e CSV incremental; METEO teve lotes de 25 000 linhas para verificações de unicidade em SQLite temporário.

## Inventário e cobertura

| Fonte | Registos | Período observado |
|---|---:|---|
| Fogos | 824 875 | 30/01/1980–24/03/2026 |
| METEO | 3 568 731 | 30/01/1980–31/12/2025 |
| FRP | 566 502 | 19/01/2004–28/11/2025, datas reconstruídas |
| PBA | 68 435 | 1975–2025 |

Schemas, tipos, tamanhos, CRS, identificadores, nulos e hashes estão em `inventario.json` e nos JSONs de cada fonte. Fogos e PBA usam EPSG:3763.

**PRDF 2025: 8252 ocorrências**, com cobertura temporal observada de **01/01/2025 a 31/12/2025**, das 00:04 do primeiro dia às 18:10 do último. Há registos nos 12 meses, em 277 municípios e 18 distritos continentais. Não se observa um corte antes do fim do ano; isto não certifica completude. Há 84 dias sem registos, que não foram tratados automaticamente como negativos.

| Mês de 2025 | Ocorrências |
|---|---:|
| Janeiro | 95 |
| Fevereiro | 32 |
| Março | 330 |
| Abril | 253 |
| Maio | 439 |
| Junho | 1156 |
| Julho | 2067 |
| Agosto | 2102 |
| Setembro | 883 |
| Outubro | 812 |
| Novembro | 63 |
| Dezembro | 20 |

Totais anteriores: 2022=10 390; 2023=7525; 2024=6255. Municípios presentes: 275, 277 e 273, respetivamente. `estabilidade_2025.csv` compara município/mês com 2022–2024. Sinaliza 50 zeros com mediana histórica ≥5 e seis picos ≥20 e superiores a cinco vezes a mediana (piso 1). Muitos zeros concentram-se em fevereiro, incluindo Vila Real. Estes limiares são apenas triagem: variação meteorológica e falha de reporte não podem ser distinguidas só pelas contagens. Nenhuma anomalia foi corrigida automaticamente.

## Taxonomia e duplicados

Incluem-se potencialmente tipos Florestal/Agrícola. Exclui-se reacendimento identificado por TipoCausa, CodCausa=711 ou relação parental preenchida; exige-se DHInicio interpretável. Não se usam área ardida, meios ou duração como critério.

| Classificação 2025 | Quantidade |
|---|---:|
| Novas ocorrências rurais potenciais | **7579** |
| Reacendimentos | **668** |
| Queimas excluídas | **5** |
| Total | **8252** |

Há 661 reacendimentos pela causa e mais sete pela relação parental. As cinco Queimas não foram presumidas autorizadas: ficam fora da taxonomia candidata. Não existem indicadores dedicados suficientes para demonstrar a exclusão universal de falsos alarmes, cancelamentos e eliminados. Não se transplantaram silenciosamente os filtros SGIF anteriores.

Codigo é único. CodigoSado não é chave única: 62 963 grupos repetidos e 202 836 linhas excedentes globalmente. Em 2025 existe um grupo com coordenada/município/relógio iguais e 14 pares na mesma célula de 0,01 grau separados por ≤10 minutos. São candidatos a investigação, não duplicados confirmados; nada foi removido. A célula não corresponde a uma distância geodésica exata.

## Qualidade temporal e territorial

DHInicio é interpretável em todas as linhas, com ano coerente. Não há DHALERTA separado na layer. DH1Intervencao é DATE: 288 145 valores parecem anteriores ao alerta quando interpretados à meia-noite, mas nenhum é de um dia anterior. Não confundir perda de precisão horária com inversão real.

Globalmente, 3173 DHFim são anteriores ao início, dos quais 36 num dia anterior. Em 2025 faltam dois DHFim, 153 primeiras intervenções e 997 resoluções; DHConclusao está vazio nas 8252 linhas. Não se detetou fim/resolução/intervenção num dia anterior ao alerta em 2025. Detalhes em `fogos.json`.

Código INE foi confrontado com a relação administrativa, nome e distrito: há três incompatibilidades código/nome em 2025. A amostra dos três municípios foi verificada com DGT/CAOP2025: **101 ocorrências territorialmente coerentes, zero conflitos**. Não se extrapola esta validação poligonal para os restantes municípios. Confiança nacional continua limitada.

A geometria Fogos não é uma layer de pontos de alerta: 760 793 geometrias estão vazias e 64 082 são polígonos/multipolígonos válidos. Para localização usaram-se as colunas de latitude/longitude, não o centroide do perímetro final. A triagem global detetou duas coordenadas inválidas ou fora do envelope continental.

## METEO e leakage

2025: **8252/8252 fogos com METEO**, incluindo todas as 7579 novas ocorrências potenciais; 26 140 linhas. Há 8028 antes do relógio do alerta, 224 coincidentes e 17 888 depois. Os valores anteriores são frequentemente arredondamentos para a hora anterior, não uma série ex ante independente. Há 5448 linhas >24 h depois, 4254 >48 h e 2208 após a extinção declarada.

Inconsistência relevante: o reacendimento `20251096294`, Montalegre, tem duração registada de 16,38 horas, mas 2058 linhas meteorológicas, prolongadas cerca de 2056 horas após o alerta. Causa não demonstrada; nada foi truncado ou corrigido para ocultar a divergência (`complementos.json`).

Globalmente, a ligação textual exata cobre 1 470 707 linhas METEO. Uma hipótese secundária unívoca remove o prefixo ANO_ das chaves históricas Fogos e liga mais 1 924 332 linhas. Restam 173 692 linhas/164 498 códigos sem resolução. Esta normalização é uma hipótese rastreável, não prova documental de identidade. Em 2025 a ligação é exata, sem esta adaptação.

Zero duplicados de ID e de (codigo,DHMeteo). Há pequenos nulos globais, 119 HR ligeiramente superiores a 100 e precipitações negativas da ordem de 10^-16, compatíveis com arredondamento mas não corrigidas. Detalhes e limites em `meteo_chaves.json`.

**METEO contém dados centrados no evento e não é apropriado para usar diretamente como feature do holdout.** A seleção depende do incêndio futuro, inclui informação posterior ao alerta e não fornece uma grelha equivalente para dias sem ocorrências. O FWI PRDF também não foi certificado como equivalente em variante, estado inicial, unidades e disponibilidade temporal ao VIGA. Pode apoiar comparações controladas, mas as features devem vir do pipeline municipal independente, limitado a T. O estudo continua retrospetivo, sem prova da disponibilidade operacional histórica dos inputs.

## FRP, PBA e cruzamentos

FRP tem 55 360 deteções em 2025, terminando a 28/11. ACQTIME tem 395 950 nulos; a comparação com a data reconstruída diverge em 478 666 linhas, incluindo nulos. Reconstrução usa ano/mês/dia/hora/minuto/segundo; 82 716 linhas sem segundo são representadas com zero e precisão ao minuto. Não há datas reconstruídas inválidas nem IDs repetidos. A descrição publicada que termina em 2024 não coincide com o conteúdo 2025 do ficheiro publicado, cujo MD5 foi confirmado.

| Associação às 7579 ocorrências potenciais | Com FRP | Sem FRP | Múltiplas deteções |
|---|---:|---:|---:|
| 2 km / ±24 h | 291 | 7288 | 202 |
| 5 km / ±48 h | 850 | 6729 | 701 |

**FRP serve apenas como validação auxiliar de positivos.** A proximidade não demonstra identidade; a ressalva de fuso mantém-se. Ausência de FRP nunca é negativo, especialmente em períodos sem deteções no ficheiro.

PBA tem 2084 perímetros em 2025, dos quais 2083 ligados exatamente a Fogos por SGIF. Globalmente há 21 217 matches SGIF e 47 218 sem match; a chave ANEPC acrescenta 664 ligações secundárias unívocas, com 2966 casos ambíguos. BEST_Codigo estimado não foi promovido a match oficial. Existem 16 conflitos de início e 60 de código municipal globalmente. Não se excluiu nenhum fogo por ausência de perímetro.

Todos os 68 435 polígonos PBA são não vazios e válidos; há 22 grupos de geometria idêntica. Em 2025, 145 pares intersectam-se, 33 com sobreposição superior a 10% da menor área. Sobreposição não prova duplicação. **PBA serve apenas como validação espacial**, não como feature do evento futuro; área/perímetro final e demais resultados posteriores são leakage.

`cruzamentos.json`, `geometria.json`, `frp_cruzamento.json` e `complementos.json` guardam contagens e limitações. `leakage.csv` classifica os campos dos quatro schemas e metadata adicional: identificadores para associação não são automaticamente features seguras.

## Cobertura e estimativas 1/0/null

Reutilizou-se o cache INE 13512 e resultados SGIF locais. SGIF2025 previamente auditado=8252, igual ao PRDF; não se demonstrou identidade linha a linha de 2025. INE continental=8245, diferença bruta +7. O bruto PRDF inclui Queimas e reacendimentos, pelo que a reconciliação bruta não valida a taxonomia final.

295/308 totais municipais coincidem, incluindo zeros nas ilhas que não provam cobertura. Seis divergências continentais: Guimarães +1, Vila Nova de Famalicão +2, Covilhã +1, Sertã +1, Sintra +1, Vila Franca de Xira +1. As restantes sete são municípios madeirenses com INE positivo e ausência no PRDF. Não se atribuiu a diferença a revisões sem evidência.

O INE2025 local está **provisório**, atualizado a 30/05/2026. A coincidência anual entre fontes relacionadas não certifica cada janela de 24 horas. Falta evidência consolidada do universo municipal/periódico e do tratamento de falsos eventos/eliminados. Não se exige igualdade perfeita; exige-se cobertura defensável.

Critérios em config.json: FORTE requer universo/cobertura documentados; ACEITÁVEL admite evidência consolidada e reconciliação sem anomalias relevantes; DUVIDOSO inclui provisoriedade/conflitos; SEM_EVIDÊNCIA indica ausência de universo territorial sustentado. Resultado: **3336 blocos município×mês DUVIDOSO** no Continente, **360 SEM_EVIDÊNCIA** nas ilhas, nenhum FORTE/ACEITÁVEL. Nenhum município/período está atualmente elegível para gerar negativos condicionais segundo estes critérios.

Estimativas agregadas para T diário de 01/01 a 31/12/2025, não um dataset final:

| Município | Positivos potenciais | Negativos certificados | null | Janelas |
|---|---:|---:|---:|---:|
| Lisboa | 1 | 0 | 364 | 365 |
| Faro | 27 | 0 | 338 | 365 |
| Vila Real | 45 | 0 | 320 | 365 |
| **Três municípios** | **73** | **0** | **1022** | **1095** |
| Todos os 308 municípios | 5458 | 0 | 106962 | 112420 |

Contexto de 01/01/2026 foi usado apenas para fechar a última janela futura de 2025. Não foram exportados labels finais diários. Temporalidade ambígua e território incerto permanecem null, salvo outra ocorrência que confirme presença nas duas convenções. Os positivos nacionais são potenciais, com verificação territorial menos completa fora da amostra. Não se calcula prevalência sobre apenas positivos conhecidos: seria enganador.

## Decisão e próximos passos

**NO-GO por cobertura insuficiente para certificar zeros.** Não é prova de que 2025 esteja truncado ou de que o PRDF seja inutilizável. Não existe neste momento um subconjunto elegível demonstrado para avaliar o candidato com negativos. PRDF continua útil para novas ocorrências potenciais, reconciliação, validação espacial e investigação futura.

Para reabrir: obter evidência consolidada de cobertura municipal/periódica, resolver a taxonomia e o tratamento de eliminados/falsos eventos, esclarecer divergências relevantes e rever os blocos explicitamente. Totais definitivos ajudariam; igualdade anual isolada não basta. Só depois construir o holdout e autorizar a avaliação única separadamente.

## Verificações e limites do fecho

Os pequenos artefactos esperados existem: inventário, cobertura, leakage, cruzamentos, proveniência, integridade, decisão temporal e scripts/testes. **12 testes existentes aprovados**, incluindo taxonomia, FRP, contagens, proteção de null, ligações METEO, read-only e compatibilidade temporal. `git diff --check` passou. A verificação do fecho não repetiu hashes dos datasets nem scans pesados: reutilizou a evidência de integridade já produzida.

Não se executou o candidato, não houve previsões/métricas, treino, alteração do threshold ou calibração. Produção/API/frontend permanecem fora do âmbito. Não houve deploy nem commit. Alterações preexistentes no working tree não foram incluídas nem revertidas.
