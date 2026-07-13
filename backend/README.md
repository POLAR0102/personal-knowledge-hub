# Personal Knowledge Hub API

“基于 RAG 与 Agent 的智能个人知识库系统”的 FastAPI 后端。当前已完成用户认证、知识库 CRUD、文档处理、本地向量索引、语义检索和带真实引用的单轮 RAG 问答。

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

默认使用 `BAAI/bge-small-zh-v1.5` 本地模型生成 Embedding，不需要 Embedding API Key。第一次建立索引时会下载约 90MB 的模型到 `LOCAL_EMBEDDING_CACHE_DIR=./model_cache`，之后可以直接使用本地缓存。

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
- 本地 Embedding 写入持久化 ChromaDB，支持重复索引、索引健康检查和按用户、知识库隔离的语义检索
- RAG 问答只使用检索到的上下文，并根据模型返回的来源编号映射真实文档引用
- 当前仍不支持扫描版 PDF OCR、聊天历史、Agent 和笔记生成

## DeepSeek API Key

DeepSeek 官方 Key 只用于 RAG 回答，不用于文档 Embedding。当前索引使用本地模型，因此不要把 DeepSeek Key 填入 `AI_API_KEY`。

在被 Git 忽略的 `.env` 中配置：

```env
CHAT_API_KEY=replace-with-your-new-deepseek-api-key
CHAT_BASE_URL=https://api.deepseek.com
CHAT_MODEL=deepseek-v4-flash
```

真实 DeepSeek Key 不能写入 `.env.example`，也不要发送到前端或日志。后端使用独立的 `CHAT_*` 配置，避免与 Embedding 配置混用。

当前问答接口为单轮调用，不保存历史会话；会话持久化将在后续阶段实现。

切换 Embedding 模型后，必须重新为已有文档建立索引，不能混用不同维度或不同模型生成的向量。
