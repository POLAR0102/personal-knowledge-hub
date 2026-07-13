# Personal Knowledge Hub Frontend

“基于 RAG 与 Agent 的智能个人知识库系统”前端。当前已完成基础布局、用户认证、知识库管理、文档上传、解析和文本片段调试。

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

- `/`：受保护的 Dashboard，显示真实知识库和文档数量
- `/login`：登录页
- `/register`：注册页
- `/knowledge-bases`：受保护的知识库列表、分页、创建、编辑和删除
- `/knowledge-bases/:id`：受保护的知识库详情，以及文档上传、处理、删除和文本片段查看
- `/documents`：受保护的文档管理入口
- `/chat`：受保护的 AI 问答占位页
- `/agent`：受保护的 Agent 占位页
- `/notes`：受保护的笔记占位页

文档上传后状态为 `pending`（等待处理），用户可手动启动解析和文本切分。当前不包含 Embedding、向量数据库、RAG、AI 问答、Agent 或笔记业务逻辑。
