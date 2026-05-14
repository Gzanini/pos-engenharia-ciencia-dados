param(
    [string]$Source = "C:\Users\Guilherme_Zanini\Desktop\Pos-unisinos\tipos_de_dados\Arquivos base",
    [string]$Target = "C:\Users\Guilherme_Zanini\Documents\github\pos-engenharia-ciencia-dados\tipos-dados-avancados-modelagem-ciencia-dados\data\backup"
)

if (!(Test-Path -LiteralPath $Source)) {
    throw "Pasta de origem não encontrada: $Source"
}

New-Item -ItemType Directory -Path $Target -Force | Out-Null
Copy-Item -Path (Join-Path $Source '*') -Destination $Target -Force
Write-Host "Arquivos copiados de '$Source' para '$Target'."
