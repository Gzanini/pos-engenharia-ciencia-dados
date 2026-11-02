$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$sources = @("anp", "populacao", "pib", "ipca")

foreach ($source in $sources) {
    $sampleDirectory = Join-Path $projectRoot "data\samples\$source"
    $inputDirectory = Join-Path $projectRoot "data\input\$source"

    New-Item -ItemType Directory -Path $inputDirectory -Force | Out-Null
    Copy-Item -Path (Join-Path $sampleDirectory "*") -Destination $inputDirectory -Force
}

Write-Host "Amostras copiadas para data/input."

