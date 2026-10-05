# Fase 6 — validação operacional real controlada

Ensaio executado em 05/10/2026. Não foram alterados ficheiros de produção,
fórmulas, modelos, frontend, serviços, configurações ou dados de produção.
Não foi feito commit. Os ficheiros novos pertencem exclusivamente a esta pasta.

## A–D. Região, fonte, dados e reconstrução

Lisboa: 01/10/2025–30/09/2026, 365 dias anteriores à data operacional escolhida,
01/10/2026. As outras quatro regiões: 02/08/2026–30/09/2026, 60 dias cada.
Só foram executadas depois de Lisboa passar os controlos de dados, sequência,
API e comparação científica e de se examinarem os episódios meteorológicos.

BD descartável `viga_fwi_test_phase6`, PostGIS 15/3.3, no container
`viga-fwi-phase6-db`, rede `none`, sem portas publicadas. Foi preparado o modelo
Regiao e as tabelas FWI existentes, com o catálogo oficial do projeto. Os IDs
foram consultados por nome na BD descartável: Lisboa 1, Faro 5, Vila Real 17,
Funchal 19, Ponta Delgada 20. Não são IDs presumidos da produção.

Fonte: Open-Meteo Archive `/v1/archive`, `models=ecmwf_ifs`, sem fallback.
Coordenadas consultadas: Lisboa 38.7169/-9.1399; Faro 37.0194/-7.9322;
Vila Real 41.3006/-7.7457; Funchal 32.6669/-16.9241;
Ponta Delgada 37.7412/-25.6756. As coordenadas da grelha devolvidas estão nos
ficheiros `*_recolha.json`; Lisboa devolveu 38.69947/-9.196167.

Validados °C, %, km/h a 10 m e mm, timestamps GMT com offset zero, latitude,
longitude, ordem cronológica, ausência de duplicados/nulos e exatamente
24 intervalos `(t-24h,t]` por dia. Temperatura, humidade e vento correspondem a
t; a precipitação é a soma das 24 horas, não a precipitação do dia civil.
Referência: 12:00 UTC no Continente/Madeira e 13:00 UTC nos Açores.

A resposta foi guardada integralmente, com SHA-256, URL, parâmetros, instante
de ingestão e coordenadas. O modelo é explicitamente selecionado no pedido;
a resposta JSON não identifica independentemente o modelo. Portanto, a
proveniência do produto assenta no contrato da fonte e no pedido preservado,
não numa confirmação autónoma do conteúdo. A documentação descreve IFS
horário global desde 2017: https://open-meteo.com/en/docs/historical-weather-api.
São dados em grelha, não medições garantidas de uma estação local.

Foram feitos cinco pedidos HTTP reais, um por região, sem retries nem erros.
As respostas contêm também horas de margem dos dias civis pedidos; apenas
as 14 520 horas necessárias foram usadas/persistidas (Lisboa 8760;
restantes regiões 1440 cada). Total: 605 dias persistidos, cinco reconstruções,
zero linhas em `fwi_diario`. Todas terminaram `reconstruido`.

Semente explícita em cada região, no dia anterior à janela: FFMC=85, DMC=6,
DC=15, qualidade `inicializacao_convencional`, origem registada como ensaio.
Não é uma política científica de estabelecimento. Nem 365 nem 60 dias
promovem a sequência. A repetição da reconstrução completa calculou zero
novos dias; não houve duplicação.

## E. Estatísticas de Lisboa

Precisão completa preservada nos JSON. Valores arredondados só nesta tabela.

| Índice | Mínimo | P05 | P25 | Mediana | P75 | P95 | Máximo |
|---|---:|---:|---:|---:|---:|---:|---:|
| FFMC | 11,2051 | 33,7415 | 65,9063 | 84,0681 | 90,4411 | 93,9598 | 96,0611 |
| DMC | 0,0472 | 0,4543 | 2,8952 | 22,1454 | 91,1659 | 234,3528 | 298,8211 |
| DC | 1,7200 | 2,4400 | 19,6280 | 87,8993 | 476,3946 | 846,4626 | 928,4086 |
| ISI | 0,00000362 | 0,0203 | 1,0411 | 3,3318 | 7,4889 | 10,8811 | 14,4720 |
| BUI | 0,0901 | 0,5893 | 4,2552 | 26,1122 | 117,9549 | 267,2008 | 331,1662 |
| FWI | 0,00000080 | 0,0048 | 0,4685 | 6,1831 | 28,5141 | 38,2612 | 48,4577 |

Estatísticas dos seis índices de cada região: `*_resultado.json`.

## F–G. Anomalias e comportamento meteorológico

Não foram encontrados NaN, infinitos, negativos, lacunas ou saltos de dias.
As ligações ao dia anterior e os snapshots FFMC/DMC/DC foram conferidos.
Não foi imposto um teto artificial ao FWI ou aos códigos de secura.

Os maiores saltos absolutos de cada índice foram selecionados automaticamente
e incluídos na amostra independente. São variações reais do cálculo, não
erros a suavizar. `Lisboa_episodios.json` preserva os inputs e resultados.

- **Seca:** 20 dias com precipitação exatamente zero, de 14/07 a 02/08/2026.
  DMC cresceu de 156,01 para 231,00 e DC de 596,19 para 763,24. FFMC variou
  com a humidade; FWI não cresceu monotonamente porque o vento também variou.
- **Chuva forte:** 13/11/2025, 56,5 mm/24 h, humidade 91%. FFMC caiu de
  59,73 para 25,30; DC de 56,13 para 2,80. Nos dias seguintes continuou a
  chover, incluindo 36,2 mm em 15/11, quando FFMC atingiu 11,21.
- **Seca para chuva:** de 22 para 23/08/2026, 4,2 mm e humidade 97%:
  FFMC 89,76→42,23; DMC 298,82→101,14; FWI 31,12→0,394. A queda grande de DMC
  foi verificada contra R, sem alterar constantes ou tolerâncias.
- **Persistência profunda:** em 24/08, 18,5 mm fizeram DC cair de 892,88
  para 700,82. O valor permanece elevado após o período seco; não foi truncado.
- **Chuva para secagem:** após a sequência chuvosa de 23–27/08, a chuva foi
  0,3 mm em 28/08 e zero em 29/08; FFMC recuperou de 70,32 para 81,30 e
  85,53; DMC/DC retomaram a subida. FWI depende também do vento e não tem
  de acompanhar monotonamente cada código.
- **Vento elevado:** 07/02/2026, 38,6 km/h, mas 20,6 mm/24 h; FWI≈0,406.
  Vento forte isoladamente não implica FWI elevado quando os combustíveis
  modelados estão húmidos.
- **Humidade elevada:** 01/02/2026, 98%, com 9,5 mm; FFMC≈17,36 e
  FWI≈0,0000208, coerentes com condições húmidas.
- **Maior queda FWI:** 29→30/09/2026, 44,87→4,46; vento 25,2→1,8 km/h,
  chuva 0→2,4 mm. O ISI caiu 12,57→0,70. Este salto também passou na referência.

Isto é uma avaliação qualitativa dos inputs/resultados, não validação contra
incêndios observados nem prova da representatividade local do produto.

## H. Comparação independente

Usado o código R cffdrs **1.8.17** já preservado na prova técnica, sem alterações.
`lat.adjust=TRUE`; cada dia da amostra recebe os inputs reais e o estado
anterior persistido. Não se repetiu a prova científica completa da Fase 1.
Esta amostra verifica transições diárias independentes; não constitui uma
segunda reconstrução anual integral em R.

Tolerâncias originais: `atol=1e-8`, `rtol=1e-10`, inalteradas.

| Região | Dias na amostra | Comparações dos seis índices | Maior erro absoluto |
|---|---:|---:|---:|
| Lisboa | 18 | 108 | 4,974×10⁻¹³ |
| Faro | 14 | 84 | 4,832×10⁻¹³ |
| Vila Real | 12 | 72 | 2,132×10⁻¹³ |
| Funchal | 11 | 66 | 3,979×10⁻¹³ |
| Ponta Delgada | 15 | 90 | 4,832×10⁻¹³ |

Todas as 420 comparações passaram. Inputs, outputs R/xclim, diferenças
absolutas e relativas: `*_amostra_inputs.csv`, `*_referencia.csv` e
`*_comparacao.json`. A divergência conhecida perante cffdrs **1.9.2** permanece;
não se afirma equivalência com essa variante.

## I–J. Desempenho e validação geográfica

| Região | Dias | Horas | Recolha (s) | Reconstrução (s) | Pico RSS do processo (MiB) | FWI mínimo–máximo |
|---|---:|---:|---:|---:|---:|---:|
| Lisboa | 365 | 8760 | 0,650 | 15,062 | 418,88 | 0,0000008–48,46 |
| Faro | 60 | 1440 | 0,423 | 6,292 | 375,41 | 4,18–53,72 |
| Vila Real | 60 | 1440 | 0,354 | 4,941 | 376,80 | 0,0000054–31,73 |
| Funchal | 60 | 1440 | 0,360 | 5,075 | 378,11 | 0,27–35,21 |
| Ponta Delgada | 60 | 1440 | 0,361 | 5,127 | 376,65 | 0,033–9,94 |

Lisboa: soma dos tempos medidos de recolha e reconstrução **15,712 s**.
A reconstrução inclui inicialização, cálculo e commits diários; a recolha
inclui HTTP, interpretação e validação. Não inclui arranque dos containers,
imports anteriores ao cronómetro, comparação R, API posterior e análise.
RSS obtido por `resource.getrusage(...).ru_maxrss` no processo Linux; não é
memória incremental do xclim nem inclui PostgreSQL, Docker ou browser.

A recolha foi feita em lote no adaptador experimental e entregue ao fluxo
existente em 365/60 leituras diárias. Este ensaio **não mede** o custo da
estratégia de um pedido remoto por dia do comando atual. Zero retries e zero
falhas da fonte; não houve teste de indisponibilidade prolongada da fonte.
Não foram extrapolados resultados para o Dell Wyse.

## K. API e frontend

A API real foi executada com FastAPI TestClient, router de produção e sessões
da BD descartável; não se importou `main` nem se iniciou o scheduler.
Foram guardadas respostas antes/depois e histórico das cinco regiões.

Exemplo Lisboa após a reconstrução:

```json
{
  "estado": "em_inicializacao",
  "estado_inicializacao": "reconstruido",
  "operacional": false,
  "estabelecido": false,
  "data_referencia": "2026-09-30",
  "instante_referencia_utc": "2026-09-30T12:00:00Z",
  "fwi": 4.464203567142161,
  "atualidade": "desatualizado"
}
```

O campo de atualidade está corretamente desatualizado face a 05/10, pois
esta é uma janela histórica deliberadamente concluída em 30/09. Não se
alterou o relógio nem se apresentou o ensaio como atualização do dia corrente.
Histórico cronológico: 365/60 resultados, revisão ativa, sem duplicados.
Ausência inicial devolveu null, não zero. Regressão API verifica zero válido.

Edge headless apresentou `4,46`, data 30/09/2026 e
“Não operacional — valor técnico, quando disponível.”, sem indicação
“Operacional estabelecido”. Nos detalhes apresentou proveniência e 30 dias.
O teste reproduz no browser as respostas HTTP reais exportadas da API
isolada; **não é uma ligação HTTP direta browser→API→PostgreSQL**.
As outras áreas usam o simulador existente para não tocar na produção.
Zero e null foram variações explicitamente simuladas apenas no teste de UI.
Evidências: `browser.json` e `Lisboa_dashboard.png`.

## Testes e incidentes do ensaio

- Quatro testes novos de evidências passaram, com verificações para as cinco
  regiões, todos os dias, intervalos, somas, cadeia, API e referência.
- 19 testes existentes da API Fase 4 passaram, incluindo zero/null e erros.
- Dez testes frontend FWI passaram.
- Um cenário Edge Fase 6 passou (antes/depois, histórico, zero/null).
- Cinco artefactos ML, inferência dos dois modelos e SHAP passaram;
  resultado preservado em `ml.json`.
- `pip check`: `No broken requirements found.`
- `git diff --check` passou; ficheiros novos também verificados sem staging.

Incidentes restritos ao ensaio: a política PowerShell impediu a primeira
invocação do script; foi autorizado `-ExecutionPolicy Bypass` apenas no
processo, sem alteração persistente da política. A invocação agregada seguinte
terminou com código 1 no invólucro PowerShell, embora as quatro regiões
tenham concluído e as verificações individuais de referência indiquem
sucesso no log; os ficheiros de evidência foram posteriormente validados
pelos quatro testes, que terminaram com código 0. Não se considerou o código
agregado prova de sucesso nem se repetiu a recolha desnecessariamente.

O primeiro teste browser falhou a guardar a captura devido a um caminho com
espaços codificados; foi corrigido apenas o script experimental com
`fileURLToPath` e a repetição passou. Não foi um erro da aplicação.
Avisos não fatais: depreciação Starlette/httpx, integração opcional matplotlib
e nomes de features nas matrizes da prova ML. Não foram alteradas dependências.

## L. Recomendação

**Avançar para uma validação alargada das restantes regiões em ambiente
isolado**, mantendo `reconstruido` e `operacional=false`.
Não recomendar ainda promoção automática a operacional ou publicação em
produção. Faltam um critério científico documentado de estabelecimento,
validação regional da representatividade meteorológica e medição do fluxo
de recolha real no hardware de destino. As quatro janelas de 60 dias não
demonstram estabilidade anual nem convergência do DC.

Não ocorreu nenhum dos critérios técnicos de bloqueio do utilizador.
O modelo pedido não ser identificado novamente na resposta é uma limitação
de rastreabilidade declarada, não foi interpretado como validação independente.

## M. Comandos relevantes executados

Executados a partir da raiz do projeto; caminhos absolutos usados nos mounts.
Nos exemplos abaixo, `$raiz` corresponde à raiz e `$ev` a esta pasta/evidencias.
Não se carregou `.env.prod`, não se executou Compose up/down, e não se
executaram comandos dentro dos containers de produção.

```powershell
git status --short
docker ps -a --format '{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}'
docker images --format '{{.Repository}}:{{.Tag}}|{{.Size}}'
docker inspect --format '{{.Name}}|{{.Id}}|{{.Image}}|{{.State.StartedAt}}|{{.RestartCount}}' viga_backend_prod viga_frontend_prod viga_db_prod viga_nginx_prod
docker run --detach --rm --name viga-fwi-phase6-db --network none -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_DB=viga_fwi_test_phase6 postgis/postgis:15-3.3
```

Invocações Python de preparação/reconstrução usaram este padrão:

```powershell
docker run --rm --network container:viga-fwi-phase6-db --mount "type=bind,source=$raiz,target=/workspace,readonly" --mount "type=bind,source=$ev,target=/evidencias" -e DATABASE_URL=postgresql+psycopg2://postgres@127.0.0.1/viga_fwi_test_phase6 -e PYTHONDONTWRITEBYTECODE=1 projeto_final_curso-backend:latest python /workspace/experiments/fwi_fase6/ensaio.py preparar
# Mesmo padrão: ensaio.py reconstruir Lisboa
# Recolha: --network bridge, DATABASE_URL com destino inacessível de teste,
# ensaio.py recolher Lisboa 365; nome temporário viga-fwi-phase6-fetch.
# Reconstrução Lisboa: nome temporário viga-fwi-phase6-run.
# Análise: --network none, analisar.py preparar Lisboa / comparar Lisboa.
# R: --network none, imagem r-base:4.5.3,
# Rscript /workspace/experiments/fwi_fase6/referencia.R Lisboa.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./experiments/fwi_fase6/regioes_adicionais.ps1
```

`regioes_adicionais.ps1` contém os comandos completos das quatro regiões,
parando à primeira falha detetada. Imagens existentes reutilizadas; sem build.

```powershell
# Em docker run --rm --network none, repositório readonly:
python /workspace/experiments/fwi_fase6/test_evidencias.py
python /workspace/experiments/xclim_062/validar_ml.py /evidencias/ml.json
python -m pip check
# working directory /workspace/backend:
python -m unittest discover -s tests -p test_fwi_fase4.py -v
# Na pasta frontend:
node --test tests/fwiDiario.test.mjs
$env:VITE_API_URL='/api'
npm.cmd run dev -- --host 127.0.0.1 --port 5174 --strictPort
# Na raiz, Playwright temporário já existente via VIGA_PLAYWRIGHT_MODULE:
node --test --test-isolation=none --test-name-pattern='Fase 6:' experiments/fwi_fase6/frontend.browser.mjs
docker exec viga-fwi-phase6-db psql -U postgres -d viga_fwi_test_phase6 -c 'SELECT count(*) AS horas FROM fwi_horario; SELECT count(*) AS dias FROM fwi_historico_dia; SELECT count(*) AS operacionais FROM fwi_diario; SELECT estado,count(*) FROM fwi_reconstrucao GROUP BY estado;'
docker inspect --format '{{.HostConfig.NetworkMode}}|{{json .HostConfig.PortBindings}}' viga-fwi-phase6-db
git diff --check
# Ficheiros novos: git diff --no-index --check -- NUL <ficheiro>
docker stop viga-fwi-phase6-db
```

## N–O. Recursos temporários e produção

Criados: `viga-fwi-phase6-db` com BD `viga_fwi_test_phase6`, os containers
efémeros `viga-fwi-phase6-fetch`, `viga-fwi-phase6-run` e runners sem nome
fixo, todos com `--rm`. A BD foi parada/removida no fim; os snapshots,
respostas brutas e resultados ficaram nesta pasta. Não foi criado volume
nomeado nem publicada porta Docker. Vite local escutou só em 127.0.0.1:5174
para o ensaio Edge e foi terminado no fim.

Produção: mesmos IDs, imagens, instantes de arranque e RestartCount=0 antes
e depois, conforme `producao_antes.txt`/`producao_depois.txt`. Não foram
executados pedidos à API de produção nem acessos à sua BD. Os jobs normais
da produção podem continuar a alterar os seus próprios dados durante o
ensaio; não se afirma que a BD ficou globalmente congelada.

Ficheiros criados: `ensaio.py`, `analisar.py`, `referencia.R`,
`regioes_adicionais.ps1`, `test_evidencias.py`, `frontend.browser.mjs`,
este relatório e as evidências em `evidencias/`. Nenhum ficheiro existente
foi alterado. Nenhum texto público da aplicação foi criado ou alterado.
