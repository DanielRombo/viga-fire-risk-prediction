# Fase 7 — método e reprodução

## Âmbito

Só scripts/evidências experimentais; nenhum ficheiro de produção é alterado.
Reutiliza `experiments/fwi_fase6/ensaio.py` e `analisar.py` por importação,
com diretório de saída e ligação à BD substituídos apenas no processo do ensaio.
Não importa `main`, não inicia jobs, não executa Compose, não escreve na produção.

Catálogo atual: 30 pontos, 28 com recolha automática. Gondomar e Barcelos
também são incluídos para não excluir regiões existentes do catálogo.
Os 25 pontos não validados na Fase 6 recebem primeiro uma janela de 60 dias.

Janela curta: 02/08/2026–30/09/2026. Janela anual: 01/10/2025–30/09/2026.
Data operacional de ensaio: 01/10/2026. Semente convencional explícita no dia
anterior: FFMC=85, DMC=6, DC=15. Todas as sequências ficam `reconstruido`.

Amostra anual planeada: Porto (litoral norte), Bragança (interior norte),
Coimbra (centro), Castelo Branco (interior centro), Évora (Alentejo), Faro
(Algarve). Faro é o único ponto algarvio do catálogo, pelo que a exclusão
da repetição dos seus 60 dias não impede a extensão anual solicitada.
Todas as regiões com alertas na janela curta são também ampliadas para um ano.
As sequências anuais são independentes das curtas, noutra BD descartável;
não se substituem resultados nem se alteram configurações já persistidas.

## Fonte e integridade

Open-Meteo Archive, `models=ecmwf_ifs`, mesma configuração da Fase 6.
Sem fallback, sem retries escondidos. Uma chamada em lote por região/janela;
o fluxo de reconstrução existente recebe os intervalos reais diários desse lote.
Não se mede aqui o custo de pedir cada dia remotamente em separado.

Unidades: temperatura °C, humidade %, vento km/h a 10 m, precipitação mm;
timestamps GMT/UTC; coordenadas em graus. Temperatura/humidade/vento em t,
precipitação das 24 horas terminadas em t: `(t-24h,t]`.
Continente/Madeira: 12:00 UTC; Açores: 13:00 UTC.

Guarda resposta HTTP integral, SHA-256, parâmetros, instante de ingestão,
coordenadas solicitadas/devolvidas, snapshots horários/diários, estado
anterior, índices, estatísticas e resultados API. O modelo é explícito no
pedido; a resposta não o identifica novamente de forma independente.

Falha estrutural/HTTP, lacuna, duplicado, null, NaN, infinito ou negativo
inválido bloqueia o respetivo passo. Não se preenche, corrige ou limita
nenhum valor para fazer o ensaio passar.

## Triagem exploratória

Limiares fixados no script antes de inspecionar os resultados desta fase:

- Variação absoluta diária: FFMC>40; DMC>100; DC>150; ISI>15; BUI>100; FWI>25.
- FWI>50: alerta exploratório de valor elevado.
- Máximo regional acima de Q3+3×IQR dos máximos das regiões na mesma janela:
  alerta exploratório de discrepância espacial.

Estes limiares **não são classes oficiais, limites físicos ou prova de erro**.
Valores inferiores aos limiares também podem ter problemas não detetados
por esta triagem. Não se afirma que a ausência de alerta prove validade
meteorológica. Não se atribuem classificações de risco à interface.

Todos os dias sinalizados são acrescentados à amostra do código R original
cffdrs 1.8.17 já preservado na prova. São usados os inputs reais, latitude,
data e FFMC/DMC/DC anteriores persistidos. Tolerâncias inalteradas:
`atol=1e-8`, `rtol=1e-10`. Sem equivalência alegada com cffdrs 1.9.2.
Não se recalcula toda a sequência científica em R.

A investigação regista para cada alerta inputs, diferenças meteorológicas,
estado anterior e comparação R. Examina-se o contexto de chuva/secagem,
vento/humidade e a grelha espacial. A explicação numérica não valida o
produto meteorológico contra medições locais independentes.

## Ilhas e interpretação nacional

Funchal e Ponta Delgada são excluídos da nova recolha de 60 dias conforme o
pedido. As suas evidências da Fase 6 são verificadas novamente offline,
incluindo checksum e todos os 24 intervalos de cada dia. Não se faz uma
nova chamada externa para repetir esse trabalho.

São os únicos pontos da Madeira/Açores no catálogo atual; não representam
automaticamente as restantes ilhas, vertentes, altitudes ou microclimas.
A tabela nacional reúne pontos do catálogo, não cria um índice agregado
nem demonstra cobertura espacial integral de Portugal.

## Comandos

Na raiz do projeto, com Docker disponível:

```powershell
docker run --detach --rm --name viga-fwi-phase7-db --network none -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_DB=viga_fwi_test_phase7_60 postgis/postgis:15-3.3
docker exec viga-fwi-phase7-db createdb -U postgres viga_fwi_test_phase7_365
powershell.exe -NoProfile -ExecutionPolicy Bypass -File experiments/fwi_fase7/executar.ps1 preparar 60
powershell.exe -NoProfile -ExecutionPolicy Bypass -File experiments/fwi_fase7/executar.ps1 preparar 365
powershell.exe -NoProfile -ExecutionPolicy Bypass -File experiments/fwi_fase7/executar.ps1 recolher 60
powershell.exe -NoProfile -ExecutionPolicy Bypass -File experiments/fwi_fase7/executar.ps1 reconstruir 60
# Em container sem rede, com repositório readonly e evidencias montadas:
python /workspace/experiments/fwi_fase7/analisar.py 60
powershell.exe -NoProfile -ExecutionPolicy Bypass -File experiments/fwi_fase7/executar.ps1 referencia 60
powershell.exe -NoProfile -ExecutionPolicy Bypass -File experiments/fwi_fase7/executar.ps1 comparar 60
# Examinar os alertas antes da ampliação.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File experiments/fwi_fase7/executar.ps1 recolher 365
powershell.exe -NoProfile -ExecutionPolicy Bypass -File experiments/fwi_fase7/executar.ps1 reconstruir 365
python /workspace/experiments/fwi_fase7/analisar.py 365
powershell.exe -NoProfile -ExecutionPolicy Bypass -File experiments/fwi_fase7/executar.ps1 referencia 365
powershell.exe -NoProfile -ExecutionPolicy Bypass -File experiments/fwi_fase7/executar.ps1 comparar 365
python /workspace/experiments/fwi_fase7/analisar.py tabelas
python /workspace/experiments/fwi_fase7/concluir.py
python /workspace/experiments/fwi_fase7/validar.py
git diff --check
docker stop viga-fwi-phase7-db
```

`executar.ps1` especifica mounts, redes, imagem e variáveis; não carrega .env.prod.
A recolha não tem acesso à BD, e os processos com acesso à BD partilham
apenas a rede `none` do container descartável. PostgreSQL usa `trust` só
nesse ambiente sem portas, não uma password hardcoded nem credenciais reais.
Os ficheiros de produção são montados apenas para leitura.

## Ficheiros e evidências

- `ensaio.py`: catálogo completo, ligação restrita, orquestração experimental.
- `executar.ps1`: runners Docker sem alteração dos serviços existentes.
- `analisar.py`: estatísticas, triagem e amostra de dias sinalizados.
- `referencia.R`: chamada ao código cffdrs preservado, sem alterações científicas.
- `concluir.py`: investigação por alerta, sensibilidade à janela e resumo medido.
- `validar.py`: cobertura, integridade, cadeia, referência e ilhas.
- `evidencias/60/` e `365/`: dados reais e resultados separados.
- `evidencias/estatisticas_nacionais.csv` e `.md`: seis índices por ponto/janela.
- `evidencias/investigacao_alertas.json` e `.md`: um registo por alerta.
- `evidencias/sensibilidade_janela.json`: diferença entre estados curtos/anuais
  usando as mesmas horas sobrepostas; não define convergência suficiente.

Nenhum texto público, dependência, endpoint, frontend, scheduler ou fórmula
do projeto é alterado por esta fase.
