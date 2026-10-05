# Fase 8 — concluída

O bloqueio anterior de autorização foi resolvido pela instrução explícita de
retoma. `convergencia.py`, `rh100.py` e `verificar.py` concluíram sem erros,
em containers descartáveis sem rede, sem acesso à BD e sem novas recolhas.

Os dados históricos guardados não foram alterados. Foram gerados apenas
resultados, verificações e documentação experimentais.

- 306 768 horas e 12 782 dias únicos, sete regiões.
- 27 combinações de sementes, quatro horizontes, 28 matrizes completas.
- 759 213 passos diários multissemente; sete regressões anteriores exatas.
- 216 verificações RH com inputs equivalentes aprovadas.
- As 56 divergências originais face ao wrapper público permanecem registadas.
- Recomendação: conservar RH=100% real.
- Convergência não equivale a validação operacional: manter `reconstruido`.
- Produção intacta; nenhum commit.

Relatório completo: [RELATORIO.md](RELATORIO.md).
Resultados verificáveis: `evidencias/integridade.json`,
`evidencias/comparacao_sementes.csv` e `evidencias/rh100_impacto.json`.

Não repetir `dados.py`: as séries históricas estão completas.
