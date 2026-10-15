# ML 5B.7 — cobertura 2025

Ler `RELATORIO.md` para a decisão e `fontes.csv` para fontes/limitações. Resultados reproduzíveis a partir dos pequenos artefactos locais; não avaliam o candidato ML.

## Artefactos

- `fontes.csv`, `proveniencia.csv`: 19 entradas e linhagem.
- `matriz_cobertura_2025.csv`: 36 blocos município/mês.
- `contagens_municipais.csv`, `contagens_mensais.csv`, `resultado.json`: estimativas, sem labels finais.
- `reconciliacao_anual.csv`, `reconciliacao_mensal.csv`, `ine_verificacao.json`: comparação com fontes oficiais.
- `config.json`: condições explícitas para zero e âmbito.
- `fontes_nao_uteis.md`: prevenção de interpretações indevidas.
- `manifesto_inputs.json`, `evidencias/*.json`: hashes e metadados de aquisição.
- `pesquisar_fontes.py`: downloads limitados, cache, redirects e erros preservados.
- `inspecionar_documentos.py`: inspeção local do PDF, sem rede.
- `consolidar.py`: gera tabelas apenas com pequenos inputs já obtidos.
- `test_cobertura.py`: nove testes.

## Comandos usados

```powershell
python experiments/ml_5b/cobertura_5b7/pesquisar_fontes.py todas
python -m pip install --target experiments/ml_5b/cobertura_5b7/_deps pypdf==6.1.1 --disable-pip-version-check
python experiments/ml_5b/cobertura_5b7/inspecionar_documentos.py
python experiments/ml_5b/cobertura_5b7/consolidar.py
python -m unittest discover -s experiments/ml_5b/cobertura_5b7 -p test_cobertura.py -v
git diff --check
git status --short
```

A rede e o leitor PDF exigiram execução autorizada fora do sandbox. Os erros iniciais de rede foram guardados; não representam falhas das fontes. O endpoint histórico ANEPC devolveu HTML, não dados. As leituras existentes são reutilizadas: não repetir downloads para consultar o relatório.

Os binários/PDFs e `_deps` ficam locais e ignorados. Os metadados e fontes permitem recuperar os documentos, mas a publicação remota pode mudar; usar os hashes para distinguir versões. O PDF SGIFR foi inspecionado por inteiro para termos de cobertura/consolidação; páginas relevantes 13, 30, 105, 118 e 133. Texto extraído integral dessas páginas fica local, excluído do Git; as conclusões são documentadas no relatório.

Pesquisa dirigida em 14/10/2026: ANEPC/PROCIV ocorrências e dados abertos 2025; DECIR2025 registo SADO; ICNF/SGIFR relatório anual/provisório 2025; INE13512/metodologia; dados.gov ProCiv; relatórios municipais Lisboa/Faro/Vila Real; EFFIS metodologia; FIRMS deteções ausentes; documentação IRS/FaRDaP inglesa como plano B. Não é uma garantia de exaustividade de todos os arquivos municipais existentes.
