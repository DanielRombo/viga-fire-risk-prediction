# FWI diário — Fase 4: API paralela ao legado

## Contrato e compatibilidade

São acrescentados dois endpoints públicos apenas de leitura:

```text
GET /api/fwi-diario/{id_regiao}
GET /api/fwi-diario/{id_regiao}/historico
```

O primeiro devolve o registo mais recente da seleção, com a respetiva validade.
O segundo devolve `resultados` por data crescente, sem agregar séries ou revisões.
Nenhum pedido recolhe dados, calcula índices, altera estados ou promove uma
reconstrução. O campo `fwi` de `/api/risco/{id_regiao}` mantém a heurística
legada e não foi renomeado nem substituído. O frontend permanece inalterado.

Parâmetros comuns:

| Parâmetro | Comportamento |
|---|---|
| `serie=auto` | Predefinição: usa `fwi_diario` se existir algum registo da versão adotada; caso contrário, usa a revisão mais recente da reconstrução. Não escolhe com base no valor ou na atualidade. |
| `serie=operacional` | Consulta exclusivamente `fwi_diario`. O nome da série não garante que o registo esteja estabelecido: verificar `estado` e `operacional`. |
| `serie=reconstrucao` | Consulta exclusivamente `fwi_historico_dia`, na revisão ativa. |
| `revisao=N` | Seleciona uma revisão histórica explícita da mesma região; implica a série de reconstrução. É incompatível com `serie=operacional`. |

Parâmetros do histórico: `inicio` e `fim` inclusivos (AAAA-MM-DD), `limite`
(predefinição 100, máximo 366) e `offset` (predefinição zero). A resposta inclui
`tem_mais`. Para paginar uma reconstrução de forma estável, fixar `serie` e a
`revisao` devolvidas na primeira página. Se uma nova revisão ainda não tiver
dias, não se reutilizam silenciosamente os dias da revisão antiga.

As duas séries são independentes nesta fase. Não se fundem dias coincidentes,
não se transfere automaticamente uma reconstrução para `fwi_diario` e não se
oculta uma série antiga/incompleta escolhendo outra mais favorável. O consumidor
pode pedir explicitamente cada série. A versão consultada é
`xclim-0.62.0-cffdrs-1.8.17-classico-v1`.

## Campos de cada resultado

- `estado`, `mensagem`, `estado_inicializacao`: disponibilidade pública e estado
  persistido da sequência, apresentados separadamente.
- `data_referencia`, `instante_referencia_utc`, `calculado_em`: datas reais
  persistidas; não são substituídas pela hora do pedido.
- `ffmc`, `dmc`, `dc`, `isi`, `bui`, `fwi`: valores sem arredondamento adicional.
  Zero é válido; ausência, NaN, infinito e valores fora dos limites tornam o
  campo nulo e impedem `ok`.
- `origem`: produto meteorológico persistido; `metodo`, `versao`,
  `versao_xclim=0.62.0` e `variante=classica_cffdrs_1.8.17` identificam o cálculo.
  Não é afirmada equivalência com cffdrs 1.9.2.
- `qualidade`, `validade`: qualidade da inicialização e validade do registo.
- `estabelecido`: registo completo e coerente, pertencente a uma sequência
  estabelecida; pode ser antigo.
- `operacional`: verdadeiro apenas quando `estado=ok` e `estabelecido=true`.
  Não significa que o frontend já utiliza o resultado.
- `atualidade`: `atual`, `desatualizado` ou `indisponivel`, avaliada separadamente
  da qualidade científica e da atividade da revisão.
- `data_referencia_esperada`, `prazo_calculo_utc`, `atraso_permitido_minutos`:
  regra diária aplicada pelo servidor.
- `serie`, `revisao`, `revisao_ativa`: identificação explícita da seleção.
  Na série operacional não há revisões históricas, pelo que estes dois últimos
  campos são nulos.
- `proveniencia`: identificador do registo, da reconstrução e assinatura
  persistida. `processamento` inclui código de erro, data pendente e próxima
  tentativa, sem expor exceções internas ou o texto livre da causa.

O estado `reconstruido` e a inicialização convencional são expostos como
`em_inicializacao`, com o estado original em `estado_inicializacao`, e nunca
como operacionais. Durante a reconstrução o mesmo bloqueio se aplica, mesmo
que existam valores técnicos. Uma revisão substituída/desatualizada nunca é
operacional. Um estado histórico `estabelecido` só permite essa classificação
se a qualidade da semente também for estabelecida e o registo estiver ativo,
completo e calculado. Esta leitura não cria um novo critério científico.

## Atualidade diária

A regra meteorológica de duas horas não é utilizada.

- Continente/Madeira: referência às 12:00 UTC; prazo às 13:00 UTC.
- Açores: referência às 13:00 UTC; prazo às 14:00 UTC.
- Tolerância técnica: 60 minutos, definida em `ATRASO_PERMITIDO_MINUTOS`.
- Antes do prazo de hoje, a data exigida é ontem. A partir do prazo, inclusive,
  é hoje. Um resultado de hoje já calculado após a referência pode ser aceite
  antes do prazo. O horário de verão não altera estas horas UTC.
- Recalcular hoje um resultado de anteontem não o torna atual.
- Instantes futuros, inconsistentes com a região, ou timestamps de cálculo
  ausentes/anteriores à referência são dados inválidos.

Os 60 minutos são uma política técnica de publicação desta API; não constituem
uma garantia de latência da fonte nem alteram o scheduler. O histórico também
indica a atualidade relativa ao momento da consulta: um dia antigo pode ser
estabelecido e estar temporalmente desatualizado.

No último resultado, uma falha registada para uma data já devida pode devolver
`erro_fonte`, `dados_incompletos` ou `estado_anterior_ausente`, conservando os
valores técnicos do último registo e a sua `atualidade`. Uma falha de amanhã
não invalida o resultado de hoje. No histórico não se aplica a falha mais
recente do processamento indiscriminadamente a todos os dias.

## HTTP

- 200: consulta concluída, incluindo indisponibilidade explícita e histórico
  vazio (`resultados=[]`). Um HTTP 200 não significa `operacional=true`.
- 404: região ou revisão inexistente.
- 422: parâmetros inválidos ou intervalo de datas invertido.
- 503: não foi possível consultar a BD. Não é devolvida uma lista vazia como
  substituto de uma falha de infraestrutura.

As tabelas já pertencem às Fases 1–3. A importação da nova rota regista os
modelos antes do `Base.metadata.create_all` existente no arranque; não são
alteradas colunas nem dados. Os pedidos GET não criam tabelas.

## Exemplos

Exemplo ilustrativo completo, para uma consulta em 2026-10-04 às 15:00 UTC.
Os valores zero são uma fixture técnica de teste, não uma observação real:

```json
{
  "id_regiao": 1,
  "tipo": "fwi_diario_classico",
  "estado": "ok",
  "mensagem": "FWI diário estabelecido e atual.",
  "data_referencia": "2026-10-04",
  "instante_referencia_utc": "2026-10-04T12:00:00Z",
  "calculado_em": "2026-10-04T14:59:00Z",
  "ffmc": 0.0,
  "dmc": 0.0,
  "dc": 0.0,
  "isi": 0.0,
  "bui": 0.0,
  "fwi": 0.0,
  "origem": "open-meteo-forecast-best-match-horario-v1",
  "metodo": "Canadian Fire Weather Index diário — variante clássica adotada",
  "versao": "xclim-0.62.0-cffdrs-1.8.17-classico-v1",
  "versao_xclim": "0.62.0",
  "variante": "classica_cffdrs_1.8.17",
  "qualidade": "estabelecido",
  "validade": "valido",
  "estado_inicializacao": "estabelecido",
  "estabelecido": true,
  "operacional": true,
  "atualidade": "atual",
  "data_referencia_esperada": "2026-10-04",
  "prazo_calculo_utc": "2026-10-04T13:00:00Z",
  "atraso_permitido_minutos": 60,
  "serie": "operacional",
  "revisao": null,
  "revisao_ativa": null,
  "proveniencia": {"id_registo": 1, "id_reconstrucao": null, "assinatura": "<assinatura persistida>"},
  "processamento": null
}
```

Excertos de outras respostas (os restantes campos do contrato mantêm-se):

```json
{"estado":"indisponivel","estado_inicializacao":"sem_estado","fwi":null,"operacional":false}
```

```json
{"estado":"em_inicializacao","estado_inicializacao":"reconstruido","fwi":0.0,"operacional":false,"serie":"reconstrucao","revisao":2,"revisao_ativa":true}
```

```text
GET /api/fwi-diario/1/historico?serie=reconstrucao&revisao=1&inicio=2024-01-01&fim=2024-12-31&limite=100
```

## Textos públicos novos

| Estado | Mensagem literal |
|---|---|
| `ok` | FWI diário estabelecido e atual. |
| `desatualizado` | O FWI diário não corresponde à data esperada ou pertence a uma revisão desatualizada. |
| `indisponivel` | Não existe um resultado FWI diário disponível para esta seleção. |
| `em_inicializacao` | A sequência FWI ainda não está estabelecida; os valores apresentados são apenas técnicos. |
| `em_reconstrucao` | A sequência FWI está em reconstrução; os valores apresentados não são operacionais. |
| `dados_incompletos` | Os dados necessários ao FWI diário estão incompletos ou inválidos. |
| `erro_fonte` | A atualização do FWI diário está bloqueada por uma falha da fonte meteorológica. |
| `estado_anterior_ausente` | Não existe um estado anterior estabelecido para continuar o FWI diário. |

Outros textos públicos acrescentados:

- `Região não encontrada.`
- `Revisão FWI não encontrada para esta região.`
- `A seleção de revisão aplica-se apenas à série de reconstrução.`
- `A data inicial não pode ser posterior à data final.`
- `Não foi possível consultar o FWI diário. Tente novamente mais tarde.`
- Método: `Canadian Fire Weather Index diário — variante clássica adotada`.
- Grupo OpenAPI: `FWI diário`.
- Resumos OpenAPI: `Consultar o novo FWI diário de uma região` e
  `Consultar o histórico do novo FWI diário`.

Não foram alterados textos existentes do frontend ou do contrato legado.

## Validação e limites desta fase

- 19 testes novos passaram em PostgreSQL/PostGIS descartável: contrato HTTP,
  zeros/nulos, estados de inicialização, referências regionais, tolerância,
  revisões, ordenação, paginação, parâmetros inválidos, erro de BD e ausência
  de escritas nos pedidos GET.
- Regressão backend: 150 testes considerados, oito ignorados por dependerem
  de PostgreSQL, sem falhas. Os sete casos científicos `CalculoDiarioTests`
  da Fase 1 foram excluídos, sem repetir a prova científica. O teste de arranque
  com Uvicorn e os testes existentes do contrato legado passaram.
- Cinco artefactos ML validados e previsão técnica com ambos os modelos:
  estado `ok`, resultado meteorológico 0,978, histórico 0,112, ensemble 0,458.
  A verificação não altera nem valida novamente o objetivo científico do ML.
- `pip check` passou. Build de produção com `--no-cache` concluído na imagem
  isolada `viga-fwi-phase4:test`, sem substituir os serviços em execução.
- Versões verificadas: Python 3.11.17, xclim 0.62.0, NumPy 2.4.4, Numba 0.68.0,
  scikit-learn 1.8.0, joblib 1.5.3, XGBoost 3.2.0 e SHAP 0.51.0.
  Requirements, constraints e Dockerfiles permaneceram inalterados.
- `git diff --check` e a verificação dos ficheiros novos passaram.

Esta fase disponibiliza leitura de dados já persistidos; não resolve a ausência
de uma sequência estabelecida, não promove reconstruções convencionais nem
transfere estados entre séries. A tolerância de 60 minutos é uma política
técnica explícita. A publicação no frontend continua por implementar.
Não se fizeram alterações à BD de produção nem se substituíram os contentores
de produção; o contentor de BD usado nos testes foi descartado.
