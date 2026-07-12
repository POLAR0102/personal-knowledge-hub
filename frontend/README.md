# Personal Knowledge Hub Frontend

“基于 RAG 与 Agent 的智能个人知识库系统”前端。当前阶段完成 React、TypeScript、Vite、Tailwind CSS、React Router、Axios 和 Zustand 的基础初始化。

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

## 当前页面

- `/`：首页 Dashboard，并检查后端健康状态
- `/login`：登录占位页
- `/register`：注册占位页
- `/knowledge-bases`：知识库占位页
- `/documents`：文档占位页
- `/chat`：AI 问答占位页
- `/agent`：Agent 占位页
- `/notes`：笔记占位页

当前不包含认证、知识库、文档处理、RAG 或 Agent 业务逻辑。
