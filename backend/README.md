# Personal Knowledge Hub API

“基于 RAG 与 Agent 的智能个人知识库系统”的 FastAPI 后端。当前版本仅完成 T01：应用初始化、环境变量、SQLite/SQLAlchemy 基础设施、Alembic 预留和健康检查。

## 环境要求

- Python 3.11

## 安装

在项目根目录执行：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

请在 `.env` 中将 `JWT_SECRET_KEY` 替换为本地生成的随机密钥。T01 尚未实现 JWT，但不要将真实密钥提交到 Git。

## 启动

```powershell
uvicorn app.main:app --reload
```

服务启动后可访问：

- 健康检查：<http://127.0.0.1:8000/api/v1/health>
- OpenAPI 文档：<http://127.0.0.1:8000/docs>

健康检查应返回：

```json
{
  "status": "ok",
  "service": "personal-knowledge-hub-api"
}
```

## 测试

```powershell
pytest
```

## 数据库迁移

Alembic 环境已预留。后续添加 SQLAlchemy 模型后，可创建并执行迁移：

```powershell
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

默认数据库为项目运行目录中的 `personal_knowledge_hub.db`。数据库文件和本地 `.env` 已被 Git 忽略。
