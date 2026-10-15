# Limitações científicas que permanecem

1. Apenas 132 positivos nas 1693 linhas elegíveis; alguns folds exteriores têm dois positivos.
2. Vila Real domina a evidência longitudinal. Faro só é elegível em 2024; Lisboa não tem positivos elegíveis em 2022 e está null em 2024.
3. Drift de prevalência, sazonalidade e composição municipal; a amostra não representa uniformemente o território.
4. Negativos 2022–2024 são condicionais à cobertura empírica, não certificação universal independente de incêndios ausentes.
5. Seleção por insensibilidade às sementes FWI exclui 1174 dias e pode introduzir viés meteorológico. Os motivos de exclusão sobrepõem-se.
6. Thresholds e importâncias variam entre folds; não existe ponto de operação estável demonstrado.
7. Sigmoid não melhora todos os folds; Brier e bins não sustentam probabilidade operacional.
8. Seleção entre 61 configurações com quatro folds sobrepostos no treino induz otimismo; média/desvio não são intervalos de confiança independentes.
9. 2024 foi observado em 5B.4. Não pode selecionar/afinar o candidato 5B.5 nem ser novamente apresentado como teste novo.
10. Nenhum negativo certificado em 2025; 36 blocos dos três municípios permanecem DUVIDOSO.
11. PRDF harmoniza SGIF/ICNF, não é fonte independente de ocorrências. INE e AGIF não multiplicam independência por republicarem dados relacionados.
12. Não foi obtido histórico público SADO completo verificável. Registo obrigatório não prova equivalência/completude do export.
13. Divergência oficial de reacendimentos SGIF (~8%) versus SADO (6,4%) em 2025; não harmonizada automaticamente.
14. Timestamp é operacional de alerta; fuso histórico não totalmente esclarecido. Casos com presença diferente entre convenções são null.
15. Observação meteorológica com valid_time≤T não prova available_at≤T. Archive/IFS é retrospetivo e pode incorporar revisões posteriores.
16. Um ponto meteorológico não representa toda a heterogeneidade municipal; confiança territorial média e limites CAOP2025 aplicados a anos anteriores.
17. Importâncias e coeficientes são associações descritivas, não causalidade; permutar features físicas correlacionadas pode criar combinações irreais.
18. Resultados do modelo 5B.4 não são resultados externos do candidato congelado 5B.5, apesar de ambos usarem HistGradientBoosting.

Não se eliminam estas limitações renomeando o score como probabilidade ou reavaliando o teste já observado.
