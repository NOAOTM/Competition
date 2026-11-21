90%的情况你只需要双击 start.cmd

# 真知 Agent v20

面向学习与科研的中文工作台。应用仅通过 Docker Compose 运行；本机无需安装 Python 或 Node.js。首次启动会在已运行的 Windows Ollama 与带持久模型卷的项目 Ollama 容器之间自动选择，并将选择保存在 `.env`，后续不会切换模型目录。本地模型不可用时会明确显示原因，不会返回伪造的 AI 结果。

## 第一次运行

1. 安装并启动 Docker Desktop。
2. 双击 `first-time.cmd`。脚本生成本机 `.env` 随机密钥、构建镜像并启动服务；会复用已选 Ollama 中已有的默认模型，仅在缺少时拉取 `deepseek-r1:7b`。首次下载模型需预留磁盘空间和时间。
3. 后续日常使用双击 `start.cmd`。重复运行安全，不执行 build、pip/npm 安装或数据清理。

首次模型下载失败时，运行 `model.cmd pull deepseek-r1:7b` 重试。学生证多模态认证还需手动运行 `model.cmd pull qwen2.5vl:7b`；它不会在首次安装时自动额外下载。

## Docker 命令

- `start.cmd`：首次启动时选择正在运行的 Windows Ollama 或项目 Ollama 容器并保存选择，之后始终使用同一个模型目录；等待应用健康检查后打开 `http://localhost:3000`。Windows Ollama 的 API 需可从 Docker Desktop 通过 `host.docker.internal:OLLAMA_PORT` 访问。切换来源时手动修改 `.env` 的 `OLLAMA_TARGET=auto|host|container`。
- `stop.cmd`：停止容器但保留数据库、上传件、结果和模型。
- `status.cmd`：查看运行状态；退出码 0/1/2 分别代表运行中/部分异常/停止。
- `logs.cmd [backend|frontend|ollama]`：查看全部或指定服务的最近 200 行日志并持续跟踪。
- `first-time.cmd`：首次安装或 Dockerfile/依赖变更后构建镜像。
- `model.cmd pull|list|ps|run`：管理本地模型。
- `reset.cmd`：输入 `YES` 二次确认后删除 Compose 数据卷；不可恢复。

开发 Compose 挂载源码并热加载。容器版 Ollama 不占用 Windows 的 11434 端口；模型保存在 `ollama_data` 卷。`model.cmd` 会对当前选定的 Ollama 执行模型管理。生产配置不挂载源码：

```powershell
docker compose -f docker-compose.prod.yml --profile local-llm up -d --build --wait
```

`.env` 由 `first-time.cmd` 从 `.env.example` 创建并被 Git 忽略。密钥、外部 API key 和学习通 Cookie 只能放在本机 `.env`，不得提交。服务容器间使用 `backend:8000` / `ollama:11434`；浏览器访问 `localhost`，Next.js 通过同源 `/api/*` rewrite 代理 API。

## 已实现功能

- 科研助手首页采用浅色绿系左侧导航、模型状态、任务输入、文件上传、功能/模型/分析模式选择、进度与错误提示。
- 文字工具（文献导读、研究设计、润色、翻译、知识前沿、逻辑图、数据分析、检索策略、写作提纲、学习计划）由 Ollama 或 OpenAI 兼容 API 真实生成。任务先进入后端后台队列，再由全局任务卡轮询进度；在科研助手、PS、日程等页面间切换不会中断或丢失任务。模型超时、连接失败或服务错误不会扣额度；成功请求会记账。LLM 有超时、网络与服务端错误重试、内存缓存和 `<think>` 清理。浏览器完整刷新或后端进程重启后，当前内存任务状态不保证恢复。
- PDF/DOCX/TXT 文献任务支持 PDF 文本布局排序、pdfplumber 回退、无文本时 Tesseract OCR、可配置分块和重要性截断；Pass 0 元数据、Pass 1 分块结构化提取、Pass 2 综合，并提供阶段进度轮询。产物包含知识 JSON、中文 Markdown、DOT/PNG 逻辑图、15 页 16:9 PPTX（含备注）、PPT 大纲和运行日志。缓存键包含文件 SHA-256、模型、上下文与提示版本；英文文献生成自动翻译节选。
- “创作伙伴 / 我的 PS”内嵌固定版本 PhotoCraft v0.23.1 Web 编辑器，提供其完整图像编辑工具，不跳转到外部站点。编辑在用户浏览器本地处理；保存/导出位置与格式由 PhotoCraft 控制，不会上传到真知 Agent，浏览器需支持 WebGPU 或 WebGL2。PhotoCraft 的 MIT 许可、NOTICE 与素材归属文件随镜像提供。
- CSV/XLSX 图表：字段预览、折线/柱/饼/散点/3D 散点并导出 PNG。
- 文献库通过 OpenAlex 公共目录检索实际书目与摘要，支持主题快捷检索、摘要筛选、浏览器本地收藏、CSV 导出与 Open Knowledge Maps 主题地图入口。
- 知识前沿以博客式信息流展示 OpenAlex 的真实论文与来源摘要，不伪装成实时新闻或生成的研究结论。
- 美食页通过 OpenStreetMap 地理编码与 Overpass 返回附近餐馆，以真实地点卡片展示距离、可获得的价位与地图入口；不编造评分或商家照片。
- 日程支持 CSV/XLSX 课表导入、周视图、手动提醒与删除。
- 账户支持手机号、算术验证码、开发模式演示短信码、签到、额度，以及将学生证图片发给配置的视觉模型进行类别/姓名/学校/修图痕迹审核。管理员通过 `.env` 的 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 初始化，支持查用户、启停与调额度。
- `/api/v1/system/llm-health` 返回 provider、模型列表、连通性和中文错误提示。

## 模型配置

默认 `OLLAMA_PROVIDER=ollama`，模型为 `deepseek-r1:7b`，上下文 `OLLAMA_NUM_CTX=8192`，长请求超时 360 秒。可在 `.env` 改 `OLLAMA_MODEL`、`OLLAMA_NUM_CTX`。如需云端 OpenAI 兼容服务，显式设置 `OLLAMA_PROVIDER=openai`、`OPENAI_BASE_URL`、`OPENAI_MODEL` 和 `OPENAI_API_KEY`；凭据不会暴露给浏览器。

## API 与持久化

- `GET /health`、`GET /api/v1/system/llm-health`
- `/api/v1/auth/login`、`/api/v1/account/*`
- `POST /api/v1/tools/tasks`、`GET /api/v1/tools/tasks/{task_id}` 与兼容同步工具路由 `/api/v1/tools/run`
- `POST /api/v1/agent/research`、`GET /api/v1/agent/progress/{task_id}`、`GET /api/v1/download/{file_id}`
- `/api/v1/chart/*`、`/api/v1/library/*`、`/api/v1/food/*`、`/api/v1/schedule/*`、`/api/v1/admin/*`

Compose 命名卷 `db_data`、`app_output`、`app_uploads`、`app_logs`、`ollama_data` 保存数据库、产物、上传文件、日志和模型；容器均为 `restart: "no"`，系统/ Docker 重启后不会自动拉起。默认 dev compose 将前后端源码挂载用于热更新。

`photocraft` 静态服务由 `first-time.cmd` 与前端一起构建，项目附带 PhotoCraft v0.23.1 官方 Web 发布包并在构建时校验 SHA-256。更新此发布版本或其 Dockerfile 后重新运行 `first-time.cmd`；日常 `start.cmd` 不会构建或下载发布包。

## 当前限制与验证边界

- Open Knowledge Maps 没有接入未公开 API；书目检索与导出由 OpenAlex 实际提供，知识地图入口链接到其站点。
- PhotoCraft 在浏览器端运行，项目不会接收或持久化其工作区文件；WebGPU/WebGL2 能力取决于用户浏览器和设备。
- 扫描表格尚未自动转成数据列；图表目前接受 CSV/XLSX。扫描 PDF 文献 OCR 依赖容器内 Tesseract 中文语言包。
- 学习通同步需本机配置有效 `CHAOXING_COOKIE`。当前只尝试读取登录页内可识别的截止日期，不会把未确认结果自动写成提醒；复杂课程页面可能需要人工核对。
- 短信目前仅在 `APP_ENV=development` 输出演示码；生产环境未配置 SMS 服务商时会返回明确 503。
- 文献质量门禁只发警告；Pass 3 审稿自检与 Pass 4 修订未默认实现。英文翻译是节选，不承诺覆盖整篇长文。视觉学生证认证要求另外拉取多模态模型，且模型判断需人工复核。
- 外部 OpenAlex、OpenStreetMap/Overpass、学习通服务和真实 Ollama 推理依赖网络/用户凭据，未连接或凭据缺失时会显示错误；本次不会用示例结果代替真实结果。
