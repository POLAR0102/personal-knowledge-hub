# Docker 与腾讯云部署说明

## 1. 当前部署方案

系统使用两个容器：

```text
浏览器
  ↓ HTTP
Nginx + React（frontend）
  ↓ /api 内网转发
FastAPI + Uvicorn（backend）
  ├─ SQLite 持久化卷
  ├─ 上传文件持久化卷
  ├─ ChromaDB 持久化卷
  ├─ Embedding 模型缓存卷
  └─ 滚动日志卷
```

前端是唯一需要对外开放的入口。Compose 将后端 `8000` 端口绑定到 `127.0.0.1`，公网用户不能绕过 Nginx 直接访问后端。

## 2. 腾讯云服务器准备信息

真正上线时需要确认以下信息，但不要发送密码、私钥或 API Key：

- 服务器系统和版本，例如 Ubuntu 22.04/24.04
- Docker 与 `docker compose` 是否已安装
- 公网 IP
- 是否已有域名以及域名是否完成解析
- 希望使用临时端口 `8080`，还是正式的 `80/443`

正式使用 `80/443` 时，轻量应用服务器防火墙建议只开放：

- `22`：SSH，最好限制来源 IP
- `80`：HTTP
- `443`：HTTPS（配置域名证书后）

如果首次验收保留默认的 `FRONTEND_PORT=8080`，还需要临时开放 TCP `8080`；验收完成并切换到 `80` 后立即关闭。任何情况下都不需要向公网开放 `8000`、SQLite、ChromaDB 或其他内部端口。

## 3. 首次启动

在服务器克隆项目后进入项目根目录：

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

编辑 `.env`，至少设置：

```env
FRONTEND_PORT=8080
JWT_SECRET_KEY=刚才生成的随机值
CHAT_API_KEY=你的真实Chat模型Key
```

`CHAT_API_KEY` 可以暂时留空，此时注册、知识库、文档处理、索引和语义检索仍可运行，但 RAG 自然语言回答和 Agent 不能调用 Chat Model。

启动：

```bash
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
```

首次构建会下载 Python、Node、Nginx 依赖；首次建立文档索引还会下载本地 Embedding 模型，因此耗时比后续启动长。

检查：

```bash
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8080/healthz
docker compose logs --tail=100 backend
docker compose logs --tail=100 frontend
```

然后在浏览器访问 `http://服务器公网IP:8080`。确认功能后，可把 `FRONTEND_PORT` 改为 `80` 并重启：

```bash
docker compose up -d
```

## 4. HTTPS 与正式公网发布

IP 加端口适合首次验收，不适合长期公开使用。正式发布前还应：

1. 将域名解析到服务器公网 IP。
2. 配置可信 HTTPS 证书和自动续期。
3. 只保留 `80/443` 公网入口。
4. 使用高强度 JWT 密钥和独立的演示账号密码。
5. 确认 `.env` 没有进入 Git、日志或截图。
6. 做一次完整备份和恢复演练。

HTTPS 的具体配置取决于服务器系统、域名和证书方案，因此在拿到这些非敏感信息后再实施，不在当前 Compose 中猜测域名。

## 5. 演示数据（可选）

生产模式不会接受默认演示密码。可以通过不回显的 shell 变量输入临时密码：

```bash
read -s DEMO_PASSWORD
docker compose exec backend python -m scripts.seed_demo --password "$DEMO_PASSWORD"
unset DEMO_PASSWORD
```

登录后，在知识库详情中手动处理并索引演示文档。公网答辩结束后删除演示账号或更换密码。

## 6. 更新与回退

更新前先备份，然后执行：

```bash
git pull --ff-only
docker compose build
docker compose up -d
docker compose ps
```

数据库迁移由后端容器启动命令自动执行。若更新后异常，应先保留现场日志和数据卷，再切回已验证的 Git 提交重新构建；不要用 `docker compose down -v` 处理应用错误。

查看日志：

```bash
docker compose logs -f --tail=200
```

应用滚动日志还持久化在 `log_data` 卷的 `/data/logs/app.log`。
