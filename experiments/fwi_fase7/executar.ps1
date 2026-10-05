param([ValidateSet('preparar','recolher','reconstruir','referencia','comparar')][string]$Modo, [int]$Dias=60)
$ErrorActionPreference='Stop'
$raizEnsaio=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$ev=(Resolve-Path (Join-Path $PSScriptRoot 'evidencias')).Path
$mounts=@('--mount',"type=bind,source=$raizEnsaio,target=/workspace,readonly",'--mount',"type=bind,source=$ev,target=/evidencias")
if ($Modo -eq 'referencia') {
    docker run --rm --network none @mounts r-base:4.5.3 Rscript /workspace/experiments/fwi_fase7/referencia.R $Dias
} else {
    $redeEnsaio=if ($Modo -eq 'recolher') {'bridge'} elseif ($Modo -eq 'comparar') {'none'} else {'container:viga-fwi-phase7-db'}
    $urlEnsaio=if ($Modo -in @('preparar','reconstruir')) {"postgresql+psycopg2://postgres@127.0.0.1/viga_fwi_test_phase7_$Dias"} else {'postgresql+psycopg2://test@127.0.0.1:1/sem_acesso'}
    docker run --rm --network $redeEnsaio @mounts -e "DATABASE_URL=$urlEnsaio" -e PYTHONDONTWRITEBYTECODE=1 projeto_final_curso-backend:latest python /workspace/experiments/fwi_fase7/ensaio.py $Modo $Dias
}
exit $LASTEXITCODE
