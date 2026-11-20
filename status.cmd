@echo off
chcp 65001 >nul
cd /d "%~dp0"
docker compose --profile local-llm ps
docker compose --profile local-llm ps --status running -q | findstr . >nul
if errorlevel 1 (
  echo 状态：已停止或未启动
  exit /b 2
)
docker compose --profile local-llm ps --status exited -q | findstr . >nul
if not errorlevel 1 (
  echo 状态：部分服务异常，请运行 logs.cmd 查看日志
  exit /b 1
)
echo 状态：服务正在运行
exit /b 0
