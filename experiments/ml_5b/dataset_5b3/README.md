# Dataset ML 5B.3

Dataset **retrospetivo** de Lisboa (1106), Faro (0805) e Vila Real (1714), 2022–2024. Não contém um modelo treinado. Não é uma certificação de ausência física de incêndio nem um backtest de disponibilidade em tempo real.

- `dataset_completo.csv`: inventário auditável de 3288 município-dias, incluindo null e cobertura não aceite.
- `dataset_elegivel.csv`: 1693 linhas conservadoramente elegíveis; usar só as `features_permitidas` de `schema.json`.
- `exclusoes.csv`: 1595 linhas excluídas com motivos, sem apagar valores ou preencher labels.
- `qualidade.json`: contagens por município, ano, mês, município/ano/mês e split, qualidade e rastreabilidade meteorológica.
- `manifesto.json`, `checksums.json`: versões, fontes e hashes. Os CSV não estão autorizados para versionamento e são ignorados localmente.
- `amostra_validada.json`: contraprova de 10 positivos, 20 negativos e 6 null no export original.
- `RELATORIO.md`: decisões, resultados e limitações.

T=15:00 UTC. Temperatura (°C), humidade (%) e vento a 10 m (km/h) referem-se às 12:00 UTC do mesmo dia. Chuva em mm: soma dos 24 intervalos horários que terminam em `(T−27 h,T−3 h]`. Os seis índices usam o estado do dia anterior. Município é código textual, não ID da BD. Semana: segunda=0, domingo=6. Épocas são estações meteorológicas DJF/MAM/JJA/SON, sem classificação oficial de perigo.

Null CSV é campo vazio. Não converter para zero. `available_at_historico` vazio é intencional: não foi demonstrada a data de publicação dos valores Archive. As restantes features permitidas estão completas. Todas as colunas de cobertura, target, contagens de eventos, exclusões e proveniência são **metadados proibidos como features**.

Reprodução: executar `experiments/ml_5b/construir_5b3.py` na imagem backend validada (Python 3.11, xclim 0.62.0), com rede desligada, repositório montado em `/repo:ro` e apenas esta pasta gravável. Requer os originais locais cujos caminhos/hashes constam no manifesto; estes não acompanham automaticamente um clone. Não executar a aplicação nem passar credenciais de BD.

Depois executar `python -B experiments/ml_5b/validar_5b3.py --amostra` e `python -B experiments/ml_5b/validar_5b3.py -v`. O construtor atualiza checksums incluindo uma amostra já existente; caso esta seja regenerada, confirmar que o hash coincide ou regenerar o manifesto. Não há chamadas de rede no construtor nem no validador.

**GO condicionado para ML 5B.4 experimental**, sujeito a avaliação temporal por município, não a uma promessa de previsão real. Não foi iniciado treino. Produção/API/frontend/modelos atuais permanecem intocados.
