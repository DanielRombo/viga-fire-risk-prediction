# FWI diário — Fase 5: apresentação no frontend

## Comportamento

O dashboard apresenta um cartão compacto **FWI diário**, associado à região
selecionada, junto do índice legado. Mostra o valor, a data de referência,
o estado, o indicador operacional e a mensagem da API.

Nos detalhes existe uma secção com FFMC, DMC, DC, ISI, BUI e FWI, timestamps UTC
persistidos, origem, método, versão, variante, inicialização, série e revisão.
Não se usam limites, cores de risco ou recomendações do índice legado no novo
painel. As cores são neutras, compatíveis com as variáveis dos temas existentes.
Os valores são apresentados com até duas casas decimais; o backend mantém a
precisão original. `null` e valores inválidos são `Indisponível`; zero é `0`.

Só se mostra `Operacional estabelecido` quando os campos da API são coerentes:
`operacional` e `estabelecido` verdadeiros, estado `ok`, inicialização/qualidade
estabelecidas, validade adequada, revisão não desativada e seis índices finitos
não negativos. Uma resposta contraditória não é promovida pelo frontend.

O histórico mostra até 30 dias terminados na data de referência fornecida pela
API, por ordem cronológica. A consulta fixa a mesma série e revisão do cartão.
Não mistura revisões nem usa a hora do browser para determinar a janela.
Um erro no histórico não oculta o resultado diário; uma falha da meteorologia
legada nos detalhes também não oculta a secção FWI diário.

## Carregamento e compatibilidade

Os pedidos usam os endpoints da Fase 4. `criarCarregadorFWI` não cria timers:
o dashboard e os detalhes chamam-no no ciclo de atualização de 60 segundos
que já existia. O FWI diário é carregado independentemente do risco legado.

Mudar de região limpa a apresentação anterior. Cada resposta é verificada
contra a região, o pedido mais recente e o ciclo de vida da página. Respostas
atrasadas, incluindo do histórico, são ignoradas. Os detalhes passaram também
a proteger os seus pedidos existentes durante mudanças de região.

O índice legado mantém valores, classes e recomendações anteriores. As únicas
mudanças no mapa e no painel ML são designações que identificam o legado;
não se alteraram os modelos ML, as camadas, a seleção, o zoom ou o cálculo.
Não há alterações ao backend, à autenticação, à NASA, às dependências ou ao Docker.

## Ficheiros

| Ficheiro | Alteração |
|---|---|
| `frontend/src/components/PainelFWIDiario.jsx` | Painel compacto, detalhes e tabela histórica. |
| `frontend/src/components/PainelFWIDiario.css` | Estilos neutros e grelha adaptável. |
| `frontend/src/utils/fwiDiario.js` | Estados, formatação, validação e controlo dos pedidos, sem timers. |
| `frontend/src/services/api.js` | Dois métodos de leitura do novo FWI. |
| `frontend/src/pages/Dashboard.jsx` | Carregamento pelo refresh existente e região selecionada. |
| `frontend/src/components/Sidebar.jsx` | Cartão compacto e identificação do legado. |
| `frontend/src/pages/DetalheRegiao.jsx` | Painel completo, histórico e proteção de respostas atrasadas. |
| `frontend/src/components/PainelML.jsx` | Designação e tooltip do índice legado; ML intacto. |
| `frontend/src/components/MapaInterativo.jsx` | Apenas designações da camada e popup legados. |
| `frontend/tests/fwiDiario.test.mjs` | Dez testes unitários novos. |
| `frontend/tests/fwiDiario.browser.mjs` | Seis cenários Edge novos. |
| `frontend/tests/dashboard.browser.mjs` | API diária simulada e atualização das designações esperadas; mantém os cinco cenários existentes. |
| `frontend/tests/risco.test.mjs` | Referência ao `fwi_legado.py` já separado na Fase 1 e reconhecimento das duas formas de aspas Python. |
| `docs/fwi_diario_fase5.md` | Comportamento, textos, validação e limitações. |

## Textos visíveis criados ou alterados

Lista dos textos estáticos do novo painel; os nomes de regiões, números,
timestamps, origem, método, versões, variante e mensagens são valores da API:

| Grupo | Textos |
|---|---|
| Título e valor | `FWI diário`; variante `FWI diário — {localidade}`; `Indisponível`. |
| Estados | `Atual`; `Desatualizado`; `Indisponível`; `Em inicialização`; `Em reconstrução`; `Dados incompletos`; `Erro da fonte`; `Estado anterior ausente`; `Não operacional`. |
| Operacionalidade | `Operacional estabelecido`; `Não operacional — valor técnico, quando disponível.` |
| Inicialização | `Sem estado anterior`; `Inicializado convencionalmente`; `Em inicialização`; `Em reconstrução`; `Reconstruído, não estabelecido`; `Estabelecido`; `Falha na reconstrução`. |
| Componentes | `FFMC`; `DMC`; `DC`; `ISI`; `BUI`; `FWI`. |
| Proveniência | `Data de referência`; `Instante de referência`; `Calculado em`; `Origem`; `Método`; `Versão`; `Versão xclim`; `Variante`; `Inicialização`; `Série`; `Revisão`; sufixo temporal `UTC`. |
| Série e revisão | `Série operacional`; `Reconstrução histórica`; `Não aplicável`; `{revisão} — ativa`; `{revisão} — não ativa`. |
| Classificação | `Valor numérico sem classificação de risco nesta fase.` |
| Histórico | `Histórico FWI diário`; `Até 30 dias, na mesma série e revisão do resultado apresentado.`; `Operacional`; `Sim`; `Não`. |
| Carregamento | `A carregar FWI diário…`; `A carregar histórico FWI diário…`. |
| Ausência e falhas | `FWI diário indisponível.`; `Não foi possível obter o FWI diário.`; `Não foi possível obter o histórico FWI diário.`; `Histórico FWI diário indisponível.`; `Sem histórico diário disponível.` |

Textos legados alterados para evitar confusão:

- `FWI {valor} — ML {percentagem}` → `Índice legado {valor} — ML {percentagem}`.
- `Previsão ML + FWI` → `Previsão ML + índice legado`, no dashboard e detalhes.
- `FWI` → `Índice legado`, no cartão antigo e na coluna do histórico antigo.
- `Risco FWI` → `Risco legado`, no seletor de camadas.
- `FWI: {valor}` → `Índice legado: {valor}`, no popup do mapa.
- Novo tooltip: `Índice legado — heurística baseada em temperatura, humidade, vento e precipitação; distinto do FWI diário.`

As mensagens explicativas recebidas da API são apresentadas como texto React,
sem interpretação de HTML. Não foram criadas classes de risco para o FWI diário.

## Validação

- 37 testes unitários frontend passaram (dez novos e 27 existentes).
- 11 cenários Edge passaram: cinco existentes e seis novos. Incluem estados,
  null/zero, erro HTTP, troca de região, resposta atrasada, refresh único,
  Continente/Madeira/Açores, timestamps, histórico, preservação do legado e
  falha da meteorologia independente. O cenário adicional de troca nos detalhes
  foi executado separadamente, sem repetir os cenários já aprovados.
- Build Vite passou, incluindo build com `VITE_API_URL=/api`.
- Regressão backend necessária: 19 testes do contrato da Fase 4 passaram em
  contentor isolado. Não se alterou o backend nem se repetiu a prova científica.
- `git diff --check` e verificação dos ficheiros novos concluídos.

Comandos usados, a partir de `frontend`:

```powershell
node --test tests/*.test.mjs
$env:VIGA_PLAYWRIGHT_MODULE = '<instalação temporária>/node_modules/playwright/index.mjs'
node --test --test-isolation=none tests/fwiDiario.browser.mjs
$env:VITE_API_URL = '/api'
npm.cmd run build
```

Os testes browser usam o Edge instalado, Vite local e APIs simuladas. Não foram
adicionadas dependências ao projeto. O teste de risco antigo inicialmente
falhou porque procurava as classes no módulo anterior à separação do legado;
a referência foi atualizada sem remover verificações.

## Limitações

A apresentação depende dos estados persistidos da API: não estabelece nem
inicializa sequências. Usa a seleção automática de série da API para o último
resultado, mostrando a série e a revisão nos detalhes. Não existe ainda um
seletor de séries/revisões, paginação histórica adicional ou classificação
científica de risco para o novo índice. O histórico é deliberadamente simples.
Não houve deployment nem alterações à produção. Não foi feito commit.
