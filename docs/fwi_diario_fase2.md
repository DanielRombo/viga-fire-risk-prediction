# FWI diário — Fase 2

Esta fase acrescenta recolha horária, preparação diária e recuperação cronológica.
Não altera o FWI apresentado nas rotas públicas nem no frontend. Reutiliza o
adaptador da Fase 1, xclim 0.62.0, variante clássica validada contra cffdrs 1.8.17.
A divergência documentada face a cffdrs 1.9.2 mantém-se; não há alterações de fórmulas.

## Recolha e persistência

`services/open_meteo_fwi.py` consulta `/v1/forecast`, produto `best_match`, com
`temperature_2m`, `relative_humidity_2m`, `wind_speed_10m` e `precipitation`.
As unidades são explicitamente °C, %, km/h e mm, com timestamps GMT/UTC.
Não utiliza `current weather`. São dados meteorológicos de modelos, não
observações garantidas de estações no terreno.

A precipitação horária representa a soma da hora precedente, segundo a
[documentação Open-Meteo](https://open-meteo.com/en/docs). Para a referência `t`,
são necessárias as 24 amostras de `t-23h` até `t`, que cobrem `(t-24h, t]`.
Temperatura, humidade e vento são os valores em `t`.
Continente/Madeira usam 12:00 UTC e Açores 13:00 UTC, sem ajuste de hora de verão.

Novas tabelas, criadas de forma aditiva no arranque:

| Tabela | Conteúdo e unicidade |
|---|---|
| `fwi_horario` | Região, instante UTC, quatro valores meteorológicos, coordenadas consultadas e da grelha, produto, ingestão, qualidade e problemas. Única por região/instante/produto. |
| `fwi_processamento` | Região/versão, data pendente, estado, tentativas, falhas consecutivas, última/próxima tentativa e causa. Única por região/versão. |

A tabela `fwi_diario` da Fase 1 continua a guardar os seis índices e o estado
anterior. O histórico meteorológico existente não é transformado nem apagado.
Valores ausentes permanecem nulos e zeros mantêm-se válidos. Dados completos
persistidos são preservados; uma nova resposta válida pode reparar uma hora
incompleta/inválida. Alterações das coordenadas exigem revisão explícita.

## Processamento e recuperação

O scheduler existente recebe um único job `fwi_diario`, de 15 em 15 minutos,
com primeira verificação no arranque, `max_instances=1` e `coalesce=True`.
Os jobs atuais de meteorologia e NASA mantêm-se. Iniciar novamente um scheduler
já ativo não regista outros jobs.

`executar_ciclo_fwi` resolve as regiões preparadas e isola falhas por região.
`processar_regiao` processa no máximo três dias por ciclo, por ordem cronológica.
Cada dia segue o fluxo:

1. Adquirir um bloqueio transacional PostgreSQL por região.
2. Identificar o último FWI válido e o dia imediatamente seguinte.
3. Esperar que a referência UTC desse dia tenha passado.
4. Usar a janela horária persistida ou recolhê-la da Open-Meteo.
5. Validar os 24 intervalos, qualidade, coordenadas e unidades.
6. Calcular com FFMC/DMC/DC do dia anterior através do adaptador da Fase 1.
7. Confirmar o FWI e o avanço da data pendente na mesma transação.

Uma lacuna interrompe apenas a região afetada. As tentativas seguintes respeitam
um intervalo crescente de 15 minutos até seis horas. Dados incompletos podem
ficar guardados como evidência sem produzir um FWI válido. Uma falha de cálculo
reverte o resultado diário; uma falha no commit reverte toda a transação desse
dia. Se a própria BD impedir o registo da causa, esta fica no logging.

Sem estado anterior estabelecido, recolhe-se a janela mais recente já concluída
e fica registada a necessidade de inicialização. Não se inventam FFMC/DMC/DC
nem uma data inicial da sequência: `data_pendente` permanece nula nesse caso.
Registos ainda em inicialização não são tratados como estados estabelecidos.

Os estados internos incluem `pendente`, `aguardar_referencia`, `aguardar_dados`,
`inicializacao_necessaria`, `reconstrucao_necessaria` e `erro`.
Uma região ocupada por outro processo é retomada num ciclo posterior.

## Limitações intencionais

- Não foi implementada a política definitiva de inicialização nem a integração
  completa de histórico externo.
- A recolha remota está limitada à janela recente de 92 dias da Forecast API.
  Dados locais completos mais antigos podem ser utilizados; faltando-os, fica
  registado `historico_necessario`, sem saltar o dia pendente.
- A primeira janela completa persistida é preservada. Não se reprocessam
  automaticamente revisões posteriores do produto meteorológico.
- Não foram feitas chamadas meteorológicas reais na validação; as APIs foram
  simuladas. Os testes verificam o contrato documentado e as falhas da fonte.
- Não se aplicaram alterações de esquema à BD de produção nem se substituíram
  os contentores de produção. As novas tabelas serão preparadas no próximo
  arranque da aplicação com esta versão.

## Validação desta fase

- 19 testes da Fase 2 passaram em PostgreSQL/PostGIS descartável, incluindo
  bloqueio concorrente, idempotência, recuperação, falha intermédia e rollback.
- Regressão backend: 110 testes considerados, sete ignorados por condições de
  ambiente. Os sete testes científicos da classe `CalculoDiarioTests` da Fase 1
  foram excluídos, conforme solicitado. A concorrência da Fase 2, ignorada na
  execução SQLite, passou separadamente em PostgreSQL.
- Arranque testado com Uvicorn e operações externas simuladas: HTTP 200,
  apenas um scheduler e um job FWI.
- Cinco artefactos ML validados; previsão técnica com ambos os modelos disponível
  (Kaggle 0,831; ANPC 0,112; ensemble 0,4). Sem alterações aos modelos.
- `pip check` passou e o build de produção com `--no-cache` concluiu, na imagem
  isolada `viga-fwi-phase2:test`.
- Versões verificadas na imagem: Python 3.11.17, xclim 0.62.0, NumPy 2.4.4,
  Numba 0.68.0, scikit-learn 1.8.0, joblib 1.5.3, XGBoost 3.2.0 e SHAP 0.51.0.
  Os requirements e constraints da Fase 1 não foram alterados.

Os testes novos estão em `backend/tests/test_fwi_fase2.py`; a verificação do
scheduler foi acrescentada a `backend/tests/test_production_startup.py`.
A prova técnica e os casos científicos da Fase 1 não foram repetidos.

## Textos e interface

Não foram criados ou alterados textos no frontend ou nas respostas públicas.
Os novos textos PT-PT destinam-se a documentação, logging e causas internas de
indisponibilidade (falha da fonte, timeout, dados inválidos/incompletos,
inicialização necessária ou histórico indisponível).
