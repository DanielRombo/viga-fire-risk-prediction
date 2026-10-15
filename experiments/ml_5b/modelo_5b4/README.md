# ML 5B.4 — experiência isolada

Não importar estes modelos no backend. Artefactos joblib são locais/ignorados. As saídas são scores experimentais de ignição rural **registada** no SGIF, não probabilidades operacionais.

Ordem de reprodução num diretório de resultados novo: `treinar.py` → rever `decisao_congelada.json` → `avaliar.py` → `test_experimento.py -v`. Avaliação recusa sobrescrever `metricas_teste.json`; não remover essa proteção para selecionar novamente no holdout. Usar Python e versões de `versoes.json`, sem atualizar dependências. Os originais do dataset são necessários e os hashes são verificados.

Execução utilizada: imagem backend existente, `docker run --rm --network none --entrypoint python`, `PYTHONDONTWRITEBYTECODE=1`, `OMP_NUM_THREADS=1`, repositório em `/repo:ro`, apenas `experiments/ml_5b/modelo_5b4` gravável. Não passar URLs/credenciais de BD. Não houve chamada a produção ou à rede.

`config.json` fixa seed 42, critérios e splits. `decisao_congelada.json` regista hashes dos modelos, dataset, código, threshold e seleção feita em 2023. `metricas*.json` inclui todos os grupos e bins; `metricas.csv` resume, `thresholds_validacao.csv` guarda os 99 thresholds por modelo. `scores_teste.csv` permite auditar métricas sem voltar a ajustar ou escolher modelos. `fiabilidade.svg` é uma figura autónoma, bins vazios não são representados como zero. A diagonal é referência de calibração, não curva de outro modelo.

Não usar todas as colunas do dataset como features: a lista permitida está explícita em `comum.py`. Não existem imputação de labels, SMOTE, random split, calibração no teste ou re-treino com 2023. `OneHotEncoder(handle_unknown='ignore')` trata Faro desconhecido como vetor municipal zero; isto é uma limitação de transferência, não evidência de aprendizagem em Faro.

Ver `RELATORIO.md` para interpretação e decisão experimental.
