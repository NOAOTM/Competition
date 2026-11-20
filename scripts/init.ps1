$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $root ".env"
$examplePath = Join-Path $root ".env.example"

if (-not (Test-Path $envPath)) {
    Copy-Item $examplePath $envPath
}

$content = Get-Content -Raw $envPath
if ($content -match "(?m)^SECRET_KEY=replace-me-first-time\.cmd-generates-a-random-key$") {
    $bytes = New-Object byte[] 48
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    $secret = [BitConverter]::ToString($bytes).Replace("-", "").ToLowerInvariant()
    $content = [regex]::Replace($content, "(?m)^SECRET_KEY=.*$", "SECRET_KEY=$secret")
    [System.IO.File]::WriteAllText($envPath, $content, (New-Object System.Text.UTF8Encoding($false)))
}

Write-Host "Local .env ready; generated secrets remain untracked."
