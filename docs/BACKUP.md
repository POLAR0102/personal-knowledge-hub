# 数据备份与恢复策略

## 1. 必须一起保护的数据

一份可恢复的系统备份由三部分组成：

1. SQLite：用户、知识库、文档记录、Chunk、会话、Agent 和笔记等结构化数据。
2. `UPLOAD_DIR`：用户上传的原始文件。
3. `CHROMA_PERSIST_DIR`：文档 Chunk 对应的持久化向量。

只复制 SQLite 不算完整备份；只复制 Chroma 也无法恢复业务记录。`.env` 和 API Key 不进入备份包，应由管理员通过独立的秘密管理方式保存。

## 2. 本地备份

为了让 SQLite、上传文件和向量处于同一业务时间点，先停止后端，或者至少暂停上传、处理、索引和删除操作，然后在 `backend` 目录执行：

```powershell
.\.venv\Scripts\python.exe -m scripts.backup_data --output-dir D:\knowledge-backups
```

脚本使用 SQLite 官方在线备份接口，而不是直接复制正在写入的数据库文件。输出目录示例：

```text
20260714T120000000000Z/
├─ database.sqlite3
├─ uploads/
├─ chroma/
└─ manifest.json
```

`manifest.json` 记录备份时间和实际包含的组件，不包含密码或 Key。

## 3. Docker 环境备份

安排一个短暂维护窗口：

```bash
docker compose stop backend
docker compose run --rm --no-deps backend python -m scripts.backup_data --output-dir /backups
docker compose start backend
docker compose cp backend:/backups/. ./backups
```

备份首先写入 `backup_data` 命名卷，再把卷内内容复制到宿主机。完成后应将宿主机备份再复制到腾讯云对象存储、另一台机器或其他独立介质；备份与服务器放在同一块云盘上不能防止整机故障。如果上传目录或 Chroma 目录尚不存在，命令会输出警告并在 `manifest.json` 中将对应组件记为 `null`，归档前应确认这确实代表系统尚无该类数据。

## 4. 建议周期

- 每天至少一次自动备份。
- 重大升级、迁移和演示前额外备份。
- 至少保留最近 7 份每日备份，并保留一份月度备份。
- 定期检查剩余磁盘空间。
- 每月至少做一次恢复演练，未验证的备份不能视为可靠。

## 5. 恢复步骤

恢复会替换当前数据，必须在维护窗口执行：

1. 停止后端，确认没有上传、索引或删除请求。
2. 再备份当前现场，避免误操作后无法回退。
3. 核对备份中的 `manifest.json`，确认数据库、上传文件和 Chroma 均存在。
4. 将 `database.sqlite3` 恢复到 `DATABASE_URL` 指向的位置。
5. 将 `uploads/` 恢复到 `UPLOAD_DIR`。
6. 将 `chroma/` 恢复到 `CHROMA_PERSIST_DIR`。
7. 保留服务器当前 `.env`，不要用备份覆盖密钥。
8. 启动系统并检查健康接口、登录、文档文件和索引健康状态。
9. 对一个已索引知识库执行语义搜索和带引用问答，确认 SQLite 与 Chroma 对应。

容器环境中的具体恢复命令涉及覆盖命名卷，执行前必须再次确认目标卷和备份时间。本项目目前提供经过测试的备份脚本，但刻意不提供“一键覆盖”恢复脚本，以避免选错备份时自动破坏现有数据。

## 6. 故障判断

- 数据库存在、原文件丢失：列表仍可见，但重新处理会失败，应恢复上传目录。
- Chunk 存在、向量丢失：索引健康检查会显示向量缺失，可在确认原文件和 Chunk 正常后重新索引。
- Embedding 模型变化：健康检查会提示模型不匹配，应重新索引，不能混用旧向量。
- Chat API 不可用：不影响已保存数据和语义检索，修复配置后可重新问答或重试 Agent 任务。
