$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$port = 11434
$target = "auto"
foreach ($line in Get-Content (Join-Path $root ".env")) {
    if ($line -match "^OLLAMA_PORT=(\d+)$") {
        $port = [int]$matches[1]
    }
    if ($line -match "^OLLAMA_TARGET=(host|container|auto)$") {
        $target = $matches[1]
    }
}

if ($target -eq "host" -or $target -eq "auto") {
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/tags" -TimeoutSec 3
        if ($null -ne $response.models) {
            $selected = "host"
        } elseif ($target -eq "host") {
            Write-Output "host-unavailable"
            exit 1
        } else {
            $selected = "container"
        }
    } catch {
        if ($target -eq "host") {
            Write-Output "host-unavailable"
            exit 1
        }
        $selected = "container"
    }
} else {
    $selected = "container"
}

if ($target -eq "auto") {
    $envPath = Join-Path $root ".env"
    $content = Get-Content -Raw $envPath
    if ($content -match "(?m)^OLLAMA_TARGET=") {
        $content = [regex]::Replace($content, "(?m)^OLLAMA_TARGET=.*$", "OLLAMA_TARGET=$selected")
    } else {
        $content = $content.TrimEnd() + [Environment]::NewLine + "OLLAMA_TARGET=$selected" + [Environment]::NewLine
    }
    [System.IO.File]::WriteAllText($envPath, $content, (New-Object System.Text.UTF8Encoding($false)))
}

Write-Output $selected
