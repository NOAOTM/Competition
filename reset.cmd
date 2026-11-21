@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 下列 Docker 卷将被永久删除：
docker volume ls
echo 这会删除数据库、上传文件、导出产物和 Ollama 模型。
set /p CONFIRM=输入 YES 继续：
if /i not "%CONFIRM%"=="YES" (
  echo 已取消。
  exit /b 1
)
docker compose --profile local-llm down --volumes
if errorlevel 1 exit /b 1
echo 项目数据卷已删除。
