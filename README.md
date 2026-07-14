# 智能个人知识库系统

本科毕业设计项目“基于 RAG 与 Agent 的智能个人知识库系统”。系统已经形成完整业务闭环：用户认证、知识库、文档上传与解析、文本切分、向量索引、语义检索、带真实引用的 RAG 问答、会话历史、固定工作流 Agent、Markdown 笔记，以及文档标签、收藏和组合搜索。

## 技术栈

- 后端：Python 3.11、FastAPI、SQLAlchemy 2、Alembic、SQLite、ChromaDB、pytest
- 前端：React、TypeScript、Vite、React Router、Axios、Zustand、Tailwind CSS
- AI：本地 Embedding、OpenAI 兼容 Chat API（当前默认 DeepSeek 配置）
- 部署：Docker Compose、Nginx、Uvicorn

## 项目结构

```text
backend/              FastAPI、数据库迁移、测试和维护脚本
frontend/             React 前端和 Nginx 配置
docs/                 部署、备份和答辩演示说明
docker-compose.yml    前后端容器编排和持久化卷
.env.example          Docker Compose 环境变量模板
```

## 本地开发运行

需要两个 PowerShell 窗口。

窗口一启动后端：

```powershell
cd C:\Users\polar\Documents\knowledge\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

首次使用前，请在 `backend/.env` 中设置随机的 `JWT_SECRET_KEY`。需要 RAG 回答和 Agent 时，再设置 `CHAT_API_KEY`；真实 Key 不得提交到 Git，也不要发到聊天或截图中。

窗口二启动前端：

```powershell
cd C:\Users\polar\Documents\knowledge\frontend
npm install
Copy-Item .env.example .env
npm run dev
```

访问地址：

- 前端：<http://127.0.0.1:5173>
- 后端健康检查：<http://127.0.0.1:8000/api/v1/health>
- 后端接口文档：<http://127.0.0.1:8000/docs>

## Docker Compose 运行

Docker 运行使用根目录 `.env`，与本地开发使用的 `backend/.env` 不是同一个文件。

```powershell
cd C:\Users\polar\Documents\knowledge
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

把命令输出填入根目录 `.env` 的 `JWT_SECRET_KEY`。如需真实 RAG/Agent，再填写 `CHAT_API_KEY`。随后执行：

```powershell
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
```

默认访问 <http://127.0.0.1:8080>。Nginx 会把浏览器的 `/api` 请求转发给后端；后端端口只绑定到服务器本机，避免直接暴露到公网。

数据保存在 Docker 命名卷中：

- `database_data`：SQLite
- `upload_data`：上传的原始文件
- `chroma_data`：ChromaDB 向量
- `model_cache`：本地 Embedding 模型缓存
- `log_data`：滚动日志
- `backup_data`：容器内备份

停止服务时不要执行 `docker compose down -v`，`-v` 会删除这些数据卷。

## 自动化验证

后端完整测试：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

核心 E2E 测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_e2e_core_flow.py
```

该 E2E 通过真实 FastAPI 路由验证“注册 → 登录 → 创建知识库 → 上传 → 处理 → 索引 → RAG 问答与引用 → Agent → 保存笔记”。外部 AI 和向量服务使用确定性测试替身，因此测试不会消耗 API 额度，也不依赖公网。

前端检查：

```powershell
cd ..\frontend
npm run lint
npm run build
```

## 演示数据

本地开发环境可在迁移后执行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.seed_demo
```

脚本创建一个演示账号、知识库和状态为 `pending` 的 Markdown 文档，不会伪造 Chunk 或向量。登录后仍需在页面中依次点击“开始处理”和“建立索引”，这样答辩时能真实展示数据流程。脚本可重复执行，不会重复生成记录。

默认演示账号只允许用于本地环境，公网部署前必须删除或修改密码。生产环境运行脚本时必须显式提供密码。

## 运维入口

- 部署与腾讯云准备：[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- 数据备份与恢复：[docs/BACKUP.md](docs/BACKUP.md)
- 答辩演示流程：[docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md)
- 后端详细说明：[backend/README.md](backend/README.md)
- 前端详细说明：[frontend/README.md](frontend/README.md)

当前首版的明确边界：扫描版 PDF 不做 OCR；Agent 只执行固定工作流，不访问互联网、不执行代码；Chat Model 不可用时语义检索仍可运行，但 RAG 回答和 Agent 生成会失败并显示明确错误。
