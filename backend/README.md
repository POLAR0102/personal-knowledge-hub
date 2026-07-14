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
