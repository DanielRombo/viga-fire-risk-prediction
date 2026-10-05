param([string]$Script,[switch]$Rede)
$raiz=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$ev=(Resolve-Path (Join-Path $PSScriptRoot 'evidencias')).Path
$redeEnsaio=if ($Rede) {'bridge'} else {'none'}
docker run --rm --network $redeEnsaio --mount "type=bind,source=$raiz,target=/workspace,readonly" --mount "type=bind,source=$ev,target=/evidencias" -e DATABASE_URL=postgresql+psycopg2://test@127.0.0.1:1/sem_acesso -e PYTHONDONTWRITEBYTECODE=1 projeto_final_curso-backend:latest python "/workspace/experiments/fwi_fase8/$Script"
exit $LASTEXITCODE
