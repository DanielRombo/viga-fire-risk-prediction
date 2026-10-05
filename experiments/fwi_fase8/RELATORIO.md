# Fase 8 — RH=100% e influência do estado inicial

## Decisão recomendada

Preservar **RH=100% real**. A diferença com o cffdrs público 1.8.17 resulta do
seu pré-processamento para 99,9999%, não de uma necessidade demonstrada das
equações adotadas. Não alterar constantes, fórmulas ou tolerâncias.

**Manter as sequências como `reconstruido`.** O estudo permite certificar
convergência para as sementes ensaiadas, mas não estabelece, por si só, um
critério científico universal para publicação operacional. Não foi promovida
qualquer sequência nem alterado código de produção.

## Âmbito, dados e configuração

Retoma concluída em 05/10/2026. Não foram repetidas recolhas. Os cálculos
usaram apenas os ficheiros guardados, num container descartável `--network none`,
com o repositório montado só para leitura e escrita restrita a `evidencias/`.
DATABASE_URL aponta deliberadamente para uma porta inacessível no próprio
container; não existe ligação à BD. Não foi criada BD nesta fase.

Sete pontos do catálogo, não sete territórios integralmente amostrados:
Lisboa, Faro, Vila Real, Castelo Branco, Évora, Funchal e Ponta Delgada.
Funchal e Ponta Delgada não representam a diversidade dos respetivos arquipélagos.

Fonte: Open-Meteo Archive, produto pedido `ecmwf_ifs`, proveniência
`open-meteo-archive-ecmwf-ifs-horario-v1`. São dados meteorológicos de grelha,
não observações de estações. A resposta não fornece uma certificação externa
do modelo para cada hora: a atribuição do produto assenta no pedido fixado e
no contrato da fonte. Coordenadas consultadas e da grelha estão preservadas.

Cada região dispõe de 1826 dias (01/10/2021–30/09/2026) e 43 824 horas:
**12 782 dias únicos e 306 768 horas**. A preparação anterior reutilizou
39 360 horas e recolheu 267 408 em sete pedidos, sem falhas nem retries.
Esta retoma fez **zero pedidos meteorológicos**.

Temperatura em °C, humidade em %, vento a 10 m em km/h, precipitação em mm
somada nos 24 intervalos horários terminados no instante de referência.
Referência fixa às 12:00 UTC no Continente/Madeira e 13:00 UTC nos Açores;
não se desloca com a hora civil de verão. O xclim recebe `mm/day` para a taxa
média diária numericamente equivalente ao total das 24 horas, e latitude
em `degrees_north`. Datas incluem 29/02/2024.

Biblioteca: xclim 0.62.0, API pública `cffwis_indices`, variante clássica.
`initial_start_up=False`, `season_method=None`, `overwintering=False`,
`dry_start=None`. RH real, sem correção artificial. Estado explicitamente
fornecido, sem reinicialização sazonal. A divergência conhecida com cffdrs
1.9.2 na constante FFMC continua fora do âmbito; não se afirma equivalência.

## Sementes e horizontes

27 combinações: FFMC ∈ {60, 85, 95}, DMC ∈ {2, 6, 150}, DC ∈ {5, 15, 1000}.
Incluem os cenários húmido 60/2/5, convencional 85/6/15 e seco 95/150/1000.
Os cenários secos têm ordens de grandeza observadas nas fases anteriores.
São hipóteses de sensibilidade, não estimativas do estado verdadeiro; os
27 pontos não demonstram cobertura de todos os estados iniciais possíveis.

| Horizonte | Início | Fim | Dias por região |
|---|---|---|---:|
| 1 ano | 01/10/2025 | 30/09/2026 | 365 |
| 2 anos | 01/10/2024 | 30/09/2026 | 730 |
| 3 anos | 01/10/2023 | 30/09/2026 | 1096 |
| 5 anos | 01/10/2021 | 30/09/2026 | 1826 |

28 ensaios região/horizonte, 28 119 dias somados por semente e **759 213
passos diários para as 27 sementes**, além das pequenas regressões e testes RH.
Não são 759 213 dias meteorológicos independentes.

Dispersão absoluta = máximo − mínimo entre sementes; relativa = dispersão /
máximo dos valores absolutos (zero se todos forem zero). A tolerância mantida
é `atol=1e-8`, `rtol=1e-10`. Não é um limiar de relevância operacional.
Convergência significa que a dispersão fica dentro dessa tolerância e assim
permanece até ao fim da janela observada. Igualdade exata é guardada à parte.
O primeiro dia é contado como dia 1. Nenhuma tolerância foi relaxada.

## Convergência por região e horizonte

Dias até convergência numérica mantida até ao fim; «não» significa que o
critério não se verifica no fim da janela. Datas exatas e seguimento estão
nos JSON; igualdade exata e dispersões diárias também estão nos CSV/NPZ.

| Região | Anos | FFMC | DMC | DC | ISI | BUI | FWI |
|---|---:|---:|---:|---:|---:|---:|---:|
| Lisboa | 1 | 21 | 45 | 80 | 20 | 80 | 80 |
| Lisboa | 2 | 16 | 114 | 159 | 15 | 159 | 159 |
| Lisboa | 3 | 18 | 69 | 134 | 16 | 134 | 134 |
| Lisboa | 5 | 19 | 85 | 438 | 17 | 438 | 438 |
| Faro | 1 | 15 | 48 | 96 | 15 | 96 | 96 |
| Faro | 2 | 16 | 115 | 151 | 14 | 151 | 151 |
| Faro | 3 | 14 | 183 | 183 | 14 | 183 | 183 |
| Faro | 5 | 20 | 175 | 913 | 20 | 913 | 913 |
| Vila Real | 1 | 23 | 32 | 44 | 21 | 44 | 44 |
| Vila Real | 2 | 7 | 9 | 98 | 7 | 98 | 98 |
| Vila Real | 3 | 18 | 23 | 26 | 15 | 26 | 26 |
| Vila Real | 5 | 22 | 34 | 102 | 18 | 102 | 102 |
| Castelo Branco | 1 | 22 | 45 | 80 | 21 | 80 | 80 |
| Castelo Branco | 2 | 16 | 48 | 115 | 14 | 115 | 115 |
| Castelo Branco | 3 | 21 | 27 | 111 | 19 | 111 | 111 |
| Castelo Branco | 5 | 17 | 87 | 437 | 17 | 437 | 437 |
| Évora | 1 | 15 | 74 | 120 | 16 | 120 | 120 |
| Évora | 2 | 14 | 114 | 157 | 11 | 157 | 157 |
| Évora | 3 | 19 | 27 | 135 | 18 | 135 | 135 |
| Évora | 5 | 19 | 176 | 459 | 17 | 459 | 459 |
| Funchal | 1 | 24 | 93 | não | 21 | não | não |
| Funchal | 2 | 15 | 35 | 167 | 14 | 167 | 167 |
| Funchal | 3 | 16 | 32 | 106 | 16 | 106 | 106 |
| Funchal | 5 | 20 | 82 | 179 | 20 | 179 | 179 |
| Ponta Delgada | 1 | 16 | 20 | 103 | 14 | 103 | 103 |
| Ponta Delgada | 2 | 15 | 35 | 95 | 13 | 95 | 95 |
| Ponta Delgada | 3 | 14 | 12 | 60 | 11 | 60 | 60 |
| Ponta Delgada | 5 | 18 | 32 | 85 | 15 | 85 | 85 |

Nos 28 ensaios, FFMC converge numericamente em 7–24 dias (igualdade exata
em 7–36), DMC em 9–183 dias. DC requer 26–913 dias nos ensaios em que
convergiu; o ensaio anual do Funchal não convergiu. ISI converge em 7–21
dias; BUI/FWI acompanham aqui o prazo de DC, incluindo a exceção do Funchal.
Estes intervalos são resultados empíricos desta amostra, não garantias globais.

Na trajetória iniciada em 2021, DC requer 438 dias em Lisboa, 913 em Faro,
102 em Vila Real, 437 em Castelo Branco, 459 em Évora, 179 no Funchal e
85 em Ponta Delgada. **365 dias não bastam universalmente.** Uma janela
plurianual foi necessária para eliminar a memória em alguns destes casos.

Não existe contradição entre Faro convergir em 96 dias na janela anual e
913 na janela de cinco anos: as sementes foram introduzidas em anos diferentes,
com precipitação e secagem diferentes. O horizonte disponível não determina
sozinho o prazo de convergência.

## Diferenças entre sementes: dimensão e efeito nos seis índices

Máxima dispersão absoluta observada em qualquer dia dos quatro horizontes
de cada região (inclui o início; não confundir com a diferença final):

| Região | FFMC | DMC | DC | ISI | BUI | FWI |
|---|---:|---:|---:|---:|---:|---:|
| Lisboa | 8,92058909 | 148 | 995 | 5,885749446 | 223,2741438 | 34,20067896 |
| Faro | 9,207579234 | 148 | 995 | 9,63066019 | 225,0036063 | 51,96800841 |
| Vila Real | 10,99496787 | 148 | 995 | 5,690053913 | 222,4812626 | 32,69345678 |
| Castelo Branco | 9,21145149 | 148 | 995 | 6,568109838 | 223,4356711 | 37,57933064 |
| Évora | 8,026746143 | 148 | 995 | 6,549092927 | 223,730837 | 40,48612849 |
| Funchal | 11,69322369 | 148 | 995 | 6,404458965 | 222,3158114 | 38,86449316 |
| Ponta Delgada | 10,1611332 | 132,465291 | 995 | 0,5998704253 | 199,111346 | 14,51837371 |

Diferenças finais: **zero exato nos seis índices em 27 dos 28 ensaios**.
A exceção é Funchal, horizonte de um ano:

| Índice | Dispersão absoluta final | Dispersão relativa final |
|---|---:|---:|
| FFMC | 0 | 0 |
| DMC | 0 | 0 |
| DC | 0,5100204211 | 0,0008306929575 |
| ISI | 0 | 0 |
| BUI | 0,01491151568 | 0,0001588578229 |
| FWI | 0,0005576022499 | 0,0001192738829 |

A semente convencional, isoladamente, chega ao mesmo resultado final nos
horizontes de 1, 2, 3 e 5 anos, nas sete regiões (diferença exata zero nos seis
índices). **Isto não basta para demonstrar independência da semente**: no
Funchal outras sementes ainda divergem no ensaio anual. Comparar apenas duas
trajetórias convencionais teria ocultado essa dependência.

`comparacao_sementes.csv` contém 168 linhas (região/horizonte/índice),
com máximos e valores finais absolutos/relativos e os dois prazos de convergência.
Os 28 CSV de dispersão e NPZ preservam toda a evolução, sem arredondamento
para os cálculos; os números deste relatório são apenas apresentados arredondados.

## RH=100%: código, motivo demonstrável e decisão

No cffdrs 1.8.17, commit `9481404cad25387292c1d8692bdb126bbe514d9c`,
`R/fwi.r:181` executa `rh[k] <- ifelse(rh[k] >= 100, 99.9999, rh[k])`
antes de chamar os componentes. O comentário refere apenas limitar RH.
O manual guardado não documenta a substituição e o histórico consultado
não fornece a intenção exata dos autores. Não é possível afirmar honestamente
por que escolheram esse epsilon.

A análise das equações e das implementações consultadas não demonstra uma
singularidade em RH=100: a secagem DMC proporcional a (100−RH) fica zero;
os termos FFMC têm limites finitos. O R interno trata BUI quando os códigos
são zero. Os 18 casos executados com RH=100 são finitos e coincidem com o
R interno. Isto sustenta interpretar o ajuste como particularidade do wrapper,
não como requisito normativo identificado do Canadian FWI.

**Política recomendada A:** aceitar RH real dentro de [0,100], conservar
100%, rejeitar valores fora do intervalo, não substituir 100 por 99,9999
para forçar igualdade com o wrapper público. Não há alteração implementada.

Foram repetidos apenas os 18 casos identificados, em 12 regiões, com o mesmo
estado anterior de cada caso. Cada política usa o seu input explicitamente.
As 108 comparações com R interno (RH=100) e 108 com R público (RH=99,9999)
passaram: **216 verificações**. As **56 reprovações originais** entre inputs
diferentes continuam registadas; não são reclassificadas nem escondidas.

| Índice | Máxima diferença absoluta | Mediana absoluta | Máxima relativa com denominador não nulo | Casos com valor real zero | Reprovações originais |
|---|---:|---:|---:|---:|---:|
| FFMC | 0,0002919127307 | 0,0002210284725 | 7,865637655e-05 | 6 | 18 |
| DMC | 2,757663999e-06 | 2,116545e-06 | 5,60687294e-05 | 14 | 18 |
| DC | 0 | 0 | 0 | 0 | 0 |
| ISI | 1,792948855e-07 | 1,341063127e-11 | 0,0001930336211 | 0 | 1 |
| BUI | 4,687638907e-06 | 4,233079763e-06 | 5,381783104e-05 | 14 | 18 |
| FWI | 3,817955387e-08 | 2,942692225e-12 | 0,0002070588212 | 0 | 1 |

Diferenças relativas usam |ajustado−real|/|real|; quando o real é zero,
a diferença relativa é indefinida e guardada como null, não como zero ou
infinito. DC não depende de RH neste ensaio e a diferença é exatamente zero.
O maior efeito absoluto observado em FWI é cerca de 3,82×10⁻⁸. É pequeno
nestes casos, mas isso não justifica alterar medições reais ou tolerâncias.

Máximo absoluto por caso, na ordem FFMC/DMC/DC/ISI/BUI/FWI:

| Região | Data | FFMC | DMC | DC | ISI | BUI | FWI |
|---|---|---:|---:|---:|---:|---:|---:|
| Braga | 2026-02-09 | 0,0002433301895 | 2,059725e-06 | 0 | 1,048434779e-11 | 4,119439975e-06 | 2,26720893e-12 |
| Braga | 2026-02-11 | 0,0002326698708 | 2,18757e-06 | 0 | 9,369099912e-13 | 4,375129497e-06 | 2,022518526e-13 |
| Cascais | 2026-02-09 | 0,0002564278492 | 2,343825e-06 | 0 | 1,114687291e-10 | 4,687638907e-06 | 2,449248967e-11 |
| Coimbra | 2026-02-10 | 0,0002279005137 | 2,315415e-06 | 0 | 8,050143039e-13 | 4,630819014e-06 | 1,746600697e-13 |
| Gondomar | 2026-02-09 | 0,0001865266382 | 2,04552e-06 | 0 | 3,199116955e-12 | 4,091030028e-06 | 7,060267694e-13 |
| Gondomar | 2026-02-10 | 0,0002141564312 | 2,201775e-06 | 0 | 7,049356156e-13 | 4,403539443e-06 | 1,532061917e-13 |
| Guarda | 2025-11-07 | 0,0001475895899 | 1,352316e-06 | 0 | 1,792948855e-07 | 2,508840818e-06 | 3,817955387e-08 |
| Guimarães | 2025-12-05 | 0,0001993988323 | 1,693236e-06 | 0 | 1,069636012e-11 | 3,386465448e-06 | 2,328017957e-12 |
| Guimarães | 2026-02-10 | 0,0002034997155 | 2,13075e-06 | 0 | 6,273806019e-13 | 4,26148971e-06 | 1,366207241e-13 |
| Loures | 2026-02-09 | 0,0002325274212 | 2,457465e-06 | 0 | 2,255339775e-09 | 4,528238233e-06 | 4,77604394e-10 |
| Matosinhos | 2026-02-09 | 0,000207945149 | 2,116545e-06 | 0 | 1,612490242e-11 | 4,233079763e-06 | 3,557366492e-12 |
| Portalegre | 2025-11-05 | 0,0002409952222 | 2,068248e-06 | 0 | 1,309850194e-09 | 3,575708472e-06 | 4,753729817e-10 |
| Portalegre | 2026-01-21 | 0,0002029111979 | 1,415765e-06 | 0 | 1,508801203e-09 | 2,831523641e-06 | 3,323550397e-10 |
| Portalegre | 2026-02-11 | 0,0002464703069 | 2,088135e-06 | 0 | 1,257708002e-12 | 4,176259869e-06 | 2,696893227e-13 |
| Porto | 2026-02-09 | 0,000207945149 | 2,116545e-06 | 0 | 1,612490242e-11 | 4,233079763e-06 | 3,557366492e-12 |
| Viana do Castelo | 2025-10-19 | 0,0002919127307 | 2,757663999e-06 | 0 | 6,198452034e-09 | 3,24083385e-06 | 4,279218977e-09 |
| Viana do Castelo | 2026-02-10 | 0,0002456238703 | 2,230185e-06 | 0 | 1,110615714e-12 | 4,460359336e-06 | 2,390830358e-13 |
| Vila Nova de Gaia | 2026-02-09 | 0,000207945149 | 2,116545e-06 | 0 | 1,612490242e-11 | 4,233079763e-06 | 3,557366492e-12 |

Este é um estudo de efeito num dia com estado anterior igual. Não mede
acumulação plurianual da política alternativa de RH. Não se extrapola o
efeito máximo observado para todos os climas, estados ou sequências possíveis.

## Proposta objetiva de estabelecimento — sem promoção

É possível definir agora um **certificado técnico de convergência da amostra**:

1. Série horária contínua, 24 intervalos por dia, unidades e coordenadas
   verificadas, sem null/NaN/infinito, proveniência e checksums preservados.
2. Método, versão, calendário, produto e conjunto de sementes fixados e
   rastreáveis; recálculo cronológico sem saltos ou estado silenciosamente reposto.
3. FFMC, DMC e DC exatamente iguais entre todas as sementes ensaiadas na
   data candidata. A igualdade exata evita inventar um limiar de relevância
   operacional e é mais exigente do que a tolerância científica já usada.
4. Registar a primeira data dessa igualdade e confirmar continuidade nas
   datas posteriores disponíveis. A igualdade dos três estados, com os mesmos
   inputs e algoritmo determinístico, implica a mesma evolução futura para
   **essas trajetórias**, enquanto os inputs e o método forem iguais.
5. Qualquer correção histórica ou mudança de produto/método invalida o
   certificado dependente e exige recálculo. Guardar o envelope e a evidência.

Este certificado NÃO equivale ainda ao estado público `estabelecido`.
O conjunto de 27 sementes é finito e não foi demonstrado que delimite todos
os estados fisicamente plausíveis por região. Também não valida o erro da
meteorologia de grelha nem a representatividade espacial. Não foi definido
um limiar material de erro aceitável por uma autoridade científica.

Assim, **não se propõe uma regra automática suficiente para `estabelecido`
nesta fase**. A condição técnica acima pode ser implementada futuramente
como evidência auxiliar, mantendo `reconstruido`, até serem aprovados o
envelope inicial regional, a qualidade meteorológica e o significado
operacional. Não basta esperar 365 dias, nem basta comparar a semente
convencional em dois horizontes.

Recomendação: avançar com validação controlada e revisão científica desses
critérios; **não avançar já para promoção operacional automática**. Para
o ensaio, cinco anos permitiram convergência completa em todas as regiões;
isso não constitui uma prescrição universal de cinco anos.

## Integridade, desempenho e proteção da produção

`verificar.py` passou: checksums das respostas novas/reutilizadas/fontes;
igualdade das horas novas com a resposta bruta; igualdade das horas
reutilizadas com as evidências anteriores; continuidade e unicidade horária;
valores finitos e intervalos válidos; agregações de 24 horas; instantes
regionais; 28 matrizes com 27 sementes; índices finitos e não negativos;
resumos, datas de convergência e 216 verificações de referência RH.
As sete regressões convencionais têm diferença máxima **zero** face aos
resultados anteriores guardados. Nenhuma fórmula nem tolerância foi alterada.

O erro anterior de dimensões foi corrigido no script experimental antes
desta retoma. Os cálculos agora concluíram sem erro. Houve apenas um aviso
de integração opcional matplotlib/cf_xarray; não afetou os índices.

| Região | Tempo medido no processamento dos quatro horizontes (s) | Pico RSS acumulado do processo (MiB) |
|---|---:|---:|
| Lisboa | 1.776 | 389.58 |
| Faro | 1.026 | 400.90 |
| Vila Real | 0.920 | 405.86 |
| Castelo Branco | 3.818 | 419.86 |
| Évora | 3.452 | 419.86 |
| Funchal | 3.436 | 419.86 |
| Ponta Delgada | 3.309 | 419.86 |

Soma dos tempos regionais: **17.737 s**. Inclui preparação/leitura,
cálculos e escrita dentro de cada execução regional; exclui importação inicial,
arranque Docker e verificações posteriores. O RSS é o máximo acumulado do
mesmo processo, não memória incremental por região. Não se extrapola para
o Dell Wyse. Nenhuma nova chamada externa, retry ou falha da fonte nesta retoma.

Consulta Docker apenas de metadados confirmou IDs, imagens, instantes de
arranque e contadores de reinício iguais aos de `producao_antes.txt` nos
quatro containers. Não se fizeram consultas à BD de produção. Isto demonstra
ausência de intervenção desta tarefa nos serviços; não significa que a BD
tenha ficado estática enquanto o scheduler normal continuou a funcionar.

## Reprodutibilidade e ficheiros

Comandos executados nesta retoma:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File experiments/fwi_fase8/executar.ps1 convergencia.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File experiments/fwi_fase8/executar.ps1 rh100.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File experiments/fwi_fase8/executar.ps1 verificar.py
python experiments/fwi_fase8/relatorio.py
python experiments/fwi_fase8/finalizar.py
docker inspect --format '{{.Name}}|{{.Id}}|{{.Image}}|{{.State.StartedAt}}|{{.RestartCount}}' viga_backend_prod viga_frontend_prod viga_db_prod viga_nginx_prod
git diff --check
git status --short
```

Não voltar a executar `dados.py` para reproduzir os cálculos: os dados estão
guardados. `executar.ps1` usa `projeto_final_curso-backend:latest`; para uma
reprodução futura rigorosa deve usar-se a imagem por digest, cujo identificador
está na evidência de produção inicial, além das versões e fontes fixadas.

Ficheiros experimentais da Fase 8:

- `dados.py`, `fontes.py`: preparação anterior; não executados nesta retoma.
- `convergencia.py`: 27 sementes e quatro horizontes; executado sem novas alterações.
- `rh100.py`: comparação das duas políticas com referências preservadas.
- `executar.ps1`: runner isolado, sem rede por defeito.
- `verificar.py`: verificações de integridade, tabela comparativa e manifesto SHA-256.
- `relatorio.py`: gera este relatório a partir dos resultados.
- `finalizar.py`: confirma checksums preservados, metadados de produção,
  sintaxe, espaços e âmbito Git; guarda `verificacao_final.json`.
- `ESTADO.md`: estado final; `RELATORIO.md`: relatório completo.
- `evidencias/`: fontes e dados anteriores preservados; sete observações diárias,
  sete resumos de convergência, 28 NPZ, 28 CSV de dispersão, política,
  `rh100_impacto.json`, `comparacao_sementes.csv`, `integridade.json`,
  `checksums_finais.json` e evidência de produção. O manifesto enumera os ficheiros
  de evidência e os seus hashes, excluindo-se a si próprio.

Não foram alterados ficheiros de produção nem textos da interface pública.
Os únicos textos novos são os relatórios e mensagens experimentais em PT-PT.
Não foi feito commit.

## Fontes científicas preservadas

- [cffdrs 1.8.17, código público](https://raw.githubusercontent.com/cffdrs/cffdrs_r/9481404cad25387292c1d8692bdb126bbe514d9c/R/fwi.r): transformação da RH antes das funções internas.
- [Manual da mesma versão](https://raw.githubusercontent.com/cffdrs/cffdrs_r/9481404cad25387292c1d8692bdb126bbe514d9c/man/fwi.Rd): contexto dos inputs e inicialização; não justifica o epsilon.
- [xclim 0.62.0](https://raw.githubusercontent.com/Ouranosinc/xclim/v0.62.0/src/xclim/indices/fire/_cffwis.py): implementação efetivamente usada, sem substituição de RH=100.
- [Van Wagner e Pickett, 1985](https://climatelibrary.ecc.gov.nt.ca/dataset/c36897fc-7ee0-44ea-9e8a-3b2147911139/resource/a4df620a-52bc-4a78-afed-2e6a8dd226d4/download/fwi_equation_19973.pdf): equações de referência.
- [Canadian Forest Service, NOR-X-424, 2015](https://publications.gc.ca/collections/collection_2016/rncan-nrcan/Fo133-1-424-eng.pdf): código publicado de referência.

As conclusões de convergência são inferências dos ensaios aqui guardados,
não limiares prescritos por estas publicações. A intenção histórica dos autores
do wrapper quanto a RH=99,9999 permanece não documentada nas fontes consultadas.
