# ML 5B.3 — construção concluída

13/10/2026. Apenas ficheiros experimentais locais; sem treino, deploy, commit ou acesso à BD.

## Inventário e seleção

A janela candidata completa foi preservada para auditoria, incluindo Lisboa/2024 e outros blocos sem cobertura suficiente. Isto não os admite no dataset elegível: só cobertura aceitável/forte pode entrar. O inventário permite verificar os dias excluídos, em vez de ocultar lacunas.

| Conjunto | Linhas | Positivos | Negativos condicionais | null | Prevalência classificada |
|---|---:|---:|---:|---:|---:|
| Completo | 3288 | 177 | 2644 | 467 | 6,2744% |
| Elegível | 1693 | 132 | 1561 | 0 | 7,7968% |
| Excluído | 1595 | 45 | 1083 | 467 | 3,9894% |

As contagens de labels do ML 5B.2B mantêm-se exatamente. Lisboa/2024 tem 366 null, nunca convertidos para zero. As exclusões podem ter mais de um motivo: 1174 dias com sensibilidade à semente, 467 target null, 431 cobertura não aceite, 9 horizontes que atravessam a fronteira anual. Estes números sobrepõem-se e não devem ser somados.

| Município | Completo | 1 / 0 / null | Elegível | 1 / 0 elegível |
|---|---:|---|---:|---|
| Lisboa | 1096 | 12 / 711 / 373 | 381 | 6 / 375 |
| Faro | 1096 | 50 / 995 / 51 | 270 | 11 / 259 |
| Vila Real | 1096 | 115 / 938 / 43 | 1042 | 115 / 927 |

`qualidade.json` inclui discriminação mensal, anual, municipal e município × ano × mês. O inventário tem zero gaps, zero duplicados e zero features meteorológicas/FWI inválidas. As descontinuidades do conjunto elegível são exclusões explícitas, não falhas ocultadas na recolha.

## Features e tempo

Lista permitida: município, temperatura, humidade, vento, precipitação nas 24 horas anteriores à referência, FFMC, DMC, DC, ISI, BUI, FWI, mês, dia do ano, dia da semana e época do ano. Não foram introduzidos acumulados adicionais nem informação sobre o incêndio futuro.

Referência meteorológica/FWI: 12:00 UTC, hora padrão continental, também no verão. Emissão experimental T: 15:00 UTC. As 24 precipitações horárias terminam entre as 13:00 UTC do dia anterior e as 12:00 UTC do próprio dia, representando `(referência−24h,referência]`. O target é `(T,T+24h]`. Datas bissextas incluídas; nunca converter a referência para 12h civis de verão.

Não há meteorologia com valid_time posterior a T. O prefixo FWI até 31/12/2024 foi recalculado e comparado com a sequência da Fase 8: erro máximo **0 nos três municípios**. Isso verifica causalidade computacional; não prova disponibilidade histórica em T. Archive/IFS pode ter revisões e assimilação posteriores, pelo que `available_at_historico` permanece vazio e o estudo é apenas retrospetivo.

Os labels herdam a convenção Europe/Lisbon e a análise de sensibilidade a UTC. DHInicio não contém fuso; janelas cuja classificação muda permanecem null. A evidência refere-se a ignições rurais registadas no SGIF, não necessariamente ao instante físico exato da ignição.

## Meteorologia, coordenadas e proveniência

Reutilização exclusivamente local: **85536 horas verificadas**, 28512 por município, para 1188 dias de cálculo por ponto (01/10/2021–31/12/2024). Nenhum download. Produtos, coordenadas consultadas, unidades, timestamps, 24 intervalos por dia, finiteza e hashes conferidos contra a resposta original.

| Município | Coordenada consultada | Centro de grelha devolvido |
|---|---|---|
| Lisboa | 38,7169; −9,1399 | 38,69947; −9,196167 |
| Faro | 37,0194; −7,9322 | 37,012302; −7,955139 |
| Vila Real | 41,3006; −7,7457 | 41,300526; −7,7474976 |

A diferença de grelha é explícita, não uma alteração silenciosa da coordenada municipal. Um ponto não representa toda a heterogeneidade municipal. O dataset usa códigos municipais 1106/0805/1714; os IDs históricos presentes nos ficheiros de experiências não são IDs para acesso à produção.

Cada linha conserva hash SGIF, hash meteorológico, versão da fonte, regra de target, município, referência UTC, origem e método xclim. O manifesto liga hashes das tabelas de cobertura, DGT, INE, consolidação, fontes horárias e scripts. A regra inclui tipos Florestal/Agrícola e exclui eliminados, marcadores/parentesco de reacendimentos e causa 711. Não usa área ardida final, mobilização ou estado final como feature/critério.

Confiança territorial média: códigos administrativos concordantes e verificação poligonal herdada da DGT. Conflitos já detetados mantêm bloqueios. CAOP2025 não prova limites históricos; sem promoção artificial para confiança alta. Negativos são condicionais à cobertura empírica, não certificados por uma fonte independente do ICNF.

## Inicialização e seleção conservadora

Semente convencional FFMC=85/DMC=6/DC=15 antes de 01/10/2021. No início do inventário existem 92 dias anteriores calculados; isto **não é assumido suficiente**. As 27 combinações da Fase 8 são recalculadas no mesmo prefixo: FFMC 60/85/95, DMC 2/6/150, DC 5/15/1000.

Em cada T, a seleção exige para os seis índices `max−min ≤ 1e−8 + 1e−10×max(abs)`, a tolerância numérica já usada nas experiências. É um critério experimental conservador de insensibilidade às sementes testadas; não um limiar científico de erro aceitável, nem garantia sobre todas as sementes possíveis. Não se usa uma data de convergência obtida olhando para dias futuros. A dispersão dos seis componentes fica em cada linha, incluindo nas exclusões.

Não foi descarregado histórico anterior só para aumentar artificialmente o conjunto elegível. As trajetórias permanecem reconstruídas e não operacionais. A exclusão por convergência depende das condições meteorológicas e pode enviesar a amostra; as futuras conclusões devem limitar-se ao domínio selecionado. Recuperar representatividade exigirá uma variante documentada com prefixo mais antigo e análise de sensibilidade, não relaxar tolerâncias para melhorar métricas.

## Split temporal e viabilidade

| Split | Elegíveis | Positivos | Negativos |
|---|---:|---:|---:|
| Treino 2022 | 373 | 51 | 322 |
| Validação 2023 | 722 | 40 | 682 |
| Teste 2024 | 598 | 41 | 557 |

Há um limite importante: os municípios não têm a mesma composição em cada ano.

- Vila Real: 354/360/328 linhas elegíveis em 2022/2023/2024, com 51/34/30 positivos. Janela efetiva começa em 10/01/2022, termina em 30/12/2024, com exclusões entre datas.
- Lisboa: 19 linhas em dezembro de 2022, todas negativas; 362 em 2023, seis positivas; nenhuma em 2024.
- Faro: 270 linhas apenas em 2024, a partir de 31/03, com onze positivas. Não aparece no treino/validação conservadores.

**Recomendação:** manter o split temporal proposto, mas usar Vila Real como avaliação longitudinal principal. Lisboa é uma análise auxiliar e Faro um teste separado de transferência para um município não observado no treino; nunca juntar tudo e alegar generalização territorial validada. Não tratar o código municipal como número ordinal; categorias desconhecidas requerem tratamento explícito. Não usar random split. Ajustar transformações só no treino; não modificar critérios depois de ver métricas de teste. Os nove horizontes que atravessam os anos são purgados conservadoramente.

## Amostra e validação

Selecionados deterministicamente 10 positivos, 20 negativos e 6 null, distribuídos entre municípios/datas. A contraprova relê o SGIF original e a lista de eliminados, reaplica a taxonomia e verifica ambas as interpretações temporais. Guarda eventos no horizonte e vizinhos anterior/seguinte. Todos os 30 labels não nulos coincidiram; os null conservam a causa, incluindo sensibilidade ao fuso e cobertura não aprovada. Exemplos: Lisboa 20230952575, Faro 20240547753, Vila Real 2022_17_0001668. Em Vila Real, 01/08/2022 permanece null por sensibilidade temporal. Os três dias 31/12/2024 da amostra não são transformados em zero.

A revisão foi contra a fonte original, não uma investigação de campo independente. `amostra_validada.json` contém os 36 casos para revisão humana. A ausência num CSV, isoladamente, não foi usada como certificado de negativo.

## Decisão

**GO condicionado para ML 5B.4 — treino experimental**, com foco longitudinal inicial em Vila Real e resultados auxiliares separados para os restantes municípios. O dataset está construído e é coerente; a reduzida amostra, enviesamento de seleção, negativos condicionais e falta de disponibilidade em tempo real impedem alegações operacionais ou nacionais. Não foi treinado qualquer modelo.

Ficheiros novos: construtor `../construir_5b3.py`, validador `../validar_5b3.py` e conteúdos desta pasta. CSV ignorados, sem staging. Produção, API, frontend, scheduler, fórmulas FWI e modelos atuais não foram alterados.

Validação final: **9/9 testes aprovados** (`python -B experiments/ml_5b/validar_5b3.py -v`), incluindo integridade de fontes/outputs, null, seleção, limites temporais, convergência no T e exclusão de metadados das features. Uma segunda construção isolada produziu os três CSV com SHA-256 idêntico. `git diff --check` passou. O aviso de ausência de suporte opcional matplotlib durante a importação xclim não afetou os cálculos; não foram instaladas dependências nem gerados gráficos. A execução não acedeu à rede ou à produção.
