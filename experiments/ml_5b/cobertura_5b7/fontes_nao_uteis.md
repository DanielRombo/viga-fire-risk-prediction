# Fontes que não certificam negativos para este target

- FIRMS/VIIRS, FRP: atividade térmica detetada; ausência pode decorrer de nuvens, passagens, tamanho/intensidade. Apoio a positivos, nunca zero por ausência.
- PBA/EFFIS: perímetros finais e área; não incluem necessariamente todos os pequenos eventos e podem incluir fogo prescrito. Datas de deteção não equivalem a alerta.
- METEO PRDF: séries selecionadas pelo evento, incluindo informação posterior. Não é inventário de cobertura dos dias sem ocorrência.
- ICNF/INE/PRDF/SGIFR: concordância entre republicações melhora rastreabilidade, mas não cria quatro fontes independentes.
- ProCiv em aberto: fotografia de ocorrências ainda ativas; ausência atual não demonstra ausência histórica. Endpoint antigo com HTTP 200 redirecionado para HTML não é export vazio.
- Fogos.pt e reutilizações de alertas: derivam da fonte operacional; sem histórico auditado de falhas de captura não certificam ausência.
- Relatórios de estabilização, grandes incêndios, limiares de área, notícias municipais: universos seletivos. Não observar uma ocorrência não prova que ela não foi registada.
- Na Minha Rua e estatísticas pré-hospitalares: outros universos; não demonstram incêndios rurais.
- Planos municipais/mapas de perigosidade: planeamento, não completude de reporte.
- Norma de registo obrigatório: documenta o universo pretendido; não prova, sozinha, execução sem lacunas nem equivalência entre o export público e a BD operacional.

As referências verificadas e a classificação A/B/C/D estão em `fontes.csv`. A categoria A do plano B inglês é utilidade potencial da documentação para auditar negativos nesse território; nenhum período inglês foi certificado nesta tarefa, nem é aplicável ao modelo português congelado sem decisão metodológica própria.
