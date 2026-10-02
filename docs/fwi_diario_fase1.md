**FWI diário — fundação backend, Fase 1**

Implementação adotada: `xclim==0.62.0`, variante clássica validada contra
cffdrs 1.8.17. Identificador persistente:
`xclim-0.62.0-cffdrs-1.8.17-classico-v1`.
Não equivale ao cffdrs 1.9.2; a diferença de constante FFMC e os resultados
comparativos continuam em `experiments/xclim_062/RELATORIO.md`.

**Limites desta fase**

O novo serviço não é chamado por endpoints, alertas ou scheduler. O módulo
`services.fwi` mantém os imports públicos existentes através de `fwi_legado`,
cujo conteúdo é o serviço anterior sem alterações. Não se recalculam dados
antigos, não se altera o ML e não se publicam novos valores FWI.
O import da interface diária não carrega xclim: a importação ocorre apenas
quando se solicita explicitamente um cálculo diário.

**API interna**

```python
from services.meteorologia_fwi import (
    AmostraHorariaFWI, TerritorioFWI, UNIDADES_FWI,
    preparar_observacao_diaria,
)
from services.fwi import EstadoFWI, QualidadeEstado, calcular_fwi_diario
from services.persistencia_fwi import (
    preparar_tabela_fwi, guardar_resultado_fwi, restaurar_estado,
)

# amostras: dados horários efetivos, com fuso explícito e unidades confirmadas.
observacao = preparar_observacao_diaria(
    id_regiao=id_regiao, data_referencia=data, territorio=TerritorioFWI.CONTINENTE,
    latitude=latitude, amostras=amostras, unidades=UNIDADES_FWI,
    origem=identificacao_da_fonte,
)
# anterior deve ser fornecido explicitamente, ou restaurado da BD.
resultado = calcular_fwi_diario(observacao, anterior)
with db.begin():
    registo = guardar_resultado_fwi(db, resultado)
estado_para_o_dia_seguinte = restaurar_estado(registo)
```

`EstadoFWI` exige região, data do dia anterior, FFMC/DMC/DC finitos, qualidade
e origem. A versão é verificada e a referência persistente `id_fwi` é opcional
para permitir um estado inicial externo, explicitamente identificado.
Regiões ou versões diferentes e intervalos superiores a um dia são rejeitados.

`ResultadoFWI` fornece FFMC, DMC, DC, ISI, BUI e FWI em precisão completa,
observação, snapshot anterior, versão e timestamp de cálculo UTC. Não existem
arredondamentos nem classes de risco nesta interface. `proximo_estado()` permite
continuidade em memória; `restaurar_estado()` recupera os valores persistidos.

Faltas, NaN, infinito, humidade fora de 0–100, vento/chuva negativos, FFMC fora
de 0–101, latitude fora de -90–90 e unidades incompatíveis provocam
`DadosFWIInvalidos`. O adaptador também rejeita outputs não finitos. Não se
substituem valores ausentes por zeros e não se reinicializa silenciosamente.

**Meteorologia e tempo**

`ObservacaoDiariaFWI` identifica região, data, território, instante UTC,
latitude, origem e unidades. São necessários temperatura em °C, humidade em %,
vento a 10 m em km/h e precipitação acumulada nas 24 h anteriores em mm.
`UNIDADES_FWI` é uma declaração explícita, não uma conversão automática.
Qualquer futura fonte deve verificar as unidades reais antes de a utilizar.

Continente e Madeira usam 12:00 UTC; Açores usam 13:00 UTC, durante todo o ano.
São as referências de meio-dia em hora padrão. No verão não correspondem a
12:00 da hora civil. Não se determina o território por uma região fixa nem
apenas pela longitude: o chamador tem de o fornecer explicitamente.

Cada `AmostraHorariaFWI` representa chuva na hora terminada no seu instante.
Para referência t, exige-se exatamente a sequência t−23h, ..., t, cobrindo
(t−24h, t]. Exclui-se a amostra terminada em t−24h. Horas duplicadas,
desalinhadas, em falta ou com precipitação inválida impedem a preparação.
Temperatura, humidade e vento são os da amostra em t. Os restantes valores
instantâneos das horas anteriores não são necessários para este cálculo.

Não há chamadas à Open-Meteo nesta fase. `current.precipitation` não é aceite
como substituto implícito da soma horária. O adaptador representa o total de
24 h dividido por um dia em `mm/day`, conforme a API pública xclim; o valor
numérico permanece igual. Datas são gregorianas e os timestamps têm fuso
explícito, normalizado para UTC antes da chamada científica.

**Estado inicial e validade**

| Qualidade fornecida | Validade dos resultados |
|---|---|
| `estabelecido` | `valido` |
| `reconstrucao_historica` | `em_inicializacao` |
| `inicializacao_convencional` | `em_inicializacao` |
| `em_inicializacao` | `em_inicializacao` |

Não existe política de início de época, período de estabilização, overwintering
ou promoção automática. A reconstrução é conservadoramente sinalizada como
inicialização até existir uma política científica explícita numa fase posterior.
Mesmo após muitos dias o serviço não declara essa sequência estabelecida por
iniciativa própria. A ausência de estado anterior é um erro explícito.
Os valores 85/6/15 aparecem apenas nos testes de referência.

Configuração fixa: `initial_start_up=False`, `season_method=None`,
`overwintering=False`, `dry_start=None`. Não foram alteradas constantes xclim.

**Persistência**

A tabela nova `fwi_diario` é independente de `dados_meteorologicos`:

| Grupo | Colunas |
|---|---|
| Identidade | `id_fwi`, `id_regiao`, `data_referencia`, `versao` |
| Referência | `instante_referencia_utc`, `territorio`, `latitude` |
| Inputs | `temperatura`, `humidade`, `vento`, `precipitacao_24h`, `unidades`, `origem_dados` |
| Outputs | `ffmc`, `dmc`, `dc`, `isi`, `bui`, `fwi` |
| Continuidade | `id_anterior`, `estado_anterior` JSON, `origem_estado` |
| Validade | `estado`, `qualidade_estado` |
| Auditoria | `assinatura`, `calculado_em`, `criado_em` |

Os timestamps PostgreSQL são `TIMESTAMP WITH TIME ZONE` e os valores numéricos
são Float de dupla precisão. A combinação região/data/versão tem restrição
única. Há chaves estrangeiras para a região e o registo anterior e restrições
de domínio/consistência da validade. O snapshot conserva também um estado
externo inicial quando ainda não existe `id_anterior` na BD.

A assinatura SHA-256 identifica inputs normalizados, estado anterior e versão.
Repetir o mesmo cálculo devolve o registo existente. Inputs, estado ou outputs
diferentes para a mesma chave provocam erro; não se sobrescreve histórico nem
se invalida silenciosamente uma sequência descendente. O índice único protege
também concorrência. O chamador controla commit/rollback; o serviço usa um
savepoint para tratar exclusivamente a tentativa de inserção duplicada.

A tabela **não é criada automaticamente no startup nesta fase**. Preparação
explícita, para a BD de destino escolhida numa futura ativação:

```python
from config.database import engine
from services.persistencia_fwi import preparar_tabela_fwi
preparar_tabela_fwi(engine)
```

Este comando cria somente a tabela nova e é repetível; exige que `regioes` já
exista. Não foi executado contra produção. Os testes usam BD descartável.
Não se importou o novo modelo em `models/__init__.py`, evitando registá-lo
no `create_all` do arranque atual por efeito indireto dos endpoints.

**Dependências e execução dos testes**

`backend/requirements.txt` inclui xclim 0.62.0 e referencia `constraints.txt`,
cópia das versões resolvidas na prova. Os Dockerfiles backend copiam esse
ficheiro antes da instalação; CMD e número de workers permanecem iguais.
Não há atualização silenciosa de NumPy, Numba, sklearn ou joblib.

```text
cd backend
python -m pip check
python -m unittest discover -s tests -v
python -m services.artefactos_ml
```

Os testes científicos usam a cópia exata do CSV da prova, com proveniência em
`backend/tests/fixtures/README_FWI.md`, e as tolerâncias originais
`atol=1e-8`, `rtol=1e-10`. Testam-se seis índices, sequência de 48 dias, zeros,
chuva forte, limites de humidade, inputs inválidos, unidades, território,
ano bissexto, mudanças de hora, qualidade inicial, continuidade persistida,
idempotência, conflito de inputs e rollback.

Para testes de persistência em PostgreSQL, a variável exclusiva de testes
`VIGA_FWI_TEST_DATABASE_URL` deve apontar para uma BD descartável cujo nome
comece por `viga_fwi_test_`. Estes testes criam/removem as suas tabelas e não
devem ser executados numa BD com dados existentes. O teste concorrente usa
duas transações reais em PostgreSQL; é omitido em SQLite.

**Textos e interface**

Não existem novos textos na interface nem alterações às mensagens públicas
dos endpoints. Foram acrescentadas mensagens PT-PT de validação interna
nos serviços diários, usadas como exceções; não estão expostas por uma rota.
Os novos documentos e comentários são técnicos. Os textos legados foram
preservados sem alterações.

**Validação executada nesta implementação**

- Build limpo, sem cache, do Dockerfile oficial de produção: imagem de teste
  `viga-fwi-phase1:test`, sem substituir os contentores em execução.
- `pip check`: sem incompatibilidades. Todas as versões presentes em
  `constraints.txt` coincidiram com as instaladas, verificadas automaticamente.
- Python efetivo: **3.11.17**, porque o tag existente `python:3.11-slim` avançou
  desde a prova com 3.11.16. Esta é a diferença de ambiente identificada.
  O tag base não foi alterado nesta tarefa. Os testes abaixo foram executados
  no build com 3.11.17, não apenas na imagem antiga da prova.
- Versões: xclim 0.62.0; NumPy 2.4.4; Numba 0.68.0; llvmlite 0.50.0;
  scikit-learn 1.8.0; joblib 1.5.3; XGBoost 3.2.0; SHAP 0.51.0;
  SciPy 1.17.1; pandas 3.0.6; xarray 2026.9.0.
- Suíte backend completa: **98 testes, sem falhas, 6 omitidos**. As omissões
  foram cinco testes NASA específicos de PostgreSQL/PostGIS já existentes e
  o novo teste de concorrência PostgreSQL, não aplicáveis à execução SQLite.
- Nova suíte diária com PostgreSQL/PostGIS descartável: **13 testes passaram**,
  sem omissões, incluindo o teste de concorrência omitido na execução SQLite.
  A BD descartável foi encerrada no final.
- Os 48 dias e os seis índices passaram com a mesma referência e tolerâncias
  da prova. Nenhuma divergência científica nova foi identificada nos casos
  testados. A diferença conhecida em relação a cffdrs 1.9.2 permanece assumida.
- Cinco artefactos ML validados no build e novamente no ambiente construído.
  Previsão técnica: ambos os modelos disponíveis, Kaggle 0,831, ANPC 0,112,
  ensemble 0,400, iguais aos resultados apresentados na prova.
- `git diff --check`: sem erros. O comando cobre ficheiros versionados;
  os ficheiros novos ainda não foram adicionados ao índice Git.
- Os quatro serviços de produção continuaram em execução, com PostGIS
  healthy. Não foi criado esquema FWI na produção, não houve alteração dos
  endpoints e não foi feito commit.

**Ficheiros desta fase**

| Ficheiros | Alteração |
|---|---|
| `backend/requirements.txt`, `backend/constraints.txt` | Dependência xclim e bloqueio do ambiente validado |
| `docker/backend/Dockerfile`, `docker/backend/Dockerfile.prod` | Copiar constraints antes de instalar; comandos de arranque preservados |
| `backend/services/fwi.py`, `backend/services/fwi_legado.py` | Interface diária e compatibilidade exata com o cálculo público anterior |
| `backend/services/fwi_diario.py` | Estados, resultados e adaptador científico diário |
| `backend/services/meteorologia_fwi.py` | Observação normalizada, unidades e janela horária de precipitação |
| `backend/models/fwi_diario.py` | Modelo da tabela aditiva com integridade e chave única |
| `backend/services/persistencia_fwi.py` | Preparação explícita da tabela, gravação idempotente e restauro de estado |
| `backend/tests/test_fwi_diario.py` | 13 testes novos, incluindo persistência e concorrência |
| `backend/tests/fixtures/cffdrs_1_8_17.csv`, `backend/tests/fixtures/README_FWI.md` | Referência preservada e proveniência científica |
| `docs/fwi_diario_fase1.md` | Contrato interno, decisões, limites e resultados de validação |
