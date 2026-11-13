$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force data | Out-Null
if (-not (Test-Path .env) -and (Test-Path .env.example) ) { Copy-Item .env.example .env }
python -m pip install -r backend/requirements.txt
Push-Location backend
python -m alembic upgrade head
Pop-Location
Write-Host "真知 Agent 初始化完成。"
