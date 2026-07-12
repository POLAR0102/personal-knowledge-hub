import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/auth'
import { getApiErrorMessage } from '../utils/api-error'

interface LoginLocationState {
  from?: string
  message?: string
}

export function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const login = useAuthStore((state) => state.login)
  const locationState = location.state as LoginLocationState | null
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      await login({ email, password })
      navigate(locationState?.from ?? '/', { replace: true })
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '登录失败，请检查输入信息'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <p className="text-sm font-medium text-indigo-600">欢迎回来</p>
      <h1 className="mt-2 text-2xl font-semibold text-slate-900">登录账户</h1>
      <p className="mt-2 text-sm text-slate-500">
        登录后访问你的知识库与智能工具。
      </p>

      {locationState?.message && (
        <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {locationState.message}
        </div>
      )}
      {error && (
        <div
          role="alert"
          className="mt-5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
        >
          {error}
        </div>
      )}

      <form className="mt-7 space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm font-medium text-slate-700">
          邮箱
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            required
            placeholder="name@example.com"
            className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 outline-none transition focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100"
          />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          密码
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            minLength={6}
            required
            placeholder="请输入密码"
            className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 outline-none transition focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100"
          />
        </label>
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? '正在登录…' : '登录'}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        还没有账户？{' '}
        <Link to="/register" className="font-medium text-indigo-600">
          创建账户
        </Link>
      </p>
    </section>
  )
}
