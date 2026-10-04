# FWI diário — Fase 3: inicialização e reconstrução histórica

## Âmbito e política

O fluxo é interno e explícito. Não altera o scheduler, `fwi_diario`, as rotas
públicas, o frontend, o ML, a NASA ou a autenticação. Reutiliza o adaptador
xclim 0.62.0 da Fase 1 e a variante clássica validada contra cffdrs 1.8.17.
A divergência conhecida face a cffdrs 1.9.2 mantém-se.

A janela predefinida é de **365 dias antes da data operacional**, configurável
por `janela_dias`/`--janela-dias` ou por uma data inicial explícita. O último
dia reconstruído é o dia anterior à data operacional. A janela é um parâmetro
técnico: **365 dias não constituem um critério científico de estabelecimento**.

A semente FFMC/DMC/DC deve ser fornecida explicitamente, pertencer à mesma
região e corresponder ao dia anterior à data inicial. Não existem valores
numéricos implícitos nem reinicialização automática depois de uma lacuna.

| Estado | Significado |
|---|---|
| `sem_estado` | Não existe uma reconstrução configurada; consulta sem criar registos artificiais. |
| `inicializado_convencionalmente` | Semente convencional registada explicitamente; ainda sem sequência calculada. |
| `em_reconstrucao` | Sequência em processamento, incluindo recálculo após uma correção. |
| `reconstruido` | Janela completa, mas a semente é convencional. Não é operacionalmente estabelecida. |
| `estabelecido` | Janela completa e contínua, partindo de um estado já estabelecido e persistido, verificado na BD. Não implica publicação. |
| `falha_reconstrucao` | Dia pendente bloqueado, com causa e próxima tentativa registadas. |

O estado adicional `reconstruido` distingue a conclusão técnica da validação
operacional. Uma semente convencional **nunca** é promovida a estabelecida,
independentemente da duração da janela. A alternativa estabelecida exige uma
referência `id_fwi` válida em `fwi_diario`, com valores, qualidade, data, região,
versão, latitude e território correspondentes. Essa classificação existente
é uma premissa de confiança, não uma nova prova científica.

Não foi implementada uma política de convergência/estabelecimento científico
para sementes convencionais. Essa decisão exige validação regional adicional.

## Fonte e tempo

É usada exclusivamente a Open-Meteo Archive API, `/v1/archive`, com
`models=ecmwf_ifs`. Não se usa `best_match`, não se adiciona ERA5-Land e não há
fallback silencioso para a Forecast API ou outro produto.

A [documentação da Archive API](https://open-meteo.com/en/docs/historical-weather-api)
indica cobertura global IFS desde 2017 e disponibiliza temperatura a 2 m,
humidade relativa, vento a 10 m e precipitação horários. A precipitação é a
soma da hora precedente. São dados de um produto meteorológico em grelha,
não observações garantidas de uma estação na região.

O cliente pede °C, %, km/h, mm e GMT/UTC; valida as unidades da resposta.
Pede os dias civis que contêm a janela e seleciona exatamente as 24 horas
`t-23h ... t`, representando a precipitação em `(t-24h, t]`.
Temperatura, humidade e vento são os valores em `t`:

- Continente/Madeira: 12:00 UTC.
- Açores: 13:00 UTC.

O horário de verão não altera estas referências. O primeiro dia FWI permitido
é 2017-01-02, pois são necessários inputs do dia anterior. A API pode não ter
um dia recente disponível: isso bloqueia a sequência, sem inventar dados.

## Persistência e proveniência

São acrescentadas duas tabelas através de `preparar_estrutura_historica`:

- `fwi_reconstrucao`: região/versão/revisão únicas; configuração, janela, semente,
  produto, endpoint, modelo, unidades, coordenadas, progresso, tentativas,
  causa, timestamps e auditoria de correções.
- `fwi_historico_dia`: dia único por reconstrução; ligação ao dia anterior,
  snapshot do estado anterior, observação diária com unidades/instante,
  snapshot das 24 horas com ingestão e coordenadas da grelha, seis índices,
  assinatura, validade e timestamp de cálculo.

As horas usam também `fwi_horario`, com o produto distinto
`open-meteo-archive-ecmwf-ifs-horario-v1`. Não se misturam com as horas Forecast
da Fase 2. As tabelas históricas permitem revisões sem alterar as restrições
ou o histórico de `fwi_diario`; o scheduler atual não as consome.

Estas tabelas são preparadas quando o comando interno é executado, de forma
aditiva e idempotente. Nenhuma migração foi aplicada à BD de produção durante
esta implementação.

## Fluxo e recuperação

1. Configurar região, janela e semente explícitas (`iniciar_reconstrucao`).
2. Adquirir o mesmo bloqueio transacional PostgreSQL por região usado na Fase 2.
3. Verificar alterações nas horas já utilizadas pela revisão ativa.
4. Obter a primeira data pendente e o estado do dia imediatamente anterior.
5. Usar as horas persistidas ou consultar a Archive API.
6. Validar os 24 intervalos e calcular com o adaptador existente.
7. Persistir o dia e avançar o cursor na mesma transação.

Cada chamada processa três dias por predefinição; o limite pode variar entre
1 e 366. Não existe um ciclo ilimitado nem um novo job. O operador invoca
`continuar` até concluir; um reinício não perde o cursor.

Uma lacuna, unidade incorreta, valor nulo/NaN/infinito, erro HTTP ou timeout
interrompe a região. O dia fica pendente. As novas tentativas respeitam um
intervalo crescente de 15 minutos até seis horas. Não se continua com um
estado de vários dias antes. Os zeros reais permanecem válidos.

Uma falha de cálculo reverte as escritas desse dia, preservando os dias já
confirmados e registando a causa. Se o próprio commit falhar, o erro propaga-se
e não se anuncia avanço; a BD pode impedir também a persistência da causa.

## Correções e idempotência

`corrigir_dia_historico` consulta explicitamente um dia novamente e exige um
motivo. Só aceita uma janela completa e válida. Se os inputs forem iguais,
não cria revisão nem altera resultados; a alteração apenas do timestamp de
ingestão não é considerada alteração meteorológica.

Se os inputs mudarem, numa única transação:

1. Atualiza as horas do produto histórico.
2. Marca os resultados desse dia e seguintes como `desatualizado`, incluindo
   revisões anteriores da região/versão.
3. Preserva todos os índices e snapshots antigos.
4. Cria uma revisão nova com motivo, inputs anteriores/novos e ligação à revisão
   substituída. O recálculo recomeça na data inicial, usando as horas em cache.

Recalcular a janela completa é uma escolha simples e conservadora desta fase.
Os dias anteriores à correção reproduzem os mesmos valores; os posteriores
usam os novos estados. Os registos de revisões diferentes são histórico de
auditoria, não duplicados da mesma revisão. Apenas a revisão mais recente é
considerada ativa.

`continuar` também compara os snapshots com as horas persistidas e deteta
alterações externas antes de retomar, mesmo numa sequência já concluída.
Escritas diretas na BD não são uma interface suportada; devem usar o comando
de correção para garantir invalidação imediata e o bloqueio partilhado.
Não são procuradas automaticamente revisões remotas da fonte.

## Comando interno

Executar na pasta `backend`, com a configuração de BD do ambiente pretendido:

```powershell
python -m services.reconstruir_fwi --ajuda
python -m services.reconstruir_fwi estado --regiao <ID_EXISTENTE>
python -m services.reconstruir_fwi iniciar --regiao <ID_EXISTENTE> --data-operacional 2026-10-01 --janela-dias 365 --ffmc 85 --dmc 6 --dc 15 --origem-estado "Semente convencional explícita para ensaio; não estabelecida"
python -m services.reconstruir_fwi continuar --regiao <ID_EXISTENTE> --limite-dias 3
python -m services.reconstruir_fwi corrigir --regiao <ID_EXISTENTE> --data 2026-02-15 --motivo "Revisão dos inputs históricos da fonte"
```

Os números do exemplo de semente são uma escolha convencional explícita para
ensaio, não valores automaticamente aplicados nem uma recomendação universal.
Em alternativa, `iniciar --estado-persistido <ID_FWI>` recebe um estado já
estabelecido. As coordenadas e o território são resolvidos a partir da região
existente na BD. Uma configuração incompatível não substitui a anterior.

O comando devolve JSON com estado, revisão, data pendente, causa e próxima
tentativa. Falha, ausência de estado ou região ocupada resultam em código de
saída 1; o estado devolvido distingue cada situação. Erros de argumentos usam 2.
Consultar `inicializado_convencionalmente` ou `reconstruido` não significa que
existe FWI operacional publicado.

## Validação

Os testes de `backend/tests/test_fwi_fase3.py` usam APIs simuladas e verificam:
365 dias, continuidade, lacunas/retoma, zeros, bissexto, mudança de ano,
Continente/Madeira/Açores, idempotência, alterações persistidas, correções
sucessivas, preservação de revisões, concorrência e rollback de cálculo,
correção e commit. Não repetem os casos científicos da Fase 1.

Foi feita adicionalmente uma consulta de leitura à Archive API para confirmar
o contrato IFS: resposta com 48 horas, offset UTC zero e unidades esperadas.
Não se executou uma reconstrução real de 365 dias nem se modificou a produção.

Resultados da validação integrada:

- 21 testes novos passaram em PostgreSQL/PostGIS descartável, sem exclusões,
  também na imagem nova de produção.
- Regressão backend: 131 testes considerados, oito ignorados por dependerem de
  PostgreSQL, sem falhas. A concorrência histórica passou separadamente na BD
  descartável. Os sete casos científicos `CalculoDiarioTests` da Fase 1 foram
  excluídos conforme a instrução de não repetir a prova anterior.
- O comando `iniciar` foi executado duas vezes e comparado com `estado` numa
  região da BD descartável: mesma revisão e mesmos dados, sem duplicação.
- Cinco artefactos ML validados e previsão técnica com ambos os modelos:
  estado `ok`, resultado meteorológico 0,978, histórico 0,112, ensemble 0,458.
  Estes valores são apenas evidência de funcionamento técnico do ML existente.
- `pip check` passou. Build com `--no-cache` concluído na imagem isolada
  `viga-fwi-phase3:test`; nenhum serviço de produção foi substituído.
- Python 3.11.17, xclim 0.62.0, NumPy 2.4.4, Numba 0.68.0, scikit-learn 1.8.0,
  joblib 1.5.3, XGBoost 3.2.0 e SHAP 0.51.0 verificados na imagem.
  Requirements/constraints não foram alterados. O build resolveu dependências
  não fixadas, incluindo SQLAlchemy 2.1.1 e FastAPI 0.142.2; os testes passaram
  também com estas versões.
- `git diff --check` e a verificação de espaços nos ficheiros novos passaram.

A primeira execução da regressão apenas dentro da imagem não tinha acesso ao
Dockerfile esperado pelo teste de arranque. Foi repetida com o repositório
montado em leitura, sem alterar o teste ou o código para contornar a falha.

## Limitações e textos

- Não existe promoção de um estado convencional por duração da janela.
- Não foi ligada a reconstrução ao scheduler nem à publicação operacional.
- A fonte IFS pode sofrer revisões e mudanças de modelo. Os snapshots registam
  os valores efetivamente utilizados; a versão exata do motor IFS não é
  fornecida por este contrato da API.
- A concorrência de produção exige PostgreSQL. SQLite serve os testes sequenciais.
- O recálculo integral e os snapshots horários por revisão têm custo de CPU e
  armazenamento; não é apagado histórico automaticamente.

**Textos públicos criados/alterados: nenhum.** Existem novos textos PT-PT apenas
na ajuda e erros do comando interno, nas causas persistidas, no logging e nesta
documentação. Frontend e respostas dos endpoints públicos permanecem intactos.
