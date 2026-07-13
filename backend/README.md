# Personal Knowledge Hub API

“基于 RAG 与 Agent 的智能个人知识库系统”的 FastAPI 后端。当前已完成用户认证、知识库 CRUD 和文档上传管理基础。

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

请在 `.env` 中将 `JWT_SECRET_KEY` 替换为本地生成的随机密钥。不要将真实密钥提交到 Git。

文档默认保存在 `UPLOAD_DIR=./uploads`，单文件大小由 `MAX_UPLOAD_SIZE_MB=20` 控制。

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
pytest -q
```

## 数据库迁移

执行已有迁移：

```powershell
alembic upgrade head
```

默认数据库为项目运行目录中的 `personal_knowledge_hub.db`。数据库文件和本地 `.env` 已被 Git 忽略。

## 文档管理

- 支持 TXT、Markdown、PDF 和 DOCX
- 单文件最大 20MB
- 上传后初始状态为 `pending`
- 文件使用随机名称保存，公开响应不暴露磁盘路径
- 用户可手动启动 TXT、Markdown、文本型 PDF 和 DOCX 解析
- 解析成功后生成带页码、标题和 offset 的文本片段
- 重复处理会替换旧片段，不会累积重复数据
- 当前阶段不执行 OCR、Embedding、向量存储或 RAG
