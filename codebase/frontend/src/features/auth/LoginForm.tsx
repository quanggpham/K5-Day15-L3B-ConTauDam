import { Eye, EyeOff, LogIn } from "lucide-react"
import { useId, useState, type FormEvent } from "react"

interface LoginFormProps {
  submitting: boolean
  /** Lỗi hiển thị cạnh form (vd sai mật khẩu). */
  error: string | null
  onSubmit: (email: string, password: string) => void
}

const inputClass =
  "block h-11 w-full rounded-lg border border-violet-300 bg-white px-3 text-base text-slate-900 outline-none placeholder:text-slate-500 focus-visible:ring-2 focus-visible:ring-violet-600 aria-[invalid=true]:border-red-600"

/** Form đăng nhập email + mật khẩu (thuần trình bày, giữ giá trị khi lỗi). */
export function LoginForm({ submitting, error, onSubmit }: LoginFormProps) {
  const id = useId()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [visible, setVisible] = useState(false)
  const errorId = `${id}-error`

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (submitting) return
    onSubmit(email.trim(), password)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor={`${id}-email`} className="mb-1 block text-sm font-medium text-slate-800">
          Email
        </label>
        <input
          id={`${id}-email`}
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          className={inputClass}
        />
      </div>
      <div>
        <label htmlFor={`${id}-password`} className="mb-1 block text-sm font-medium text-slate-800">
          Mật khẩu
        </label>
        <div className="relative">
          <input
            id={`${id}-password`}
            type={visible ? "text" : "password"}
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? errorId : undefined}
            className={`${inputClass} pr-12`}
          />
          <button
            type="button"
            onClick={() => setVisible((value) => !value)}
            aria-label={visible ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
            className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-lg text-violet-900 outline-none hover:bg-violet-50 focus-visible:ring-2 focus-visible:ring-violet-600"
          >
            {visible ? <EyeOff aria-hidden="true" className="size-5" /> : <Eye aria-hidden="true" className="size-5" />}
          </button>
        </div>
      </div>
      {error && (
        <p id={errorId} role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={submitting}
        className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-violet-700 text-base font-semibold text-white outline-none transition-colors hover:bg-violet-800 focus-visible:ring-2 focus-visible:ring-violet-700 focus-visible:ring-offset-2 disabled:opacity-60 motion-reduce:transition-none"
      >
        <LogIn aria-hidden="true" className="size-5" />
        {submitting ? "Đang đăng nhập..." : "Đăng nhập"}
      </button>
    </form>
  )
}
