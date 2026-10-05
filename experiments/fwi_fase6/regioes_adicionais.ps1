$ErrorActionPreference = 'Stop'
$raizEnsaio = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$evidenciasEnsaio = (Resolve-Path (Join-Path $PSScriptRoot 'evidencias')).Path
$montagens = @('--mount', "type=bind,source=$raizEnsaio,target=/workspace,readonly",
    '--mount', "type=bind,source=$evidenciasEnsaio,target=/evidencias")
$imagemEnsaio = 'projeto_final_curso-backend:latest'
$piloto = Get-Content -Raw -Encoding utf8 "$evidenciasEnsaio/Lisboa_comparacao.json" | ConvertFrom-Json
if (-not $piloto.passou) { throw 'A comparação científica de Lisboa não passou.' }
foreach ($nome in @('Faro', 'Vila Real', 'Funchal', 'Ponta Delgada')) {
    docker run --rm --network bridge @montagens -e DATABASE_URL=postgresql+psycopg2://test@127.0.0.1:1/sem_acesso -e PYTHONDONTWRITEBYTECODE=1 $imagemEnsaio python /workspace/experiments/fwi_fase6/ensaio.py recolher $nome 60
    if ($LASTEXITCODE -ne 0) { throw "Recolha bloqueada: $nome" }
    docker run --rm --network container:viga-fwi-phase6-db @montagens -e DATABASE_URL=postgresql+psycopg2://postgres@127.0.0.1/viga_fwi_test_phase6 -e PYTHONDONTWRITEBYTECODE=1 $imagemEnsaio python /workspace/experiments/fwi_fase6/ensaio.py reconstruir $nome
    if ($LASTEXITCODE -ne 0) { throw "Reconstrução bloqueada: $nome" }
    docker run --rm --network none @montagens $imagemEnsaio python /workspace/experiments/fwi_fase6/analisar.py preparar $nome
    if ($LASTEXITCODE -ne 0) { throw "Análise bloqueada: $nome" }
    docker run --rm --network none @montagens r-base:4.5.3 Rscript /workspace/experiments/fwi_fase6/referencia.R $nome
    if ($LASTEXITCODE -ne 0) { throw "Referência bloqueada: $nome" }
    docker run --rm --network none @montagens $imagemEnsaio python /workspace/experiments/fwi_fase6/analisar.py comparar $nome
    if ($LASTEXITCODE -ne 0) { throw "Divergência científica: $nome" }
}
