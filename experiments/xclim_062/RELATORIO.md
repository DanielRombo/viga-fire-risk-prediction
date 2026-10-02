**Prova técnica isolada do xclim 0.62.0 — conclusão em 02/10/2026**

O xclim é compatível com o ambiente Python 3.11 testado e reproduz a variante clássica do Canadian FWI implementada pelo cffdrs 1.8.17. Não reproduz exatamente a variante cffdrs 1.9.2. Recomenda-se o xclim 0.62.0 para uma futura integração explicitamente baseada na variante clássica, mantendo esta distinção científica documentada. Não foi feita qualquer integração.

Nesta retoma foram apenas consolidados os resultados existentes e consultados o estado do Docker e do Git. Não foram repetidos os testes aprovados. Os resultados completos encontram-se em [prova.json](resultados/prova.json); cada comparação diária inclui inputs, outputs e diferenças absolutas e relativas nos CSV de `resultados/`.

**A. Compatibilidade**

Instalação isolada bem-sucedida, primeiro sobre uma imagem de teste existente e depois num build de raiz com `--no-cache`, baseado em `python:3.11.16-slim`. As dependências anteriores foram usadas como constraints. Nenhuma versão existente foi alterada pela instalação do xclim e `pip check` passou. Não foram observados conflitos binários nos imports, cálculos, inferência, SHAP ou servidor HTTP exercitados.

Esta conclusão aplica-se ao ambiente bloqueado da prova. O contentor de produção atualmente em execução tem versões diferentes das exigidas pelo repositório: entre outras, NumPy 2.4.6, scikit-learn 1.9.1 e joblib 1.6.0. Não foi atualizado nem usado como alvo de instalação. Não se afirma que foi validada a instalação de xclim nesse ambiente divergente.

**B. Versões exatas**

| Componente | Versão da prova |
|---|---|
| Python | 3.11.16 |
| xclim | 0.62.0 |
| NumPy | 2.4.4 |
| Numba / llvmlite | 0.68.0 / 0.50.0 |
| scikit-learn | 1.8.0 |
| joblib | 1.5.3 |
| XGBoost | 3.2.0 |
| SHAP | 0.51.0 |
| SciPy / pandas | 1.17.1 / 3.0.6 |
| R, exclusivamente para referência | 4.5.3 |

As listas completas encontram-se em [baseline.lock](baseline.lock) e [xclim.lock](xclim.lock). São snapshots das versões resolvidas, não locks de hashes de todas as wheels. Não substituem `backend/requirements.txt`.

**C. Dependências novas**

Foram acrescentados o xclim e 20 pacotes, sem alterações aos anteriores:

```text
xclim==0.62.0
boltons==26.2.0
Bottleneck==1.6.0
cf_xarray==0.11.3
cftime==1.6.6
dask==2026.8.0
filelock==4.0.9
flexcache==0.3
flexparser==0.4
fsspec==2026.9.0
importlib_metadata==9.0.1
locket==1.0.0
partd==1.4.2
Pint==0.25.3
platformdirs==4.12.2
pyarrow==25.0.1
PyYAML==6.0.3
toolz==1.1.0
xarray==2026.9.0
yamale==6.1.0
zipp==4.1.0
```

Evidência: [dependencias.json](resultados/dependencias.json). O crescimento medido de `site-packages` foi de **219 510 747 bytes, aproximadamente 209,34 MiB**, de 1 402 195 538 para 1 621 706 285 bytes. A medição inclui os ficheiros instalados; não é uma medição de RAM nem de espaço exclusivo em camadas Docker.

**D. Conflitos e avisos**

Não houve conflito do resolvedor. Foram observados avisos sobre suporte opcional de matplotlib ausente e sobre inputs sem nomes de features nos scalers, estes últimos também existentes antes de instalar xclim. Os testes de inferência e SHAP passaram apesar desses avisos. A introdução intencional de NaN na meteorologia produziu avisos numéricos e propagação de indisponibilidade, não um valor válido.

Uma experiência de conversão de precipitação de `kg m-2 s-1`, sem metadados/contexto hidrológico, foi rejeitada por `DimensionalityError`. Não foi escondida com uma conversão automática: o teste final usa a conversão dimensional explícita entre `mm/day` e `mm/s`.

**E. Comparação científica**

Foi utilizada exclusivamente a API pública `xclim.indices.fire.cffwis_indices`. A heurística `backend/services/fwi.py` não é utilizada pela prova.

Configuração: float64; FFMC inicial 85, DMC inicial 6, DC inicial 15; `initial_start_up=False`; `season_method=None`; `overwintering=False`; `dry_start=None`. Estes estados são condições iniciais do caso de referência, não uma proposta de inicialização operacional universal para Portugal.

Inputs: 48 dias consecutivos, de 13/04/1985 a 30/05/1985, do conjunto oficial `test_fwi`, latitude original 40° N. Incluem períodos secos, chuva e mudança de mês. Os mesmos inputs foram também exercitados nas latitudes do Continente, Madeira e Açores. Não são observações meteorológicas portuguesas reais.

O código R oficial foi descarregado e executado sem alterar as suas equações, em contentor separado. Versões fixadas:

- cffdrs 1.8.17: commit `9481404cad25387292c1d8692bdb126bbe514d9c`;
- cffdrs 1.9.2: commit `4364ce8f491dfbe18fb22542104644c1c498ddab`.

URLs e SHA-256 dos ficheiros encontram-se em `referencia_1_8_17/origem.json` e `referencia/origem.json`. As cópias R conservam o código original e a identificação da licença GPL-2 em DESCRIPTION. R e estes ficheiros não entram na imagem limpa do backend.

A tolerância foi fixada antes da comparação: `abs(xclim - referência) <= 1e-8 + 1e-10 * abs(referência)`. Não foi aumentada depois de encontrar divergências. As diferenças relativas abaixo são frações, não percentagens; os máximos absoluto e relativo podem ocorrer em dias diferentes.

| Índice | Máxima diferença absoluta, cffdrs 1.8.17 | Máxima diferença relativa | Resultado |
|---|---:|---:|---|
| FFMC | 7,11 × 10⁻¹⁴ | 1,67 × 10⁻¹⁵ | Passou |
| DMC | 4,80 × 10⁻¹⁴ | 4,73 × 10⁻¹⁵ | Passou |
| DC | 4,69 × 10⁻¹³ | 4,59 × 10⁻¹⁵ | Passou |
| ISI | 4,09 × 10⁻¹⁴ | 1,33 × 10⁻¹³ | Passou |
| BUI | 4,97 × 10⁻¹⁴ | 3,83 × 10⁻¹⁵ | Passou |
| FWI | 4,62 × 10⁻¹⁴ | 1,13 × 10⁻¹³ | Passou |

Exemplo do primeiro dia: 17 °C, humidade 42%, vento 25 km/h, precipitação anterior de 24 h igual a 0 mm, latitude 40° N, data 13/04/1985, estados iniciais indicados acima.

| Índice | xclim | cffdrs 1.8.17 | Diferença absoluta | Diferença relativa |
|---|---:|---:|---:|---:|
| FFMC | 87,69298009277445 | 87,69298009277440 | 4,26 × 10⁻¹⁴ | 4,86 × 10⁻¹⁶ |
| DMC | 8,545051136 | 8,545051136 | 0 | 0 |
| DC | 19,014 | 19,014 | 0 | 0 |
| ISI | 10,85366107365507 | 10,85366107365510 | 3,02 × 10⁻¹⁴ | 2,78 × 10⁻¹⁵ |
| BUI | 8,490426535837184 | 8,490426535837180 | 3,55 × 10⁻¹⁵ | 4,18 × 10⁻¹⁶ |
| FWI | 10,096371392382368 | 10,096371392382400 | 3,20 × 10⁻¹⁴ | 3,17 × 10⁻¹⁵ |

Os valores de referência usados no teste são os calculados em R com precisão completa, não os números arredondados do ficheiro publicado `fwi_01.csv`. Consultar [comparacao_classico.csv](resultados/comparacao_classico.csv) para todas as linhas e inputs.

A comparação com **cffdrs 1.9.2 não passou** para FFMC, ISI e FWI:

| Índice | Máxima diferença absoluta | Máxima diferença relativa |
|---|---:|---:|
| FFMC | 0,1241659018 | 0,142264% |
| ISI | 0,2564271049 | 1,883606% |
| FWI | 0,2432622213 | 1,589605% |

DC, DMC e BUI mantêm as diferenças residuais da tabela anterior. A diferença identificada é de variante: xclim e cffdrs 1.8.17 usam `147.2`, enquanto cffdrs 1.9.2 usa `250 * 59.5 / 101`, aproximadamente `147.2772277`, na conversão de humidade do combustível/FFMC e no cálculo associado ao ISI. Não se trata de simples arredondamento de apresentação.

O resultado negativo continua guardado em [comparacao_calibracao.csv](resultados/comparacao_calibracao.csv) e em `prova.json`. O executável global `prova.py` termina com código 1 porque exige equivalência às duas referências; isto preserva o resultado negativo da 1.9.2 e não contradiz a aprovação explícita da variante 1.8.17. Não se deve interpretar esse código como conflito de instalação nem anunciar equivalência à 1.9.2.

Fontes: [API pública xclim 0.62.0](https://xclim.readthedocs.io/en/v0.62.0/apidoc/xclim.indices.fire.html), [referência cffdrs 1.8.17](https://github.com/cffdrs/cffdrs_r/tree/v1.8.17), [referência cffdrs 1.9.2](https://github.com/cffdrs/cffdrs_r/tree/v1.9.2), [origem do conjunto de calibração](https://search.r-project.org/CRAN/refmans/cffdrs/html/test_fwi.html).

**F. Continuidade, unidades, data e latitude**

O estado do dia N foi serializado em `estado_dia_n.json`: FFMC=87,69298009277445; DMC=8,545051136; DC=19,014. Um novo processo Python leu esse ficheiro e calculou os 47 dias restantes. Todos os seis índices coincidiram exatamente com a execução contínua: diferença máxima **0**. Não foi usada a BD.

No dia N+1: FFMC=86,24764219593841; DMC=10,401859979351913; DC=23,568; ISI=8,83757438490779; BUI=10,355328795767598; FWI=9,280210868135827.

| Grandeza | VIGA/Open-Meteo atual | Interface usada na prova |
|---|---|---|
| Temperatura | °C, `temperature_2m` | `degC`, observação à hora de referência |
| Humidade | %, `relative_humidity_2m` | `%` |
| Vento | km/h por omissão, `wind_speed_10m` | `km/h` |
| Precipitação | mm, campo `current.precipitation` | total dos 24 h anteriores dividido por 1 dia, `mm/day` |
| Latitude | graus decimais | `degrees_north` |

A precipitação atual não representa automaticamente as 24 horas necessárias. Foram testadas conversões explícitas equivalentes: °C para K (+273,15), km/h para m/s (÷3,6), percentagem para fração (÷100) e mm/dia para mm/segundo (÷86400). Os seis outputs são adimensionais. O xclim devolve-os na ordem DC, DMC, FFMC, ISI, BUI, FWI.

Casos geográficos: Continente 38,7223° N, Madeira 32,6669° N e Açores 37,7412° N. A referência clássica passou para todos. Foram testados 28/02–01/03/2024, 30/03–01/04/2024 e 26–28/10/2024, incluindo dia bissexto e ambas as mudanças de hora.

Foi fornecido o meio-dia em hora padrão: 12:00 UTC no Continente/Madeira e 13:00 UTC nos Açores, mantendo intervalos exatos de 24 h. No verão isso corresponde a 13:00 da hora civil. O xclim recebe as datas preparadas; não escolhe por si a observação horária nem valida que a chuva corresponde à janela correta. Essa responsabilidade terá de ficar no futuro adaptador meteorológico. Não foi integrada nem consultada Open-Meteo nesta prova.

**G. Desempenho medido**

Ambiente: Docker Desktop, Linux/WSL2 x86-64, AMD Ryzen 5 8500G, 12 CPUs lógicas visíveis. Estes resultados não são medições do Dell Wyse.

| Medição | Resultado |
|---|---:|
| Importação de xclim em processo novo | 2,967 s |
| Primeira comparação de 48 dias, incluindo preparação e escrita do CSV | 0,541 s |
| 1 região × 365 dias, mediana de 5 execuções após aquecimento | 0,02025 s |
| 28 regiões × 365 dias, mediana de 5 execuções após aquecimento | 0,02010 s |
| RSS antes de importar | 12,25 MiB |
| RSS após importar xclim | 309,61 MiB |
| RSS após cálculos, antes do teste ML no processo principal | 331,61 MiB |

Os tempos de cálculo incluem a chamada pública e a verificação de outputs finitos, mas excluem a construção prévia dos arrays. Foram usadas séries sintéticas constantes; não houve rede nem BD. As cinco medições individuais estão no JSON. Tempos semelhantes para 1 e 28 regiões não demonstram escalabilidade ilimitada: este volume é pequeno e o custo fixo da chamada tem peso significativo.

RSS foi lida de `/proc/self/status`; não inclui o processo filho de retoma nem representa o consumo total de toda a aplicação. Não foi isolado um valor de pico durante compilação JIT, medido consumo elétrico, nem feito ensaio de estabilidade 24/7. As medições de memória são do processo científico, não o acréscimo exato a somar à RAM de um backend que já importou bibliotecas comuns.

**H. Docker e produção**

O build experimental de raiz terminou com sucesso e validou os cinco artefactos durante o build. A imagem `viga-xclim-clean:0.62.0` foi apresentada por `docker images` com **2,62 GB**. O comando `docker image inspect` reportou os seguintes valores no campo `.Size`, uma contabilização distinta da apresentada pela listagem desta instalação Docker:

| Imagem | `.Size`, bytes |
|---|---:|
| viga-backend-ml-test:latest | 744 518 666 |
| viga-xclim-proof:0.62.0 | 813 104 601 |
| viga-xclim-clean:0.62.0 | 813 012 006 |

Na construção incremental, a diferença desse campo foi 68 585 935 bytes, aproximadamente 65,41 MiB. Não deve ser confundida com os 209,34 MiB adicionais medidos em `site-packages`, nem tomada como espaço físico exclusivo ocupado no disco. As camadas são partilhadas.

Identificador da imagem limpa: `sha256:bb1ab15abd86a42807accbecd610e80914cf5e191a80e841b3cb7a3e0e89cb9b`. A base Python resolvida foi `sha256:e41613d42d4891e4930f79523f93f81bbc7632584ec65e36ab055f41a800b41e`. O build não depende da imagem local de teste anterior: usa `Dockerfile.clean` e os constraints guardados.

Uvicorn respondeu HTTP 200 com `{"status":"VIGA API online"}`. Este foi um teste HTTP real com imports do backend e xclim, mas **criação de tabelas, preparação da BD, scheduler e recolha foram simulados** para respeitar o âmbito. Não constitui validação integral do arranque com PostgreSQL ou dos endpoints que o utilizam. A imagem contém apenas os cinco `.joblib` necessários; nenhum modelo antigo foi apagado do projeto.

Verificação final de produção, apenas de leitura:

| Contentor | Estado | Início registado, UTC | Reinícios |
|---|---|---|---:|
| viga_backend_prod | Em execução | 30/09/2026 18:18:14 | 0 |
| viga_frontend_prod | Em execução | 30/09/2026 18:30:20 | 0 |
| viga_db_prod | Em execução, healthy | 30/09/2026 18:01:22 | 0 |
| viga_nginx_prod | Em execução | 30/09/2026 17:42:31 | 0 |

As imagens continuam a ser `projeto_final_curso-backend`, `projeto_final_curso-frontend`, `postgis/postgis:15-3.3` e `nginx:alpine`. Não foram substituídas, reiniciadas ou reconfiguradas. Não houve escrita na BD de produção. Os contentores da prova foram executados com `--rm`; as imagens experimentais e a imagem R permanecem disponíveis localmente. Não se executou limpeza global do Docker.

**I. ML existente**

Passaram a validação de checksums e compatibilidade: `modelo_kaggle.joblib`, `scaler_kaggle.joblib`, `modelo_anpc.joblib`, `scaler_anpc.joblib` e `encoder_distrito_anpc.joblib`.

Foram exercitados os dois modelos, ambos os scalers, o encoder para Lisboa e SHAP. Inputs exclusivamente técnicos: 20 °C, 50%, 10 km/h, 0 mm, FFMC/DMC/DC/ISI=85/6/15/5, Lisboa, coordenadas 38,7223/-9,1393, observação 01/07/2024 12:00 UTC. Não representam dados reais nem validam o objetivo científico dos modelos.

As probabilidades sem arredondamento e os valores SHAP foram **exatamente iguais antes e depois** de instalar xclim. O serviço devolveu ambos os modelos disponíveis; valores apresentados pelo serviço: Kaggle 0,831, ANPC 0,112, ensemble 0,400. Passaram os 5 testes de artefactos e os 11 testes de inferência existentes. Logs e JSON encontram-se em `resultados/`.

**J. Riscos e limites**

- A variante deve ficar identificada: equivalência demonstrada com cffdrs 1.8.17 não é equivalência à 1.9.2. Não se propõe alterar constantes internas do xclim para disfarçar essa diferença.
- Falta de temperatura num dia propagou NaN aos seis índices desse dia e do seguinte. Uma integração futura terá de validar os inputs, sinalizar indisponibilidade e recuperar a sequência; não preencher faltas com zeros.
- A seleção da hora padrão e a acumulação real de precipitação de 24 h continuam por implementar no VIGA.
- Não foram validados nesta prova o overwintering, protocolos de início/fim de época, todas as condições extremas, classes de risco nacionais ou adequação ecológica local. A equivalência numérica não certifica a previsão operacional de incêndios.
- Importação e memória são custos relevantes num equipamento pequeno. É necessário medir no Dell Wyse concreto, incluindo ML, PostgreSQL e restantes serviços; não se extrapolaram números para esse equipamento.
- As dependências transitivas foram fixadas na prova. Instalar futuramente apenas `xclim==0.62.0`, sem os constraints, não garante repetir este ambiente.

**K. Recomendação entre xclim e cffdrs_py**

Recomenda-se **xclim 0.62.0**, com as versões resolvidas desta prova, como candidato para a integração futura da **variante clássica validada**. A recomendação assenta na equivalência numérica independente, continuidade exata, compatibilidade ML e build efetivamente executados.

Não se recomenda substituir por `cffdrs_py` com base nesta prova: essa biblioteca não foi instalada, medida nem submetida às mesmas comparações, pelo que não se pode afirmar que resolveria a diferença da 1.9.2 ou que seria melhor neste ambiente. O [repositório oficial cffdrs_py](https://github.com/cffdrs/cffdrs_py) permanece uma alternativa a avaliar se for exigida outra variante ou se o orçamento de recursos do Wyse inviabilizar xclim.

Se o requisito for reproduzir especificamente **cffdrs 1.9.2**, a decisão é **não avançar com xclim 0.62.0 como substituto equivalente**: essa comparação falhou. Será necessário escolher e validar uma implementação dessa variante. Nenhuma integração foi forçada.

**Ficheiros e preservação do âmbito**

Todas as adições pertencem a `experiments/xclim_062/`: Dockerfiles experimentais e filtros de contexto; snapshots de dependências; scripts de obtenção/execução da referência; prova científica, validação ML, testes e arranque isolado; código de referência com proveniência; resultados JSON/CSV/logs/estado; este relatório. Nenhum ficheiro de produção foi alterado. Não houve mudanças na BD, scheduler, API, frontend, modelos ou heurística atual do VIGA.

`git diff --name-only` não apresentou alterações a ficheiros versionados. `git diff --check` terminou sem erros. Este comando não inspeciona o conteúdo de ficheiros ainda não versionados; a pasta experimental encontra-se nesse estado. Não foi feito commit.
