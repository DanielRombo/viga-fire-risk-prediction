# ML 5B — auditoria de viabilidade, 12/10/2026

## Decisão

**Não treinar nem integrar um modelo nesta fase.** O objetivo é viável em princípio,
mas o conjunto local não permite demonstrar o target pedido. Não há sobreposição
entre as ocorrências ANPC locais (2016–06/07/2020) e o histórico FWI validado
(01/10/2021 em diante); não existe um calendário certificado de cobertura de
ocorrências, nem uma definição territorial municipal versionada para os 28 pontos.
Não confundir este bloqueio com inexistência de incêndios.

Auditoria exclusivamente local e de documentação pública: nenhuma ligação à BD,
nenhum container iniciado, nenhum download meteorológico/ocorrências, nenhuma
alteração aos dados originais, modelos, API, frontend, scheduler ou produção.
As contagens de produção abaixo são **fotografias documentadas de 11/10**, não
contagens atuais consultadas nesta tarefa. Os novos ficheiros são apenas auditoria,
sem construção de labels, treino ou substituição de artefactos.

## 1. Inventário e qualidade

`inventario.json` contém campos, faltas por coluna, datas interpretadas, contagens,
distribuições de eventos candidatos, tamanhos e SHA-256 dos ficheiros examinados.
`auditar.py` usa apenas a biblioteca padrão e lê os originais sem os modificar.

| Fonte local | Registos/período | Território e granularidade | Utilidade e limitações |
|---|---|---|---|
| ANPC, cinco CSV | 910 783; 09/01/2016–06/07/2020 | Ocorrências com timestamp sem fuso; candidatos em 18 distritos continentais | ID, natureza, distrito/concelho/freguesia, coordenadas, ocorrência/fecho e meios. Potencial fonte de labels após certificar cobertura, taxonomia, timestamps e duplicados. Sem negativos certificados. |
| ICNF, 36 CSV `incendios1980…2015` | 791 453; 30/01/1980–30/12/2015 nas datas lidas | Registo de incêndio; esquemas variáveis por ano | Localidade, data/hora de início ou alerta, área/causa; coordenadas só em certos esquemas, incluindo sexagesimais. Dados mais antigos sem sobreposição com o produto IFS suportado, que começa em 2017. Área final serve para auditoria, nunca feature futura. |
| Kaggle `forestfires.csv` | 517 | X/Y de grelha, mês/dia da semana; sem data completa nem georreferenciação compatível | FFMC/DMC/DC/ISI/temp/RH/wind/rain/area, sem células vazias. Impossível ligar com segurança aos 28 pontos e a um horizonte de 24 h. `area=0` não certifica ausência de ocorrência. |
| Meteorologia/FWI experimental | Fase 8: 306 768 horas e 12 782 observações diárias, sete pontos, 01/10/2021–30/09/2026 | Horário e diário, UTC, Archive/ECMWF IFS | Campos e unidades explícitos; horas incluem o antecedente necessário à chuva de 24 h. São dados de grelha reconstruídos, não disponibilidade histórica comprovada em T. Outras fases sobrepõem períodos: não somar ficheiros como amostras independentes. |
| FWI na produção, segundo o relatório anterior | 51 408 dias; 1 836 por cada um dos 28 pontos, 01/10/2021–10/10/2026 | Série histórica reconstruída | Seis índices, cadeia, revisão, origem, timestamps. `fwi_diario` operacional estava vazio; valores estão na série reconstruída. Não equivalem a certificação operacional. Não consultado nesta tarefa. |
| Meteorologia atual, fotografia anterior | 3 387 registos na fotografia de fecho | Recolha periódica por ponto | Histórico curto; contagem agregada não prova continuidade nem cobertura dos anos ANPC. Não utilizado como dataset de treino. |
| NASA FIRMS/VIIRS | Serviço de deteções; quantidade atual não consultada | Aquisição satélite por ponto/instante | O modelo `Ocorrencia.data_inicio` guarda aquisição NASA, não ignição. Deteções repetidas do mesmo fogo não são novas ignições. Falta de deteção não significa ausência de fogo. |
| Catálogo | 30 entradas, 28 com recolha automática | Pontos, 26 continentais + Funchal + Ponta Delgada | Nome/distrito/lat/lon, sem polígono municipal. GeoJSON contém 20 distritos/agrupamentos insulares, não os 28 territórios municipais. |
| Modelos antigos | 17 ficheiros joblib nas duas pastas | Cinco artefactos obrigatórios em produção | Manifesto mantém o conjunto oficial. Há cópias byte a byte (ver hashes); não carregados, apagados ou substituídos nesta auditoria. Não constituem dados adicionais. |

Os CSV científicos de referência cffdrs, resultados de ensaios e fixtures são
testes de cálculo, não ocorrências nem amostras independentes para treino.

### ANPC: contagens medidas, sem inferir cobertura

| Ficheiro | Todas as ocorrências | Candidatos com `incendio` no texto normalizado | Candidatos com data interpretável | Coordenadas numericamente válidas nos candidatos |
|---|---:|---:|---:|---:|
| 2016 | 121 187 | 17 227 | 17 227 | 17 179 |
| 2017 | 217 989 | 38 325 | 38 325 | 38 141 |
| 2018 | 234 795 | 33 507 | 33 507 | 33 507 |
| 2019 | 245 285 | 30 960 | 30 960 | 30 960 |
| 2020 | 91 527 | 10 567 | 10 564 | 10 564 |
| Total | 910 783 | 130 586 | 130 583 | 130 351 |

Validade numérica das coordenadas **não valida posição em Portugal/município**.
Há um ID repetido dentro do CSV de 2016; é necessária deduplicação transversal e
investigação de revisões, não apagar automaticamente a segunda linha. Dez datas
ANPC não foram interpretadas pelo auditor (6/1/0/0/3 por ano); zero linhas com
estrutura CSV malformada. Faltas por campo constam do inventário. Datas ICNF são
interpretáveis pelo parser, mas isso não certifica hora, fuso ou instante de ignição.

O filtro textual inclui fogo urbano/transportes/equipamentos, queimas, gestão de
combustível e consolidação de rescaldo. **Não é a seleção final de incêndios rurais.**
`distribuicao_candidatos.csv` documenta contagens por mês e distrito/concelho;
contagens zero de correspondência nominal nas ilhas são ausência de cobertura,
não labels negativos. A soma de eventos não é o número de dias positivos.

**Dataset elegível construído: 0 linhas. Positivos/negativos/prevalência: não
determináveis**, e não 0 incêndios/0% de prevalência. Sobreposição temporal entre
ANPC local e FWI validado: zero dias.

## 2. Target proposto, sujeito à documentação da fonte

Recomenda-se delimitar o objetivo a **novas ocorrências confirmadas de incêndio
rural registadas no município R**, não todos os tipos de socorro nem fogos já em
curso. Se o objetivo for todos os incêndios, a taxonomia deverá incluir explicitamente
urbanos/industriais e o papel do FWI terá de ser reavaliado. Não aplicar esta
restrição silenciosamente: a taxonomia final deve ser aprovada antes de gerar labels.

Para uma emissão T, `y(R,T)=1` se pelo menos uma ocorrência elegível tiver início
registado `T < t <= T+24h` dentro de R. Múltiplas ocorrências dão um único positivo.
Ocorrências anteriores ainda ativas não dão um novo positivo. IDs de revisões,
rescaldos e reacendimentos precisam de regra documentada de evento novo; não
classificar automaticamente cada atendimento como nova ignição.

`y=0` só se a janela completa tiver cobertura territorial/temporal certificada,
latência de notificação já encerrada e nenhuma ocorrência elegível. Fora disso,
`y=null`, com motivo; nunca preencher zeros. A fonte precisa de definir se
`DataOcorrencia` é ignição, alerta ou abertura do registo. Se for alerta, o nome do
target deve ser “nova ocorrência comunicada”, não ignição física.

Proposta de emissão diária: **15:00 UTC** para todos os municípios, janela absoluta
de 24 h. É uma proposta a validar pela latência real, não garantia de que o Archive
já publicou os dados. As referências FWI continuam 12:00 UTC no Continente/Madeira
e 13:00 UTC nos Açores. Se o FWI desse dia não estiver disponível em T, usar somente
o último resultado já disponível, com a respetiva idade, ou declarar indisponibilidade.
Não usar uma observação só porque o seu instante de validade é anterior a T.

Armazenar UTC com fuso, preservando o timestamp original e o fuso documentado da
fonte. Interpretar horas civis confirmadas com Europe/Lisbon, Atlantic/Madeira ou
Atlantic/Azores; horas ambíguas/inexistentes na mudança de hora ficam em quarentena
até haver evidência, sem atribuir arbitrariamente um offset. Nunca assumir que as
datas ANPC sem offset já são UTC.

R deve ser um polígono municipal versionado e código oficial, ligado ao ponto do
catálogo por tabela explícita, não pelo primeiro ID/nome ou pelo distrito inteiro.
Funchal e Ponta Delgada não representam os arquipélagos. Ocorrência exatamente numa
fronteira ou com coordenada/código contraditórios: usar código municipal confirmado
pela fonte; sem resolução, excluir o evento do conjunto certificado e marcar como
desconhecidas as janelas/territórios candidatos, evitando falsos negativos. Não
contar nas duas regiões. Versionar limites e harmonização histórica.

## 3. Features e leakage

Nenhuma feature foi usada para treino nesta tarefa. Candidatas: temperatura °C,
RH %, vento 10 m km/h, chuva passada 24 h mm; seis índices FWI válidos com cadeia
histórica; idade dos inputs; mês/dia do ano cíclicos; município/distrito e coordenadas
do ponto. Hora de emissão fixa não acrescenta informação. Contagens passadas só
incluem ocorrências já notificadas em T, nunca catálogos finais sem latência.

Cada linha precisa de `valid_time`, `available_at/issued_at`, `ingested_at`, fonte,
produto, revisão e checksum. O inventário encontrou horas de 2021 ingeridas em
2026: isso certifica a reconstrução, **não prova que esses valores eram conhecidos
em 2021**. Reanálise/análise revista pode incluir informação posterior. É adequada
a estudo retrospetivo explicitamente limitado; não basta para provar previsão em
tempo real. O histórico FWI reconstruído herda este problema.

Excluir meios mobilizados, área final, causa determinada posteriormente, fecho,
estado final, duração, respostas futuras, meteorologia realizada após T e deteções
NASA posteriores. Não juntar dias pelo calendário civil se o target é uma janela
UTC. Não confundir IDs experimentais de BD descartável (Lisboa ID 1 na Fase 8) com
o ID canónico 3260: ligar por catálogo, coordenadas, produto e proveniência.

## 4. Protocolo futuro, sem executar com dados inválidos

Após os gates de dados, reservar blocos temporais completos, por exemplo treino
2021–2023, validação/calibração 2024 e teste 2025 **apenas se a cobertura suportar
estes anos**. Excluir janelas cujos labels atravessem os cortes; usar validação
rolling-origin dentro do treino. Ajustar imputação, scaler, encoder, seleção,
hiperparâmetros e prevalências apenas no treino. Calibrar num bloco posterior
separado ou mediante previsões out-of-fold temporais; escolher thresholds na
validação e congelar antes de abrir o teste. Sem random split como prova principal.

Avaliar também municípios/distritos retidos, com bloqueios espaciais que reduzam
dependência entre vizinhos. Reportar ilhas separadamente; sem labels insulares,
não extrapolar uma calibração continental. Teste de drift por ano/estação/região.

Baselines planeadas: prevalência do treino; climatologia sazonal com smoothing
ajustado só no treino; regressão logística regularizada; logística só com
meteorologia/FWI. Depois Random Forest ou HistGradientBoosting das dependências
existentes, se houver melhoria. Sem novas dependências pesadas. Seed 42, manifesto,
split e pesos registados. Negativos mantidos na prevalência real no teste; qualquer
subamostragem/pesagem no treino exige corrigir e validar calibração.

Métricas: ROC-AUC, average precision (identificada como tal, sem confundir com área
trapezoidal PR), curva PR, precision/recall/F1/matriz por threshold, Brier e Brier
skill contra prevalência, curva de fiabilidade e inclinação/interceção de calibração.
Intervalos por bootstrap de blocos temporais/espaciais, não linhas independentes.
Sem positivos/negativos num estrato, métrica não definida. Definir custos e critérios
de aceitação antes do teste; não inventar agora um limiar de “boa calibração”.

**Melhor modelo, ROC-AUC, PR-AUC, precision/recall/F1, Brier e calibração: não
calculados**, pois não existe dataset elegível. Não é falha de desempenho medida.

## 5. Comparação com os modelos existentes

Kaggle aprende `area > 0` em 517 registos, não ocorrência num município nas próximas
24 h. ANPC aprende `(NumeroMeiosAereosEnvolvidos > 0) OR
(NumeroMeiosTerrestresEnvolvidos > 5)` dentro de ocorrências selecionadas. Estima uma
classe de mobilização, não presença/ausência futura. O notebook também contém um
ensaio ICNF `area_total > 1`; não confundir esse alvo com o ANPC oficial. A média
ponderada dessas saídas não muda os alvos nem demonstra calibração de ocorrência.
Modelos e nomes de campos existentes ficam integralmente preservados.

## 6. O que obter primeiro

1. Exportação oficial de ocorrências com IDs, natureza/código, timestamps e semântica,
   fuso, concelho/código, coordenadas, revisões, critérios de cobertura e períodos
   de indisponibilidade. Preferir período coincidente com 2021–2026; não presumir
   que 2026 está consolidado. Confirmar cobertura Madeira/Açores separadamente.
2. Evidência de completude e atraso de notificação por município/período. Conciliar
   totais com relatórios oficiais; totais anuais, por si só, não certificam cada dia.
3. Limites municipais CAOP versionados e correspondência explícita para os 28 pontos.
4. Meteorologia de observações ou runs arquivados com disponibilidade comprovada em T.
   O Archive IFS suportado permite investigar 2017–2020 se os labels antigos forem
   certificados, mas descarregar esses anos não resolve cobertura/latência sozinho.
5. Construir e auditar o dataset; só então baselines, calibração e teste temporal.

Referências primárias consultadas em 12/10/2026:

- [Open-Meteo Archive](https://open-meteo.com/en/docs/historical-weather-api): IFS desde 2017; produto histórico não garante disponibilidade em tempo real.
- [Historical Forecast](https://open-meteo.com/en/docs/historical-forecast-api) e [Previous Runs](https://open-meteo.com/en/docs/previous-runs-api): verificar arquivo e emissão por modelo antes de definir o período.
- [NASA FIRMS, limitações de deteção](https://firms2.modaps.eosdis.nasa.gov/alerts/notes.php): nuvens/passagens impedem equiparar ausência de deteção a ausência de fogo.
- [DGT, CAOP](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop): fonte de limites administrativos; fixar versão.
- [ICNF, lista de ocorrências rurais](https://fogos.icnf.pt/localizador/faztableocorrencias.asp?ano=2023&concelho=XXXXXXXXXXXX): ponto de partida para obter eventos; não certifica sozinho cobertura municipal diária ou insular.
- [ANEPC no portal de dados](https://dados.gov.pt/pt/organizations/autoridade-nacional-de-emergencia-e-protecao-civil-1/): solicitar documentação/arquivo completo, não tratar um feed de ocorrências em aberto como histórico exaustivo.

**Recomendação: avançar para aquisição e certificação de dados, não para treino ou
integração. Ainda não é cientificamente defensável chamar a uma nova saída do VIGA
“probabilidade de incêndio nas próximas 24 horas”.**

## 7. Verificações e reprodução

Comandos executados: `python experiments/ml_5b/auditar.py`,
`python -B experiments/ml_5b/verificar.py` e `git diff --check`.
Resultado: 80 ficheiros originais com SHA-256 e tamanho preservados (42 CSV,
17 artefactos e 21 evidências FWI). Contagens mensais e distritais reconciliadas;
28 pontos ativos; 306 768 timestamps horários sem duplicação dentro de cada
ficheiro da Fase 8; 12 782 datas diárias únicas e completas nos sete pontos.
`integridade.json` guarda o resultado. `git diff --check` sem erros.

Ficheiros criados apenas em `experiments/ml_5b/`: `auditar.py`, `verificar.py`,
`inventario.json`, `distribuicao_candidatos.csv`, `integridade.json` e este relatório.
O diretório operacional preexistente ficou intacto. Nenhum commit ou deploy.
