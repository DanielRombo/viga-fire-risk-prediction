# ML 5B.2B — cobertura empírica e labels

Fecho: 13/10/2026. Experiência local, sem treino, acesso à BD de produção, deploy ou commit.

## Decisão

**GO condicionado para construir um dataset retrospetivo experimental de Lisboa (1106), Faro (0805) e Vila Real (1714), 2022–2024, com exclusões explícitas.** Não é uma certificação de todas as ignições reais nem autorização para treino. O alvo observável é uma nova ignição rural **registada no SGIF**, usando `DHInicio`, em `(T,T+24h]`. A equivalência exata entre esse timestamp e o instante físico de ignição não está demonstrada.

O subconjunto tem 3288 linhas potenciais: 177 positivas, 2644 negativas condicionais e 467 null; prevalência de 6,2744% entre as 2821 classificadas. Lisboa/2024 permanece integralmente null. Não avançar automaticamente para os 26 municípios: só cinco tiveram verificação poligonal; três têm prova meteorológica nesta fase. Não há GO para previsão operacional em tempo real nem para negativos nacionais certificados.

## Fontes e versões

| Fonte | Proveniência e utilização |
|---|---|
| [SGIF/ICNF](https://fogos.icnf.pt/download/ExportarDadosSGIF/) | `Data2001_now.csv`, `Data2001_noweliminados.csv`, `AdministrativeRelations.csv`; ocorrências, exclusões e códigos INE. Exports de 24/03/2026, aquisição preservada nos manifestos. |
| [INE 0013512](https://www.ine.pt/bddXplorer/htdocs/minfo.jsp?var_cd=0013512&lingua=PT) | Incêndios rurais por município e causa, 2018–2024, NUTS 2024, atualização 30/05/2026. Fonte declarada: ICNF. Total e causa 4 (reacendimentos). |
| [SGIFR, relatórios anuais](https://www.sgifr.gov.pt/relatorios-anuais) | Publicações de 2023 e 2024: comparação com edições anteriores, não contagens municipais independentes. |
| [DGT/CAOP](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop?language=pt) | GeoJSON oficial dos municípios 1106, 0805, 1714, 0303 e 0603. Versão atual CAOP2025; não certifica retroativamente limites de 2018. |
| Open-Meteo Archive / ECMWF IFS | Inputs reais já guardados na Fase 8, coordenadas e hashes verificados; nenhum novo download meteorológico. |

URLs exatos, bytes, timestamps e SHA-256 estão em `fontes_5b2/*.json` e `cobertura_5b2b/*.manifesto.json`. O INE republica o ICNF: a reconciliação é um controlo de consistência entre publicações, **não uma segunda rede independente de deteção**. O acesso público ao CSV não equivale, por si, a uma licença explícita de redistribuição; manter os originais locais até esclarecer esse ponto.

| Original | Bytes | SHA-256 |
|---|---:|---|
| Data2001_now.csv | 479541125 | dc2df96256a5f85c8b1e0d39628b78ccc50862241cfe817dcefe9c147bf3ef8f |
| Data2001_noweliminados.csv | 2533108 | e06eb5f9cd7410f3803ed6a6a40761925116217b61589ed5983224d19c0df6a2 |
| INE 2018–2024 | 818293 | 09742b29153fe5e83ca0d3e8e6c06c2614fc535affbf563437cb8ea9a99aae17 |

Os downloads concluídos não foram repetidos. Integridade de tamanho/hash e estrutura CSV verificada; os originais não foram modificados. `integridade_final.json` inventaria os resultados locais. Respostas antigas do INE com parâmetros inválidos foram identificadas como erros e não como zeros; só a consulta com períodos `S7A2018` a `S7A2024` alimenta a reconciliação.

## Reconciliação 2018–2024

Comparação do universo publicado, antes de excluir reacendimentos do target:

| Ano | Export SGIF | INE | Diferença SGIF−INE | Diferença % |
|---|---:|---:|---:|---:|
| 2018 | 12274 | 12269 | +5 | +0,0408 |
| 2019 | 10831 | 10832 | −1 | −0,0092 |
| 2020 | 9619 | 9618 | +1 | +0,0104 |
| 2021 | 8186 | 8186 | 0 | 0 |
| 2022 | 10390 | 10390 | 0 | 0 |
| 2023 | 7525 | 7520 | +5 | +0,0665 |
| 2024 | 6255 | 6255 | 0 | 0 |

O relatório SGIFR de 2023 publicou 7523, entre as duas versões atuais; o de 2024 publicou 6255. Isto demonstra diferenças entre edições, mas não identifica quais linhas foram revistas. Não atribuímos automaticamente cada diferença a revisões. O boletim ICNF de 2022 com 10449 ocorrências até 15 de outubro é parcial e não foi tratado como total anual final. A reconciliação municipal completa, diferenças absolutas/percentuais e reacendimentos estão em `reconciliacao_anual.csv`; a nacional em `reconciliacao_nacional.csv`.

Não exigimos igualdade nacional para aceitar municípios reconciliados. Blocos divergentes podem ser aceites futuramente mediante explicação verificável das linhas/revisões; nesta versão, sem essa explicação, ficam duvidosos. Não foi inventada uma margem percentual para os fazer passar. As contagens de reacendimentos por causa INE e por marcadores/parentesco SGIF também diferem: não se subtrai simplesmente a causa INE ao export para fabricar o target.

## Taxonomia reproduzível e consolidação

Universo original: 495099 linhas, 2001–2026. Identidade primária: `Codigo`, sem duplicados neste export. Conservar IDs originais e motivo em `consolidado.csv`.

1. Excluir IDs presentes em `Data2001_noweliminados.csv`.
2. Aceitar `Tipo` exatamente `Florestal` ou `Agrícola`. A primeira categoria não permite separar sistematicamente povoamento e mato sem usar área final; não fazemos essa separação. Excluir `Queima` (18 linhas). Não confundir incêndio causado por uma queimada com uma queimada controlada: a causa negligente não exclui um incêndio rural real classificado como tal.
3. Excluir quando `Reacendimento_IncendioPai` existe, `Reacendimentos` não é vazio/0 **ou `CodCausa=711`**. A descrição original de 711 é reacendimento a partir de incêndio anterior. A revisão encontrou 284 linhas só identificadas por esse código; foram excluídas antes do fecho.
4. Exigir `DHInicio` válido e município resolvido administrativamente; os casos incertos bloqueiam labels relevantes.
5. Não usar área ardida, meios, duração, resolução, extinção nem `Open/Closed` para selecionar o target. A causa 711 serve apenas para excluir reacendimentos da verdade retrospectiva, nunca como feature.

Resultado em todo o export: 464659 candidatos, 30415 reacendimentos excluídos, 18 tipos não elegíveis e 7 problemas territoriais. A fonte não apresenta categorias explícitas de falsos alarmes neste export; não é possível demonstrar que nunca existam erros de classificação dentro de `Florestal/Agrícola`.

Eliminados: 2772 IDs, todos com motivo original `Duplicated`, nenhum sobreposto ao export ativo. Não foram reintroduzidos. Não existe uma cadeia de substituições suficiente para contar reclassificações ou afirmar que não ocorreram.

`CodigoSado` não é chave global: 62963 valores repetidos e 41782 grupos repetidos mesmo dentro do ano. Exemplos inspecionados têm datas/concelhos distintos. Não os fundimos. Há 975 grupos com mesmo instante, código INE, coordenadas e tipo: suspeitas conservadas, não prova de mesma ignição. O target é existência, pelo que eventos coincidentes no mesmo município/instante não multiplicam positivos. Uma futura análise de contagem de ignições exigiria resolução desses grupos. As 4596 repetições município/instante também não são removidas cegamente.

## Cobertura e estabilidade

Matriz completa: 308 municípios × 84 meses = 25872 blocos.

| Classe | Blocos mensais | Interpretação |
|---|---:|---|
| forte | 0 | Não há prova independente de cobertura diária completa. |
| aceitável | 22812 | Total anual reconciliado, sem problemas identificados, sem alerta mensal. Evidência empírica condicional. |
| duvidosa | 540 | Divergência não explicada, qualidade insuficiente ou anomalia. |
| sem evidência | 2520 | Inclui os municípios insulares ausentes do universo administrativo SGIF utilizado. Zero INE não certifica cobertura insular. |

Por ano: 1927 aceitáveis, 19 duvidosos e 210 sem evidência. Nos 26 pontos continentais do catálogo: 174 município-anos aceitáveis e 8 duvidosos.

Triagem explícita: ano vazio contra mediana dos restantes anos ≥5; mês vazio contra mediana do mesmo mês ≥5; pico mensal ≥20 e superior a 5× a mediana (denominador mínimo 1). Foram sinalizados 317 meses. São regras conservadoras de investigação, não testes científicos que provem falha ou completude. Os alertas permanecem duvidosos; não foram todos explicados. Lisboa/2024 tem zero também no INE, mas fica bloqueada pela quebra anual. Braga/2023 tem 37 contra 35 e fica duvidosa. Faro e Vila Real têm totais anuais coincidentes nos sete anos, mas mantêm exclusões mensais/temporais/territoriais.

`matriz_mensal.csv` inclui contagens e mediana comparativa. Não contém totais mensais oficiais inventados: esse campo é null, porque a reconciliação externa obtida é anual. Não usar estas regras com anos futuros de teste para simular certificação disponível em tempo real; a matriz é uma avaliação retrospectiva e deve ser congelada antes do treino.

## Tempo e território

Todos os 495099 `DHInicio` são sintaticamente válidos e sem fuso. Ano/mês/dia/hora auxiliares coincidem. Todos têm segundos 00; 20969 têm minuto 00 e 197925 minuto múltiplo de cinco. Isto indica resolução/arredondamento, não precisão ao segundo. Há 164 resoluções e 1048 conclusões anteriores ao início; esses campos não são inputs nem critérios do target.

Convenção do estudo: T=15:00 UTC diariamente, horizonte absoluto de 24 h, limite esquerdo aberto e direito fechado. Interpretamos DHInicio em Europe/Lisbon e repetimos a classificação como UTC. Se presença/ausência muda, o target é null. Horas ambíguas/inexistentes na mudança de hora bloqueiam o horizonte. Isto reduz sensibilidade, mas não prova o fuso histórico nem que DHInicio seja a ignição física exata.

Território: código INE → AdministrativeRelations → código municipal DTCC, com nomes de concelho/distrito concordantes. Coordenadas são controlo adicional, não substituem silenciosamente o código. Cinco códigos ausentes/ambíguos e duas coordenadas inválidas no universo completo. O envelope continental é apenas diagnóstico; a amostra usa polígonos reais DGT.

Lisboa, Faro, Vila Real, Braga e Coimbra: 1466 verificações coerentes, 15 incompatibilidades, incluindo eventos codificados num município vizinho mas localizados dentro do polígono da amostra. Ambos os municípios afetados ficam protegidos contra falsos zeros nesses horizontes. Não transferimos ocorrências automaticamente. Confiança média, não alta: CAOP2025 não comprova os limites históricos. Restantes 21 municípios apenas candidatos administrativos, pendentes de verificação poligonal equivalente. Funchal e Ponta Delgada permanecem fora do dataset candidato.

## Labels e prova real

`1`: pelo menos um candidato em ambas as convenções temporais. A existência confirmada pode sustentar um positivo mesmo num mês cuja cobertura global seja duvidosa.

`0`: nenhum candidato em ambas as convenções, todos os meses atravessados aceitáveis/fortes, sem bloqueio temporal ou territorial. Significa ausência de ocorrência registada sob os critérios empíricos, não prova universal de ausência física.

`null`: cobertura insuficiente, conflito territorial/temporal ou mudança da classificação com o fuso. Null nunca é convertido em zero.

| Âmbito | Linhas | 1 | 0 condicional | null | Prevalência entre classificadas |
|---|---:|---:|---:|---:|---:|
| 26 municípios, 2018–2024, candidatos | 66482 | 6484 | 54705 | 5293 | 10,5967% |
| Lisboa, abril–setembro 2023 | 183 | 6 | 175 | 2 | 3,3149% |
| Faro, abril–setembro 2023 | 183 | 19 | 157 | 7 | 10,7955% |
| Vila Real, abril–setembro 2023 | 183 | 24 | 157 | 2 | 13,2597% |
| Prova com meteorologia/FWI | 549 | 49 | 489 | 11 | 9,1078% |

`labels_mensais.csv` discrimina município/ano/mês. `dataset_piloto.csv` contém temperatura, humidade, vento, precipitação anterior, os seis componentes FWI, mês/dia do ano, target, cobertura, confiança e versão/hash das fontes.

Foram reutilizadas e verificadas 52560 horas (17520 por região), calculados 730 dias por região, de 01/10/2021 a 30/09/2023, e extraídos os seis meses. O prefixo recalculado coincide exatamente com os resultados guardados da Fase 8 (diferença máxima 0). Semente explícita 85/6/15; FWI permanece reconstruído, não estabelecido. Não há alteração científica. O tempo medido foi 4,045 s para a prova, não uma previsão de desempenho de downloads ou do Dell Wyse.

Amostra estratificada revista: 10 positivos e 20 negativos nos três municípios, repartidos pelos seis meses. `amostra_contraprova.json` cruza diretamente o CSV original, conserva IDs/timestamps/natureza/coordenadas dos positivos e eventos anterior/seguinte dos negativos nas duas convenções. Os 30 passaram. Exemplos positivos: Lisboa 20230952575 (05/08 21:57), Faro 20230498013 (27/04 14:53), Vila Real 20230400556 (04/04 12:47). Os negativos verificados incluem 01/04 e 30/09 nos três municípios. A revisão confirma a implementação contra a fonte, não é validação de campo independente.

## Leakage e limitações

As features usam apenas horas com valid_time ≤T; observação FWI de referência 12 UTC e precipitação nas 24 horas anteriores. O target usa exclusivamente o futuro `(T,T+24h]`. Não há features de área, mobilização, extinção ou estado final. O cálculo do prefixo foi comparado com a sequência longa para excluir dependência computacional do futuro.

Archive/IFS é reconstrução retrospectiva: `available_at_historico` fica vazio. Não demonstrámos que estes valores estariam disponíveis em T; assimilação/revisões podem incorporar informação posterior. Portanto não é um backtest operacional sem leakage de disponibilidade. Antes de previsão em tempo real é necessário um arquivo com tempos de emissão/disponibilidade, além de validação da qualidade das ocorrências.

Pontos meteorológicos urbanos não representam toda a variabilidade do território municipal. Documentar coordenadas fixas e testar representatividade; não afirmar que o ponto Lisboa cobre espacialmente todo o concelho. A influência da semente em DC continua uma limitação e não é resolvida por passar um número fixo de dias.

## Plano para o dataset completo — ainda não executado

1. Congelar versões, hashes, taxonomia e exclusões dos três municípios, 2022–2024. Não expandir automaticamente os 26.
2. Manter 3288 linhas de inventário, excluir os 467 null da supervisão, preservar o motivo. 177 positivos/2644 negativos são contagens preliminares após esta política, não garantia de poder estatístico.
3. Obter apenas horas em falta. Para as features de três anos: 1096×24×3 = 78912 horas, mais fronteiras e histórico de inicialização. Reutilizar apenas coordenadas/produto/hash coincidentes.
4. Definir antes da execução a política de sensibilidade às sementes. Uma opção técnica é prefixo desde 02/01/2017 até 31/12/2024, permitindo os intervalos de precipitação a partir de 01/01/2017: 2921 dias de cálculo por ponto, cerca de 210384 horas incluindo um dia antecedente por ponto. Não chamar esse prefixo garantia científica de estabelecimento. Medir dispersão entre sementes e sinalizar inputs dependentes da semente.
5. Split temporal: treino 2022, validação 2023, teste 2024. Lisboa não contribui com labels de teste; reportar desempenho por município e esta alteração de composição, sem ocultar ou preencher zeros. Ajustes apenas no treino, sem random split principal; purgar qualquer horizonte que atravesse limites de partição.
6. Rever poder estatístico e seleção dos meses antes de treinar. Não otimizar a matriz de cobertura para obter métricas melhores. Expansão a Coimbra/Braga exige resolver blocos e construir features antes de novo GO.
7. Não há estimativa fiável de tempo de recolha completa medida nesta fase. Volume está calculado; medir a primeira extensão autorizada antes de orçamentar tempo. Não extrapolar os 4,045 s para rede ou produção.

## Artefactos, execução e testes

Scripts novos, exclusivamente experimentais: `obter_5b2b.py`, `auditar_5b2b.py`, `reconciliar_5b2b.py`, `territorio_5b2b.py`, `labels_5b2b.py`, `prova_5b2b.py`, `rever_amostra_5b2b.py`, `test_5b2b.py`.

Resultados em `cobertura_5b2b/`: auditoria, consolidação, reconciliação nacional/municipal, matriz mensal, conflitos poligonais, labels e contagens, dataset piloto, amostra/contraprova e manifesto de integridade. Originais e CSV volumosos estão excluídos pelo `.gitignore` local; não assumir que a entrega de um clone inclui esses ficheiros. Não foi feito staging nem commit.

Execução local dos scripts com `python -B`. Geometria e prova xclim em imagem backend existente, `docker run --rm --network none`, repositório montado só para leitura e apenas a pasta experimental de resultados gravável. Nenhum serviço/BD de produção foi invocado. A regeneração final da taxonomia não alterou os labels da prova; não repetimos o cálculo científico desnecessariamente.

Testes: `python -B -m unittest discover -s experiments/ml_5b -p test_5b2b.py -v`; verificam cobertura, null/zero, fronteiras do horizonte, sensibilidade temporal, hashes, unicidade, prova e amostragem. Verificação final adicional dos manifestos oficiais e `git diff --check`. Não treinar até revisão e GO explícito do utilizador.

Resultado final: **10/10 testes aprovados**; oito manifestos INE/administrativos/DGT verificados; 23 artefactos locais conferidos contra `integridade_final.json`; `git diff --check` sem erros. O diff de ficheiros versionados permanece vazio: as adições desta tarefa são experimentais e ainda não versionadas. Isto não significa que os originais volumosos, ignorados, acompanhem automaticamente um futuro commit.
