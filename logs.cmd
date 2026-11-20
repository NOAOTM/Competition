@echo off
chcp 65001 >nul
cd /d "%~dp0"
if "%~1"=="" (
  docker compose --profile local-llm logs --tail=200 --follow
  exit /b %errorlevel%
)
if /i "%~1"=="backend" goto selected
if /i "%~1"=="frontend" goto selected
if /i "%~1"=="ollama" goto selected
echo 用法：logs.cmd [backend^|frontend^|ollama]
exit /b 2
:selected
docker compose --profile local-llm logs --tail=200 --follow "%~1"
exit /b %errorlevel%
