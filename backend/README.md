# Personal Knowledge Hub API

“基于 RAG 与 Agent 的智能个人知识库系统”的 FastAPI 后端。当前已完成用户认证、知识库 CRUD、文档处理、本地向量索引、语义检索、带真实引用和历史记录的 RAG 问答，以及固定工作流 Agent 和 Markdown 笔记。

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
- 当前仍不支持扫描版 PDF OCR 和完全自主 Agent

## Agent 与笔记

- Agent 支持知识总结、学习计划和主题笔记三种固定任务
- 每个任务只调用知识库语义检索和 Chat Model，不开放外部工具或代码执行
- 结果保存为 Markdown，并持久化真实引用快照和任务状态
- 失败任务可以重试；同一任务重复保存笔记不会产生重复记录
- 笔记支持手动创建、编辑、删除和按知识库筛选

## DeepSeek API Key

DeepSeek 官方 Key 只用于 RAG 回答，不用于文档 Embedding。当前索引使用本地模型，因此不要把 DeepSeek Key 填入 `AI_API_KEY`。

在被 Git 忽略的 `.env` 中配置：

```env
CHAT_API_KEY=replace-with-your-new-deepseek-api-key
CHAT_BASE_URL=https://api.deepseek.com
CHAT_MODEL=deepseek-v4-flash
```

真实 DeepSeek Key 不能写入 `.env.example`，也不要发送到前端或日志。后端使用独立的 `CHAT_*` 配置，避免与 Embedding 配置混用。

问答会话会保存用户消息、AI 回答和当时的引用快照。当前每条问题仍独立执行 RAG，历史消息暂不加入下一轮 Prompt。

切换 Embedding 模型后，必须重新为已有文档建立索引，不能混用不同维度或不同模型生成的向量。

## 文档组织

- `GET /api/v1/documents`：跨知识库分页查询当前用户文档，支持 `filename`、`status`、`knowledge_base_id`、`tag_id` 和 `is_favorite` 组合筛选。
- `GET /api/v1/documents/favorites`：查询当前用户收藏的文档，并支持相同的辅助筛选条件。
- `PUT /api/v1/documents/{document_id}/favorite`：显式设置收藏状态，重复请求不会反转结果。
- `POST /api/v1/documents/{document_id}/tags/{tag_id}` 和对应 `DELETE`：添加或移除文档标签。
- `/api/v1/tags` 提供当前用户私有标签的创建、分页列表、详情、修改和删除接口。

标签名称长度为 1 到 30 个字符，并在同一用户内保持唯一。所有文档、知识库和标签筛选都校验当前用户归属。

## 日志

后端始终向控制台输出日志，默认级别为 `INFO`。如需保留滚动日志，在 `.env` 中配置：

```env
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5
```

单个日志文件达到 `LOG_MAX_BYTES` 后自动轮转，最多保留 `LOG_BACKUP_COUNT` 个历史文件。日志不会主动记录 API Key、JWT 或完整文档正文。

## 演示数据

先执行 `alembic upgrade head`，再在 `backend` 目录运行：

```powershell
python -m scripts.seed_demo
```

开发环境默认创建以下本地演示数据：

- 账号：`demo@example.com`
- 密码：`Demo123456!`
- 一个知识库和一份状态为 `pending` 的 Markdown 演示文档

脚本可以重复执行，不会重复创建记录，也不会重置已存在账号的密码。登录后请在知识库详情中依次点击“开始处理”和“建立索引”，即可用于语义检索、RAG 与 Agent 演示。

演示账号只应用于本地答辩环境。公网部署前必须删除该账号或修改密码；当 `APP_ENV=production` 时，脚本拒绝使用默认密码，必须显式执行：

```powershell
python -m scripts.seed_demo --password "your-explicit-demo-password"
```

## 数据备份与恢复

SQLite、上传文件和 ChromaDB 共同构成一份完整数据。为保证三个组件处于同一时间点，执行备份前应停止后端服务或至少暂停上传、索引和删除操作：

```powershell
python -m scripts.backup_data
```

脚本使用 SQLite 在线备份 API 创建一致的数据库副本，并将 `UPLOAD_DIR` 和 `CHROMA_PERSIST_DIR` 复制到 `./backups/<UTC时间>/`。每份备份包含 `manifest.json`，但不会复制 `.env`、API Key 或模型缓存。

可通过参数指定备份根目录，命令在 Windows 和 Linux 上相同：

```powershell
python -m scripts.backup_data --output-dir D:/knowledge-backups
```

恢复步骤：

1. 停止后端服务。
2. 先备份或移走当前数据库、上传目录和 Chroma 目录。
3. 将备份中的 `database.sqlite3` 放回 `DATABASE_URL` 对应位置。
4. 将 `uploads/` 和 `chroma/` 分别放回 `UPLOAD_DIR` 与 `CHROMA_PERSIST_DIR`。
5. 启动后端并检查健康接口、文档文件和索引健康状态。

建议每天定时备份并至少保留最近 7 份；备份目录应放在项目目录之外或独立磁盘。当前脚本只支持 SQLite，未来切换 PostgreSQL 后应使用 `pg_dump`，上传文件和 ChromaDB 仍按相同停写策略备份。
