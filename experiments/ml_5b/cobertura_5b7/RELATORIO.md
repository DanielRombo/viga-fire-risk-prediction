# ML 5B.7 — fontes e certificação de cobertura 2025

**Decisão em 14/10/2026: NO-GO para construir o holdout rotulado de 2025.** A pesquisa encontrou suporte normativo para o registo e melhor reconciliação anual, mas não demonstrou a completude dos microdados públicos por município/período. Detetou também uma divergência oficial de classificação de reacendimentos. Não foi convertido nenhum null em zero.

Target preservado: **Existência de uma nova ocorrência rural registada no município durante (T,T+24h], usando como referência temporal o timestamp operacional de alerta.** T=15:00 UTC; proteção dupla Europe/Lisbon versus UTC mantida. Não é previsão do instante físico de ignição. 2024 continua consumido; não se carregou o candidato, não se calcularam previsões ou métricas, não se treinou/recalibrou nem alterou threshold.

## 1. Fontes encontradas e o que acrescentam

Inventário completo: `fontes.csv` (19 entradas), com entidade, URL, data de acesso, origem, independência, periodicidade, estado e limite de interpretação. A/B/C/D representam, respetivamente, utilidade para certificar negativos, validar positivos, reconciliar cobertura/totais ou ausência de utilidade para o target disponível.

| Fonte | Utilidade efetiva nesta fase | Limitação |
|---|---|---|
| ANEPC, DON DECIR 2025 | C: fundamento do universo operacional | Norma não comprova execução nem completude do export |
| ProCiv/dados.gov | B: ocorrências em aberto | Não é arquivo anual completo |
| Endpoint histórico antigo | D: não obtido | Redireciona para HTML, não devolve microdados |
| SGIF ativos/eliminados | C: universo exportado já auditado | Sem documento público que certifique cada intervalo |
| SGIF daily_fires_summary | C: agregado diário da mesma fonte | Nacional, amostra com NA; sem cobertura municipal comprovada |
| ICNF, 7.º relatório provisório | C: comparação mensal de versões | Até setembro, provisório |
| SGIFR/AGIF anual 2025 | C: reconciliação anual e divergência documentada | Não é validação independente do SGIF |
| INE 13512/metadados | C: agregado municipal | Anual, derivado ICNF, ainda provisório |
| EFFIS, FIRMS | B: apoio instrumental | Não recenseiam todos os alertas rurais |
| Municípios | B/D conforme fonte | Sem arquivo completo rural 2025 obtido |
| IRS/FaRDaP inglês | A potencial, apenas plano B | Nenhum período certificado aqui; não transferível diretamente |

### ANEPC / SADO

A [DON DECIR 2025, secção 8.a](https://prociv.gov.pt/media/d3rjmgs3/don_02_2025.pdf) exige registo das ocorrências rurais no SADO e manutenção de histórico para análise. Esta é evidência primária de desenho do sistema. Não equivale a um extrato verificável de todos os registos de 2025. A vigência da diretiva também não deve ser projetada automaticamente para datas anteriores à aprovação sem documentação antecedente.

O [catálogo ProCiv](https://dados.gov.pt/datasets/prociv-ocorrencias-em-aberto) descreve dados originados no SADO, mas sobre ocorrências em curso. A API de catálogo ainda referencia `GetHistoryOccurrence` e `GetHistoryOccurrencesByLocation`. O segundo foi testado: HTTP 200 com redirecionamento para `https://prociv.gov.pt/pt/home/`, conteúdo HTML. **Não é uma resposta de zero ocorrências.** Não foram tentados acessos autenticados ou privados. Não se demonstrou um arquivo público diário completo para os três municípios.

### SGIFR / ICNF

O [relatório anual SGIFR 2025](https://www.sgifr.gov.pt/documents/196633/196678/Relatorio_Atividades_SGIFR_2025_v20260715.pdf/83fdcf74-4a07-97d9-da97-da89052aa755?t=1784124175203) confirma 8252 ocorrências. Porém, a página 133, nota 38, distingue a taxa de reacendimentos SGIF (~8%) da apurada pelo SADO (6,4%) e refere harmonização em curso. **É um conflito relevante para excluir reacendimentos do target.** Não se transformaram percentagens em números de novos eventos nem se inferiu a distribuição municipal da divergência. Não se alterou a taxonomia para obter concordância. O documento anual melhora a evidência agregada; não fornece a ponte necessária entre o export e a completude municipal diária.

O [diretório SGIF](https://fogos.icnf.pt/download/ExportarDadosSGIF/) continua a disponibilizar ativos/eliminados e produtos diários. Não se repetiu o download de centenas de MB. Foi obtida apenas uma amostra HTTP Range de 32 KiB do agregado nacional diário: schema com Data, DNRF, meteorologia e estatísticas pós-evento, incluindo NA. Não se inferiu a cobertura integral de 2025 a partir dessa amostra. Um agregado SGIF não constitui uma segunda fonte independente.

### INE

Nova consulta do [indicador 0013512](https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd=0013512&lang=PT) confirma atualização de **30/05/2026**, último período 2025, marcado **Dado provisório**. O conteúdo estatístico é igual ao cache anterior; o hash do JSON muda devido à data de extração. Os [metadados](https://www.ine.pt/bddXplorer/htdocs/minfo.jsp?var_cd=0013512&lingua=PT) identificam periodicidade anual e fonte ICNF/Estatísticas florestais. Não documentam completude diária nem independência do SGIF.

Provisoriedade não é, isoladamente, razão suficiente para rejeitar qualquer negativo. Aqui faltam adicionalmente a demonstração de completude do extrato, reconciliação operacional não circular e resolução da taxonomia entre sistemas.

### Satélite e municípios

[EFFIS](https://forest-fire.emergency.copernicus.eu/about-effis/technical-background/rapid-damage-assessment) mapeia apenas parte dos eventos; a elevada cobertura de área ardida não significa cobertura de todas as ocorrências. Pode incluir fogo prescrito e as datas de perímetro não equivalem necessariamente ao alerta. [FIRMS](https://forum.earthdata.nasa.gov/viewtopic.php?t=5178) pode falhar deteções por nuvens, passagens, intensidade e duração. São evidência auxiliar de positivos. Partilham sensores; não contar as duas fontes como confirmações instrumentais totalmente independentes.

Na pesquisa municipal, Lisboa disponibiliza relatórios RSB, mas o encontrado é relativo a 2024; Faro disponibiliza cartografia de planeamento; Vila Real tem notícias de atividade e danos em agosto de 2025. Não foi obtido nenhum censo municipal rural completo de 2025. Isto significa **não encontrado/demonstrado nesta pesquisa**, não inexistência garantida de registos locais. Ocorrências “Na Minha Rua” e dados pré-hospitalares pertencem a outros universos.

## 2. Reconciliação e independência

| Âmbito | PRDF | Fonte comparada | Diferença PRDF−fonte |
|---|---:|---:|---:|
| 2025, agregado continental | 8252 | SGIFR 8252 | 0 |
| 2025, Continente | 8252 | INE 8245 | +7 |
| Lisboa, ano | 1 | INE 1 | 0 |
| Faro, ano | 32 | INE 32 | 0 |
| Vila Real, ano | 68 | INE 68 | 0 |

`reconciliacao_mensal.csv` compara janeiro–setembro com o [7.º relatório provisório ICNF, publicado em 01/10/2025](https://www.icnf.pt/api/file/doc/2ddb8ceae473db04): PRDF=7357 versus relatório=7732, diferença −375. Diferenças mensais: 0, 0, −1, −1, −5, −23, −54, −183 e −108. São snapshots/taxonomias não reconciliados por IDs. **Não se atribuem automaticamente a perdas de cobertura**, nem se inventa que revisões explicam todos os casos. O bruto inclui reacendimentos e Queimas; a igualdade bruta não certifica o universo de novas ocorrências.

PRDF→SGIF/ICNF, INE→ICNF e relatório anual→entidades SGIFR são linhagens relacionadas. SADO é o registo operacional primário, mas a ligação ao SGIF impede presumir independência total. Não houve novo microdado útil para cruzamento de IDs 2025, logo não se publicam matches/eventos adicionais inventados. As datas e contagens PRDF foram reutilizadas da auditoria fechada, não recalculadas.

## 3. Regra de certificação e matriz

Para gerar zero é necessário demonstrar: universo operacional, inclusão rural, período completo, município coberto, significado da ausência, reconciliação não exclusivamente circular, ausência de falhas relevantes, compatibilidade da taxonomia e qualidade temporal/territorial. Uma condição desconhecida não conta como satisfeita.

- **FORTE:** todas as condições sustentadas por documentação/extrato e controlo de cobertura.
- **ACEITÁVEL:** condições mínimas sustentadas, com limitações pequenas identificadas e reconciliadas; zero continua condicionado.
- **DUVIDOSO:** há dados, mas completude não demonstrada ou conflito relevante pendente.
- **SEM_EVIDÊNCIA:** falta universo documental aplicável.

A norma sustenta o universo pretendido e a inclusão rural. PRDF e INE sustentam presença territorial e agregados. Não demonstram que cada ausência municipal/diária seja significativa. O conflito de reacendimentos impede juntar sistemas como se fossem semanticamente idênticos.

`matriz_cobertura_2025.csv` contém **36 linhas**, janeiro–dezembro para Lisboa, Faro e Vila Real, com início/fim mensal, presença do ficheiro versus contagem de eventos separadas, dados ANEPC/INE, estado de publicação, evidências e decisão. **36 DUVIDOSO; zero FORTE, ACEITÁVEL ou novos períodos elegíveis.** Nenhuma evidência obtida justifica alargar para outros municípios. Os booleanos negativos indicam prova ausente, não prova de que o sistema esteve inativo.

## 4. Contagens provisórias e decisão

| Município | Positivos potenciais | Negativos condicionais admissíveis | null |
|---|---:|---:|---:|
| Lisboa | 1 | 0 | 364 |
| Faro | 27 | 0 | 338 |
| Vila Real | 45 | 0 | 320 |
| **Total** | **73** | **0** | **1022** |

As estimativas mensais estão em `contagens_mensais.csv` e na matriz. Total=1095 janelas; **redução de null=0**. Não são labels finais, nem prevalência certificada. Não se converteram períodos sem ocorrência observada em negativos. Os positivos continuam potenciais, com as ressalvas taxonómicas e temporais anteriores.

**2025: não certificável neste momento com a evidência pública obtida. NO-GO para construir o holdout para avaliação única.** Não significa que os registos sejam necessariamente incompletos; significa que o critério exigido não foi demonstrado. O conflito oficial foi registado e não foi ultrapassado por uma decisão automática de juntar fontes.

## 5. O que falta e próximos passos

Prioridade concreta: um extrato SADO/SGIF consolidado ou declaração verificável para os três municípios, abrangendo todo o período e a fronteira de 01/01/2026 necessária à última janela. Deve permitir rastrear códigos e revisões, falsos eventos/eliminados/reacendimentos, âmbito de registo, fuso, interrupções e reconciliação das contagens. Reconciliar em particular a divergência de reacendimentos, sem exigir igualdade artificial entre produtos diferentes.

O caminho público mais promissor é acompanhar a harmonização SADO/SGIF e a consolidação do INE, procurando os respetivos metadados de cobertura. **Esperar por um total definitivo, sozinho, não basta.** Se continuar sem extrato/documentação pública, pedir confirmação dirigida às entidades seria o próximo passo; nenhuma mensagem ou pedido foi enviado nesta fase.

2026 ainda é parcial em 14/10/2026. O ICNF publica indicadores correntes provisórios e existe diretiva DECIR2026; isso não certifica um ano completo futuro. Não se promete data de consolidação. Arquivar respostas e estado de captura a partir de agora pode ajudar, mas não recupera retroativamente ocorrências curtas perdidas entre consultas nem substitui o registo oficial.

Plano B: a [documentação inglesa de incidentes diários](https://www.gov.uk/government/statistics/fire-statistics-incident-level-datasets/daily-incident-dataset-guidance) define o universo de intervenções dos FRS e explicita lacunas, incluindo Suffolk. É um exemplo mais útil de controlo de cobertura, mas não foi certificado aqui. [Outdoor fires](https://www.gov.uk/government/statistics/fire-statistics-incident-level-datasets/outdoor-fires-dataset-guidance) não equivale automaticamente a incêndio rural; granularidade temporal/territorial, transição IRS/FaRDaP e transferência para um modelo com município precisam de auditoria própria. Não se alterou o target nem se propôs testar diretamente o candidato português noutro país.

## 6. Execução, segurança e testes

Foram consultadas páginas oficiais e pequenos recursos. Exceção documental justificada: PDF anual SGIFR de 11,34 MB, não um dataset de ocorrências. Downloads binários, PDF e dependência local estão excluídos do Git pela configuração desta pasta. `pypdf==6.1.1` foi instalado apenas em `_deps`, sem mudar requirements ou ambiente de produção. SHA-256, tamanhos, URLs finais, datas e erros/redirecionamentos constam dos metadados de aquisição.

Os scripts desta fase só usam documentação/agregados, sem abrir modelos ou repetir scans PRDF. **9 testes da fase e 12 testes existentes da auditoria PRDF aprovados: 21 no total.** A regressão PRDF inclui uma consulta read-only curta de contagem, não uma nova auditoria pesada. Foram testados critérios de zero, conservação de null, 36 blocos únicos, contagens, linhagem INE, HTTP200 HTML, amostra parcial, hashes de inputs e reconciliação. `git diff --check` passou, com apenas aviso LF/CRLF no `.gitignore` preexistente. `git status --short` mostra a nova pasta não versionada e alterações anteriores preservadas. `git check-ignore` confirmou exclusão de PDF/binários, extração textual e dependência local. Nenhum staging, commit, deploy ou alteração de produção/API/frontend.
