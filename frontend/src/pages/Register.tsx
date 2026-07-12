import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { registerUser } from '../api/auth'
import { getApiErrorMessage } from '../utils/api-error'

export function Register() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError('两次输入的密码不一致')
      return
    }

    setIsSubmitting(true)
    try {
      await registerUser({
        username,
        email,
        password,
        confirm_password: confirmPassword,
      })
      navigate('/login', {
        replace: true,
        state: { message: '注册成功，请使用新账户登录' },
      })
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '注册失败，请检查输入信息'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <p className="text-sm font-medium text-indigo-600">创建账户</p>
      <h1 className="mt-2 text-2xl font-semibold text-slate-900">注册账户</h1>
      <p className="mt-2 text-sm text-slate-500">
        创建账户，开始管理你的个人知识。
      </p>

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
          用户名
          <input
            type="text"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            minLength={2}
            maxLength={30}
            required
            placeholder="2 到 30 个字符"
            className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 outline-none transition focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100"
          />
        </label>
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
            autoComplete="new-password"
            minLength={6}
            required
            placeholder="至少 6 个字符"
            className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 outline-none transition focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100"
          />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          确认密码
          <input
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            autoComplete="new-password"
            minLength={6}
            required
            placeholder="再次输入密码"
            className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 outline-none transition focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100"
          />
        </label>
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? '正在注册…' : '注册'}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        已有账户？{' '}
        <Link to="/login" className="font-medium text-indigo-600">
          返回登录
        </Link>
      </p>
    </section>
  )
}
