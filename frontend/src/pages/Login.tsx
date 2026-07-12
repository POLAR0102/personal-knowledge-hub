import { Link } from 'react-router-dom'

export function Login() {
  return (
    <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <p className="text-sm font-medium text-indigo-600">欢迎回来</p>
      <h1 className="mt-2 text-2xl font-semibold text-slate-900">登录账户</h1>
      <p className="mt-2 text-sm text-slate-500">登录功能将在下一阶段接入。</p>
      <div className="mt-7 space-y-4">
        <label className="block text-sm font-medium text-slate-700">
          邮箱
          <input
            type="email"
            placeholder="name@example.com"
            className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 outline-none focus:border-indigo-400"
          />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          密码
          <input
            type="password"
            placeholder="请输入密码"
            className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 outline-none focus:border-indigo-400"
          />
        </label>
        <button
          type="button"
          disabled
          className="w-full cursor-not-allowed rounded-xl bg-indigo-500 px-4 py-3 text-sm font-semibold text-white opacity-60"
        >
          登录功能尚未开放
        </button>
      </div>
      <p className="mt-6 text-center text-sm text-slate-500">
        还没有账户？{' '}
        <Link to="/register" className="font-medium text-indigo-600">
          前往注册页
        </Link>
      </p>
      <Link to="/" className="mt-4 block text-center text-xs text-slate-400">
        返回演示首页
      </Link>
    </section>
  )
}
