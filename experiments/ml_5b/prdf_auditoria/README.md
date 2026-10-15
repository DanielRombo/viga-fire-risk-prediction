# Auditoria PRDF

Conclusão em `RELATORIO.md`; definição aprovada em `DECISAO_TEMPORAL.md`.
Os originais ficam exclusivamente em `data/prdf/`. Nenhum script carrega o candidato ML.

## Artefactos

- Inventário: `inventario.json`, `inventario_inicial.json`.
- Integridade/proveniência: `integridade_originais.json`, `proveniencia.json`.
- Inspeção por fonte: `fogos.json`, `meteo.json`, `frp.json`, `pba.json` e `*_execucao.json`.
- Cruzamentos: `cruzamentos.json`, `meteo_chaves.json`, `complementos.json`, `geometria.json`, `frp_cruzamento.json`.
- Território: `territorio_2025_amostra.csv`.
- Cobertura: `cobertura_2025.csv`, `cobertura_resumo.json`, `reconciliacao_2025.csv`.
- Estabilidade: `estabilidade_2025.csv`, `estabilidade.json`.
- Leakage: `leakage.csv`.
- Comparação temporal: `comparacao_temporal.json`, `amostras_temporais.json`.
- Scripts: `auditar_prdf.py`, `cobertura_prdf.py`, `geometria_prdf.py`, `meteo_chaves.py`, `complementos_prdf.py`, `estabilidade_prdf.py`, `sintese_prdf.py`, `comparar_timestamps.py`, `inspecao_inicial.py`.
- Testes: `test_prdf.py`, `test_temporal.py`.

## Fecho sem repetir auditoria pesada

```powershell
python -m unittest discover -s experiments/ml_5b/prdf_auditoria -p test*.py -v
git diff --check
git status --short
```

As fases pesadas já executadas são `auditar_prdf.py fogos|meteo|frp|pba`, seguidas dos scripts de cruzamento e síntese. Os comandos/versões das passagens principais estão nos `*_execucao.json`. Não é necessário repeti-las para consultar ou fechar o relatório. Python local registado: 3.13.13; SQLite: 3.50.4. Geometria foi executada num container isolado sem rede, sem arrancar serviços, com repositório read-only e escrita restrita à pasta da auditoria.
