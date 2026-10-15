# Fecho científico ML 5B.8

Estado: **ML 5B encerrado como linha experimental, sem validação operacional.**

Ler `RELATORIO_FINAL.md`, `limitacoes.md` e `estado_modelo.json`.
Resultados históricos copiados de JSONs, sem recalcular métricas ou carregar modelos.

```powershell
python experiments/ml_5b/fecho_5b8/validar_fecho.py
python -m unittest discover -s experiments/ml_5b/fecho_5b8 -p test_fecho.py -v
git diff --check
git status --short
```

`--gerar` regenera apenas os pequenos resumos/CSV deste diretório a partir dos artefactos existentes; não treina, avalia ou cria datasets. Os manifestos5B.4/5B.5 são verificados antes de gerar; divergência interrompe a execução. Não executar scripts de treino/avaliação para reproduzir este fecho.

Inventário: `inventario_artefactos.csv` e `inventario_resumo.json`.
Lista exata para revisão de commit: `commit_recomendado.txt`.
Exclusões: `fora_commit.csv`; adicionalmente `data/prdf/`, caches/dependências omitidos e todas as áreas fora do ML.
Nenhum staging/commit automático. Guardar os artefactos ignorados num arquivo protegido com hashes, sem os duplicar nesta pasta.
