# ML 5B.2 — obtenção e certificação de dados

12/10/2026. **NO-GO para dataset certificado/treino; fonte oficial individual identificada e amostrada com sucesso.** Não é uma conclusão de impossibilidade do modelo: o próximo passo concreto é esclarecer a exportação SGIF com o ICNF e obter o dicionário de dados e cobertura. Não houve treino, recolha meteorológica adicional, alteração de produção, API, frontend, modelos, deploy ou commit.

## 1. Resultado e fonte prioritária

Foi localizado o [diretório público de exportação SGIF do ICNF](https://fogos.icnf.pt/download/ExportarDadosSGIF/). É uma melhoria substancial face aos CSV ANPC locais: disponibiliza `Data2001_now.csv`, `Data2001_noweliminados.csv`, `AdministrativeRelations.csv`, agregados diários e outros produtos. Não é necessário depender de Fogos.pt.

O CSV individual anunciado tem **479 541 125 bytes**. Foram obtidos apenas os primeiros 131 072 bytes e os últimos 65 536, por HTTP Range/206, para inspeção; **não foi descarregado nem certificado integralmente**. O nome do ficheiro não prova o intervalo nem a completude. A listagem indica modificação em 24/03/2026, não data de consolidação científica. A cauda contém 2005 e o início 2022: não inferir min/max cronológicos a partir das extremidades.

| Fonte oficial/candidata | Produto, período e âmbito verificados | Licença/proveniência | Adequação e limitações |
|---|---|---|---|
| ICNF, exportação SGIF acima | Ocorrências individuais; nome sugere 2001–atualidade, extremos globais não auditados; amostra 2022 e cauda 2005 | Domínio oficial; SHA-256 e instante de aquisição guardados. Licença específica dos CSV **não encontrada** | Prioridade para obtenção certificada. Faltam dicionário, fuso, filtros da exportação e cobertura |
| [ANEPC em dados.gov.pt](https://dados.gov.pt/pt/datasets/prociv-ocorrencias-em-aberto/) | Ocorrências em curso oriundas do SADO; Portugal continental. Cobertura temporal não preenchida | Metadados indicam CC BY 4.0 e entidade ANEPC | Feed ativo não é arquivo histórico completo. Ausência no feed não é negativo |
| [AGIF/SGIFR, estatísticas](https://www.sgifr.gov.pt/pt/estatisticas-incendios-rurais) | Dashboard continental com análises desde 2001 | AGIF; utiliza informação ICNF/SGIF. Licença de exportação não confirmada | Útil para reconciliação de totais; não substitui registos e cobertura municipal/hora |
| [ArcGIS ICNF](https://sigservices.icnf.pt/server/rest/services/DFCI) | Catálogo DFCI e Histórico de Áreas Ardidas consultados; este último expõe duas camadas raster, não eventos | Metadados públicos guardados; serviço GIFR devolveu JSON `499 Token Required` | Não contornar autenticação. Áreas ardidas/raster não certificam ausência de ignição nem instante |
| [Geocatálogo ICNF](https://geocatalogo.icnf.pt/catalogo_tema5.html) | Áreas ardidas 1975–2025 e cartografia de risco | Dados geográficos abertos com atribuição, salvo exceção; não extrapolar automaticamente esta licença aos CSV SGIF | Perímetros servem para controlo espacial; não usar área ardida final para selecionar o target |
| [IFCN Madeira](https://ifcn.madeira.gov.pt/pt/florestas/protecao-da-floresta-contra-incendios/geral.html) | Informação de proteção da floresta; arquivo individual completo não localizado | Fonte regional oficial; licença de microdados não identificada | Pedir IFCN/SRPC RAM eventos e cobertura. Funchal continua sem labels certificados |
| [SRPCBA Açores](https://www.prociv.azores.gov.pt/bombeiros/apoio-operacional/?cat=45) | Registo de ocorrências referenciado; não obtida exportação rural histórica com cobertura | Entidade regional oficial; licença de microdados não identificada | Não confundir estatísticas de emergência médica ou incêndios urbanos com rurais; Ponta Delgada pendente |
| [DGT CAOP](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop?language=pt) | Limites oficiais versionados, incluindo versões históricas e ilhas | DGT; conservar metadados/licença do pacote escolhido | Usar a versão correspondente ao período. Nenhum polígono foi descarregado nesta fase bloqueada |

Pesquisa não exaustiva: não encontrar declaração de completude não prova que a base seja incompleta. Prova que ainda não temos a evidência necessária para a certificar. A página principal de estatísticas ICNF apresentou conteúdo dinâmico no leitor web; a aquisição Python desse host falhou por cadeia TLS não reconhecida. Não foi desativada a verificação TLS. Outros domínios oficiais acima foram acessíveis.

## 2. Auditoria efetivamente executada

`fontes_5b2.py` guarda bytes originais, URL final, instante UTC, tipo de conteúdo, HTTP status, Range e SHA-256. Cache existente é verificado, nunca substituído silenciosamente. `auditar_5b2.py` valida os hashes e extrai apenas registos CSV completos do prefixo; a linha final cortada pelo Range é excluída. As amostras não são aleatórias nem representativas do país.

- **99 campos** no CSV individual.
- **121 registos completos** na amostra inicial: 106 `Florestal`, 15 `Agrícola`; todos `ClassificacaoRegisto=Closed`; `EstadoRegisto` vazio.
- Datas observadas nesse prefixo: **03/01/2022 18:45–19/03/2022 22:30**, sem offset. Não constituem cobertura contínua desse período.
- **69 registos completos** na amostra dos eliminados: todos `EstadoRegisto=Duplicated`. Não se generaliza aos restantes eliminados.
- Relações administrativas obtidas integralmente: **4 050 linhas, 278 códigos DTCC distintos**.
- Os 28 pontos de recolha ativos foram filtrados por `recolha_automatica=true`; o JSON contém também Gondomar e Barcelos inativos, que não foram contados.
- **26 pontos ativos** têm correspondência única distrito/concelho → DTCC na tabela SGIF; Funchal/Ponta Delgada não têm correspondência. Isto é reconciliação administrativa candidata, não certificação CAOP nem prova de cobertura das ocorrências.

Campos relevantes: `Codigo`, `CodigoSado`, `Tipo`, `DHInicio`, `INE`, distrito/concelho/freguesia, `Lat_4326`, `Lon_4326`, `Reacendimento_IncendioPai`, `OriginouReacendimento`, `ClassificacaoRegisto`, `EstadoRegisto`. `INE` surge numericamente: repor zeros à esquerda conforme dicionário, nunca tratar como float ou ID VIGA. Usar a relação explícita INE/DTCC, validada quanto à unicidade; não adivinhar sempre o município cortando texto.

As contagens por município/ano/mês de **eventos candidatos na amostra** estão em `auditoria_5b2/contagens_amostra.csv`. Não são contagens do dataset completo nem prevalências. Não emitir percentagens positivas a partir de amostragem por bytes.

## 3. Taxonomia reproduzível proposta: rural_ignicao_v1

Definição pretendida: nova ignição não planeada/não controlada em povoamento, mato ou área agrícola no município de origem. Incêndio que atravessa a fronteira não cria uma nova ignição nesse outro município. Se o objetivo passar a ser município atingido, é outro target, com outra evidência temporal.

1. Naturezas elegíveis: incêndio rural em povoamento, mato ou agrícola; no SGIF amostrado, `Florestal`/`Agrícola` são **candidatos**, a confirmar pelo dicionário. Não inventar códigos numéricos de natureza que não foram publicados.
2. Preservar código e categoria originais, ID e snapshot; adjudicar revisões antes dos labels. Não interpretar `Closed` isoladamente como confirmação de incêndio.
3. Excluir falso alarme/alerta, duplicado, cancelado sem incêndio, prevenção, queima/queimada controlada, gestão de combustível e rescaldo sem nova ignição. Casos desconhecidos ficam em quarentena.
4. Distinguir **natureza do evento** de **causa**: uma queimada que escapou e gerou incêndio rural continua elegível. Não excluir automaticamente causas contendo “queimada”.
5. Não contar reacendimentos como novas ignições neste target; ligar ao pai e conservar a linha. Pai desconhecido/conflicto bloqueia a adjudicação relevante. Confirmar semântica e códigos com ICNF antes da implementação definitiva.
6. Fogacho não é excluído por ser pequeno. Não usar meios, área ardida, duração ou máximos posteriores como filtro do target. Os indicadores de área não servem para inferir que um alarme era falso.

Esta é uma especificação final **pretendida**, não um mapeamento fonte→taxonomia já certificado. Esse mapeamento permanece bloqueado pela falta de dicionário e semântica das classificações. Um [plano SGIFR do Algarve](https://www.sgifr.gov.pt/documents/196633/1535832/PRA_Algarve.pdf) distingue falsos alarmes, fogachos, florestais, agrícolas e reacendimentos; corrobora a necessidade das distinções, não documenta todos os códigos desta exportação.

## 4. Território e dimensão

Unidade recomendada: **código municipal versionado × emissão T em UTC**. Prioridade: código oficial validado; depois ponto de ignição dentro de polígono CAOP na versão/CRS corretos. Nome+distrito é auxílio à reconciliação, não regra final em caso de conflito. Coordenada na fronteira, código incoerente, ponto fora do município e versões administrativas divergentes ficam em quarentena. Área ardida que atravessa concelhos não altera o município da ignição.

`auditoria_5b2/municipios_catalogo.json` contém os 28 pontos, coordenadas e candidatos. Exemplos: Lisboa 1106, Vila Real 1714, Faro 0805, Porto 1312. Estes são códigos municipais, **não** IDs da BD VIGA. Não houve consulta nem escrita na BD.

| Alternativa | Vantagem | Limitação científica/computacional |
|---|---|---|
| A: municípios dos 28 pontos | Reutiliza infraestrutura e validações meteorológicas; começar pelos 26 continentais com código reconciliado | Amostra sobretudo urbana, poucos incêndios nalguns municípios, cobertura espacial enviesada. Ponto meteorológico urbano não representa todo o município. Ilhas exigem fonte própria |
| B: municípios continentais com cobertura certificada, até 278 candidatos | Mais diversidade rural e melhor avaliação espacial | Mais meteorologia, heterogeneidade intra-municipal; escolher pontos/ponderação antes do treino, sem os escolher em função dos incêndios futuros |

Não há ainda **nenhum município certificado para treino**. Os 278 são universo administrativo candidato, não 278 coberturas aprovadas. A expansão às ilhas não é inferida deste universo.

Cenário de planeamento **2018–2024**, não período certificado: 2 557 dias por município. São 66 482 linhas/1 595 568 horas para 26 municípios; 71 596/1 718 304 para 28; 710 846/17 060 304 para 278. Acrescentar warm-up, chuva antecedente e o dia final de labels. São contas aritméticas, não benchmark ou autorização de recolha total.

## 5. Período útil e timestamps

O maior período certificado **não pode ainda ser determinado**. O SGIF indica histórico muito mais longo que o ANPC local, mas o CSV integral e a sua consolidação não foram auditados. Não limitar a investigação a 2016–2020. Prioridade futura: anos completos consolidados recentes, potencialmente 2018–2024, a confirmar com fornecedor; excluir 2026 parcial por defeito.

[Open-Meteo Archive](https://open-meteo.com/en/docs/historical-weather-api) documenta IFS desde 2017, portanto 2016 não é suportado pelo mesmo produto escolhido. Não trocar silenciosamente para ERA5. A inicialização FWI no início do período exige histórico anterior disponível e avaliação de sensibilidade; não declarar 365 dias automaticamente suficientes.

`DHInicio` não inclui offset na amostra. O nome não prova ignição versus alerta/registo. Se representar alerta, a designação correta será ocorrência **reportada** nas próximas 24h, não instante físico exato da ignição. Exigir definição e fuso, regras DST e tratamento de horas ambíguas/inexistentes. Sem isso, não adjudicar eventos próximos da fronteira T. Horizonte em tempo absoluto `(T,T+24h]`, não “dia civil seguinte”.

## 6. Regra de labels e negativos

Implementado contrato experimental em `labels_5b2.py`, **não ligado ao VIGA**:

- `y=1`: pelo menos um evento já confirmado, temporal e territorialmente resolvido, em `(T,T+24h]`. Não precisa de completude de toda a janela para provar existência.
- `y=0`: nenhum evento elegível **e** cobertura documentada do município e horizonte inteiro; extração integral verificada, snapshot/hash, taxonomia e timestamps validados, consolidação terminada, sem casos potencialmente positivos em quarentena.
- `null`: falta qualquer evidência necessária ao negativo. Não imputar zero.

Os campos de evidência do contrato são precondições, não um certificador automático. Os testes usam evidência **simulada**, não aprovam cobertura SGIF. Na ingestão real, cada indicador terá de apontar para documento/manifesto revisto e contagens conciliadas.

Para certificar cobertura: declaração/documentação do universo abrangido, filtros e exclusões; janela territorial/temporal e interrupções conhecidas; snapshot completo (tamanho/hash/paginação/IDs); revisões/duplicados resolvidos; contagens reconciliadas com totais oficiais compatíveis com a taxonomia; latência de consolidação. Totais coincidentes são controlo necessário, não prova isolada de completude diária. Ausência de dias nacionais vazios também não basta. Cobertura diz respeito a incêndios **registados no sistema**; nunca prova que todos os pequenos incêndios não reportados foram observados.

**Contagens certificadas novas:** 0 labels positivos emitidos, 0 negativos, 0 linhas de dataset novas; prevalência indisponível. Não são zeros de incidência. Não foram construídas linhas municipais vazias para inflacionar a contagem de null. As 60 linhas da prova 5B.1 continuam com `y_certificado=null` (13 janelas com candidatos não certificados e 47 sem candidatos); nenhuma foi convertida nesta fase.

Não é possível quantificar positividade/negatividade certificada por ano/mês/município enquanto o denominador coberto não existir. Os 121 eventos amostrados não são 121 município-dias positivos.

## 7. Leakage e prova pequena

Não foi executada a nova prova de 3–5 municípios/vários meses: a condição prévia de fonte adequada para negativos não passou. Não repetir a prova meteorológica 5B.1 só para produzir uma tabela com aparência de certificação.

Inspeção manual de duas linhas contra os bytes oficiais guardados: `2022_01_0000763` (Arouca, Florestal, 03/01/2022 18:45) e `2022_01_0000831` (São João da Madeira, Agrícola, 04/01/2022 02:45). Confirmados campos de origem, **não** adjudicação final do instante/label. Nos eliminados, `AT105511` está marcado `Duplicated`. Não existe amostra de negativos reais validada; declarar o contrário seria incorreto.

Quando desbloqueada, a prova proposta é Lisboa (1106), Vila Real (1714), Faro (0805), de 01/04 a 30/09 de um ano consolidado — proposta inicial 2022, sujeita à cobertura. 183 × 3 = 549 emissões. Label inclui mais 24h no fim. Usar Archive/IFS independente dos eventos, FWI cronológico validado, semente e sensibilidade documentadas. Se faltar classe positiva num município, não fabricar eventos nem escolher janelas apenas por incêndios.

Features permitidas: temperatura/RH/vento na referência anterior a T, chuva passada, FFMC/DMC/DC/ISI/BUI/FWI encadeados sem lacunas e variáveis temporais conhecidas. Guardar `valid_time`, produto, versão, coordenadas pedidas/devolvidas, `available_at` quando demonstrável. Não reutilizar meteorologia do CSV de incêndios: é condicionada à existência do evento e contém enriquecimentos posteriores. Proibir `Max*_PosExtincao`, área final, meios, duração, conclusão, causa futura, simultaneidade calculada com eventos futuros e identidade da ocorrência como features.

Archive retrospetivo pode sustentar estudo de associação/previsão retrospetiva, mas `valid_time<=T` não prova disponibilidade operacional em T. Documentar `available_at_historico=null` quando desconhecido; não chamar “previsão em tempo real”. Para simulação operacional, adquirir arquivo de runs/publicação ou recolher prospectivamente snapshots imutáveis. Não treinar para descobrir depois que as features dependiam de revisões futuras.

## 8. Gate de desbloqueio e plano condicionado

1. Obter resposta ICNF/ANEPC ao pedido preparado em `PEDIDO_DADOS_5B2.md` (não enviado). Confirmar licença dos CSV, dicionário, semântica/fuso, universo e consolidação; obter exportação filtrada oficial para os três municípios piloto com controlo de totais.
2. Se a exportação pública atual for confirmada adequada, descarregar snapshot integral uma vez, verificar tamanho/hash, CSV completo, IDs/revisões, min/max e totais; guardar eliminados e relações administrativas como versões separadas.
3. Adquirir apenas a CAOP necessária, verificar códigos/coordenadas/versões e quarentenar ambiguidades. Manter prova de cobertura por município e intervalo.
4. Fechar mapeamento dos códigos de taxonomia sem área/meios; adjudicar amostra manual de positivos, negativos e exclusões contra a fonte consolidada.
5. Executar as 549 linhas piloto e calcular contagens y1/y0/null e prevalência por município/ano/mês com denominador explícito. Testar fronteiras do horizonte, DST, duplicados, latência, lacunas e bloqueios de negativos.
6. Só então decidir novo GO explícito. Se passar, construir primeiro o conjunto continental definido (26 ou expansão justificada), split temporal cronológico e teste espacial por município. Ajustes de preprocessing só no treino; purge de horizontes sobrepostos nas fronteiras. Não misturar ilhas sem cobertura.
7. Antes do treino, rever relatório do dataset completo, hashes, exclusões e disponibilidade em T. Esta tarefa **não autoriza treino**.

## 9. Artefactos e validação

- `fontes_5b2.py`: aquisição limitada e cache com hashes, incluindo Range.
- `fontes_5b2/`: amostras/metadados originais e manifestos. Resposta de erro de serviço também preservada; HTTP 200 com erro ArcGIS não foi tratado como dataset válido.
- `auditar_5b2.py`, `auditoria_5b2/`: schema, contagens amostrais, 28 correspondências e integridade.
- `labels_5b2.py`, `test_5b2.py`: contrato trivalente e testes de fronteiras/cobertura/DST; sem treino.
- Este relatório e minuta de pedido.

Executados: `python -B experiments/ml_5b/auditar_5b2.py`; `python -B -m unittest discover -s experiments/ml_5b -p test_5b2.py -v` (**9/9 aprovados**); `git diff --check` no fecho. Apenas biblioteca padrão Python; sem nova dependência, Docker ou BD. Resultados anteriores e ficheiros ANPC não foram modificados.
