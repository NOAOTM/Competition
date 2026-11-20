$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$ports = @{ FRONTEND_PORT = 3000; BACKEND_PORT = 8000 }
foreach ($line in Get-Content (Join-Path $root ".env")) {
    if ($line -match "^(FRONTEND_PORT|BACKEND_PORT)=(\d+)$") {
        $ports[$matches[1]] = [int]$matches[2]
    }
}
foreach ($entry in $ports.GetEnumerator()) {
    $listeners = Get-NetTCPConnection -LocalPort $entry.Value -State Listen -ErrorAction SilentlyContinue
    if ($listeners) {
        Write-Output ("Port {0} ({1}) is already in use by PID {2}." -f $entry.Value, $entry.Key, ($listeners[0].OwningProcess))
        exit 1
    }
}
exit 0
