$ModelDir = "C:\Projects\ProductFlow AI\models"
$ModelFile = Join-Path $ModelDir "smollm2-135m.gguf"
$Url = "https://huggingface.co/bartowski/SmolLM2-135M-GGUF/resolve/main/SmolLM2-135M-Q4_K_M.gguf"

if (Test-Path $ModelFile) {
    Write-Host "Model already exists at $ModelFile"
    exit 0
}

if (-not (Test-Path $ModelDir)) {
    New-Item -ItemType Directory -Path $ModelDir -Force | Out-Null
}

Write-Host "Downloading SmolLM2-135M GGUF (Q4_K_M)..."
Write-Host "URL: $Url"
Write-Host "This may take a while on a Pi Zero 2 W."

$ProgressPreference = 'SilentlyContinue'
try {
    Invoke-WebRequest -Uri $Url -OutFile $ModelFile -UseBasicParsing
    Write-Host "Model downloaded to $ModelFile"
} catch {
    Write-Host "Download failed. Try manually:"
    Write-Host "curl -L -o $ModelFile $Url"
    exit 1
}
