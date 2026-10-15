# ML 5B.5 — desenvolvimento temporal

`experimento.py` lê apenas linhas 2022–2023 do dataset elegível, valida o hash e executa os folds de `config.json`. O CSV de origem inclui 2024, mas essas linhas são descartadas antes de construir arrays/estatísticas. Nenhuma métrica ou modelo de 5B.4 é carregado: só as funções puras de métricas de `comum.py` são reutilizadas.

Execução: Python 3.11 na imagem backend existente, `docker run --rm --network none --entrypoint python`, `OMP_NUM_THREADS=1`, `PYTHONDONTWRITEBYTECODE=1`, repositório em `/repo:ro` e apenas esta pasta gravável. Sem dependências novas, credenciais, BD, downloads, produção ou treino dos modelos oficiais.

O script recusa sobrescrever resultados já existentes. Para reprodução usar cópia isolada nova dos inputs/configuração, não apagar a evidência anterior. Testes: `python test_temporal.py -v` no mesmo ambiente. Joblib experimental ignorado; nunca importar na aplicação.

Métricas: AP = average precision, não área trapezoidal. `resultados_folds.json` conserva bins, matrizes, threshold e métricas por fold/grupo. `estabilidade.json` resume média/mediana/desvio amostral/melhor/pior. `drift.csv` não aplica correções, e KS é descritivo, não um teste independente sobre dias autocorrelacionados. `composicao.json` descreve a mudança de municípios/meses. `importancia.json` é explicação no desenvolvimento, não causalidade.

Modelos fixos: logística C=1; HGB 100 iterações, 7 folhas, mínimo 20/folha, L2=1, early stopping desligado; RF 200 árvores, profundidade 5, mínimo 10/folha; baseline de prevalência do fit. Seed 42. Logística/HGB/RF com e sem class_weight=balanced. Sem SMOTE nem pesquisa adicional de hiperparâmetros.

Calibração sigmoid: logística regularizada C=1 sobre logit do score base (clip 1e−6), ajustada apenas em Vila Real no bloco posterior ao fit e anterior à avaliação. O mesmo bloco escolhe threshold por F1; isso é ajuste interno conjunto, não uma avaliação independente. O fold exterior avalia ambos. Isotonic excluída previamente por escassez de positivos. A/E, ponderação e calibração são alternativas de desenvolvimento, não experimentos externos independentes.

Configuração E inclui município para testar controlo de diferentes taxas de base no treino combinado; não é identificação numérica ordinal. F1/F2 podem ter apenas Vila Real no fit; one-hot ignora categorias desconhecidas. Seleção principal apenas Vila Real; Lisboa é secundária e Faro não tem dados elegíveis de desenvolvimento. Não alegar generalização aos três municípios.

2024 foi consumido anteriormente e está proibido para seleção, afinação ou nova avaliação nesta fase. Ver relatório para elegibilidade de 2025; dados futuros não são usados para escolher candidato.
