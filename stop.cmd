@echo off
chcp 65001 >nul
cd /d "%~dp0"
docker compose --profile local-llm stop
if errorlevel 1 exit /b 1
echo 服务已停止，数据库、上传文件、产物和模型数据均已保留。
