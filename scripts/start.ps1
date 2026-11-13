$ErrorActionPreference = "Stop"
docker compose up --build -d
Write-Host "Backend: http://localhost:8000/health"
Write-Host "Frontend: http://localhost:3000"
