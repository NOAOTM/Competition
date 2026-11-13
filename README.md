# 真知 Agent

面向大学生的学习与科研助手。仓库保留早期 Streamlit 原型 `app.py`，当前可运行主架构为 FastAPI + SQLAlchemy + Next.js。

## 已实现

- Phase 1：Docker Compose、FastAPI 配置/数据库/模型/JWT 认证、SQLAlchemy 与 Alembic 初始迁移、Next.js 前端骨架、启动/停止/初始化脚本、`.env.example`。
- Phase 2：每日签到（+10 额度）、学校认证材料上传、额度扣减与记录、文献导读、学术润色、翻译 API。
- 健康检查：`GET /health`；API 前缀为 `/api/v1`。

## 本地运行

```powershell
Copy-Item .env.example .env
.\scripts\init.ps1
docker compose up --build
```

后端默认在 `http://localhost:8000`，前端默认在 `http://localhost:3000`。不要把真实密钥提交到仓库。

## API

注册 `POST /api/v1/auth/register`，登录 `POST /api/v1/auth/login`，当前用户 `GET /api/v1/account/me`，签到 `POST /api/v1/account/check-in`，认证上传 `POST /api/v1/account/verification`，以及 `/api/v1/tools/literature-guide`、`/polish`、`/translate`。工具接口使用 Bearer token，并按 10/5/5 额度扣减。

## 验证

```powershell
python -m compileall backend/app
docker compose config
```