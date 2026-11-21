param(
    [ValidateSet("start", "stop", "status", "logs", "gpu")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot

try {
    switch ($Action) {
        "start" {
            docker compose up --build --detach
            if ($LASTEXITCODE -ne 0) {
                throw "Falha ao construir ou iniciar o container Docker."
            }
            docker compose exec -T notebook python -c "import tensorflow as tf; gpus = tf.config.list_physical_devices('GPU'); print('TensorFlow:', tf.__version__); print('GPUs:', gpus); assert gpus, 'Nenhuma GPU foi detectada pelo TensorFlow'; x = tf.random.normal((1024, 1024)); y = tf.matmul(x, x); print('Teste matricial:', y.device)"
            if ($LASTEXITCODE -ne 0) {
                throw "O container iniciou, mas a validação do TensorFlow/GPU falhou."
            }
            Write-Host "Jupyter Lab: http://localhost:8888/lab?token=eurosat"
        }
        "stop" {
            docker compose down
            if ($LASTEXITCODE -ne 0) { throw "Falha ao encerrar o container." }
        }
        "status" {
            docker compose ps
            if ($LASTEXITCODE -ne 0) { throw "Falha ao consultar o container." }
        }
        "logs" {
            docker compose logs --follow notebook
        }
        "gpu" {
            docker compose exec -T notebook nvidia-smi
            if ($LASTEXITCODE -ne 0) { throw "Falha ao consultar a GPU no container." }
        }
    }
}
finally {
    Pop-Location
}
