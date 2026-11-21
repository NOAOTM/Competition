@echo off
chcp 65001 >nul
cd /d "%~dp0"
if "%~1"=="" goto help
set OLLAMA_MODE=container
for /f %%M in ('powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\detect-ollama.ps1"') do set OLLAMA_MODE=%%M
if /i "%OLLAMA_MODE%"=="host-unavailable" (
  echo [错误] .env 选择复用本机 Ollama，但本机 Ollama 当前未运行。请启动 Ollama 后重试。
  exit /b 1
)
if /i "%OLLAMA_MODE%"=="host" (
  where ollama >nul 2>nul
  if errorlevel 1 (
    echo [错误] 已连接本机 Ollama，但找不到 ollama 命令。请将 Ollama 安装目录加入 PATH。
    exit /b 1
  )
)
if /i "%~1"=="pull" goto pull
if /i "%~1"=="list" goto list
if /i "%~1"=="ps" goto ps
if /i "%~1"=="run" goto run
if /i "%~1"=="delete" goto delete_model
echo 支持的操作：pull [模型名]、list、ps、run [模型名]、delete [模型名]
exit /b 2

:pull
set MODEL=%~2
if "%MODEL%"=="" set MODEL=deepseek-r1:7b
if /i "%OLLAMA_MODE%"=="host" (
  ollama pull "%MODEL%"
) else (
  docker compose --profile local-llm up -d ollama
  if errorlevel 1 exit /b 1
  docker compose --profile local-llm exec -T ollama ollama pull "%MODEL%"
)
exit /b %errorlevel%

:list
if /i "%OLLAMA_MODE%"=="host" (
  ollama list
) else (
  docker compose --profile local-llm exec -T ollama ollama list
)
exit /b %errorlevel%

:ps
if /i "%OLLAMA_MODE%"=="host" (
  ollama ps
) else (
  docker compose --profile local-llm exec -T ollama ollama ps
)
exit /b %errorlevel%

:run
set MODEL=%~2
if "%MODEL%"=="" set MODEL=deepseek-r1:7b
if /i "%OLLAMA_MODE%"=="host" (
  ollama run "%MODEL%"
) else (
  docker compose --profile local-llm exec ollama ollama run "%MODEL%"
)
exit /b %errorlevel%

:delete_model
if "%~2"=="" (
  echo 用法：model.cmd delete 模型名
  exit /b 2
)
if /i "%OLLAMA_MODE%"=="host" (
  ollama rm "%~2"
) else (
  docker compose --profile local-llm exec -T ollama ollama rm "%~2"
)
exit /b %errorlevel%

:help
echo 用法：model.cmd pull [模型名] ^| list ^| ps ^| run [模型名] ^| delete 模型名
exit /b 2
