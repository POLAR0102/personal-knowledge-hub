# Personal Knowledge Hub Frontend

“基于 RAG 与 Agent 的智能个人知识库系统”前端。当前已完成用户认证、知识库管理、文档处理、向量索引、语义检索、带历史记录的 RAG 问答，以及轻量 Agent 和 Markdown 笔记。

## 环境要求

- Node.js 20 或更高版本
- npm 10 或更高版本
- FastAPI 后端运行在 `http://127.0.0.1:8000`

## 安装

在项目根目录执行：

```powershell
cd frontend
npm install
Copy-Item .env.example .env
```

## 启动

先启动后端，再启动前端：

```powershell
npm run dev
```

访问 <http://localhost:5173>。

## 构建检查

```powershell
npm run build
```

## 认证流程

- 注册成功后跳转登录页
- 登录成功后在浏览器本地保存 Access Token
- Axios 自动为请求添加 Bearer Token
- 应用启动时通过 `/auth/me` 恢复用户状态
- Token 无效或过期时自动清除登录状态并返回登录页
- 退出登录会清除本地 Token

Token 只用于请求认证，不会显示在页面中。

## 当前页面

- `/`：受保护的 Dashboard，显示真实知识库、文档、笔记和问答会话数量
- `/login`：登录页
- `/register`：注册页
- `/knowledge-bases`：受保护的知识库列表、分页、创建、编辑和删除
- `/knowledge-bases/:id`：受保护的知识库详情，以及文档上传、处理、删除和文本片段查看
- `/documents`：受保护的文档管理入口
- `/chat`：受保护的问答会话页，可新建、切换和删除会话，并查看历史消息与引用快照
- `/agent`：受保护的轻量 Agent 页，可执行资料总结、学习计划和主题笔记任务
- `/notes`：受保护的 Markdown 笔记页，可管理手动或 Agent 生成的笔记

文档上传后状态为 `pending`（等待处理），用户可手动完成解析、文本切分和向量索引。问答会将问题发送到后端，由本地 Embedding 检索相关片段，再由后端 Chat Model 生成带真实引用的回答。会话、消息和引用快照会保存到数据库，刷新后可恢复；当前历史消息尚不参与下一轮 RAG Prompt。Agent 使用固定、可说明的系统工作流执行知识任务，已完成结果可幂等保存为笔记。
