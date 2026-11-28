import { useRef, useState } from "react"
import { Link, Navigate, useLocation } from "react-router-dom"
import { Activity } from "lucide-react"
import { ErrorState, LoadingState, stateButtonClass } from "@/components/states"
import { LoginForm } from "./LoginForm"
import { resolveReturnPath } from "./returnPath"
import { useAuth } from "./useAuth"

const MESSAGES = {
  invalid: "Email hoặc mật khẩu không đúng. Hãy kiểm tra lại.",
  unavailable: "Chưa đăng nhập được do lỗi kết nối. Hãy thử lại sau ít phút.",
}

export default function LoginPage() {
  const { status, signIn, signOut, retry } = useAuth()
  const location = useLocation()
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const busy = useRef(false)

  if (status === "authenticated") {
    const from = (location.state as { from?: unknown } | null)?.from
    return <Navigate to={resolveReturnPath(from)} replace />
  }
  if (status === "loading") return <LoadingState fullPage label="Đang chuẩn bị đăng nhập..." onRetry={retry} />
  if (status === "unconfigured") {
    return (
      <ErrorState
        fullPage
        title="Chưa cấu hình đăng nhập"
        message="Backend chưa có cấu hình Supabase. Hãy liên hệ quản trị viên."
        onRetry={retry}
      />
    )
  }
  if (status === "backend_unreachable") {
    return (
      <ErrorState
        fullPage
        title="Không kết nối được backend"
        message="Không tải được cấu hình ứng dụng. Hãy kiểm tra mạng hoặc thử lại sau."
        onRetry={retry}
      />
    )
  }
  if (status === "verify_failed") {
    return (
      <ErrorState
        fullPage
        title="Chưa xác minh được quyền truy cập"
        message="Hệ thống tạm thời không kiểm tra được quyền của bạn. Hãy thử lại."
        onRetry={retry}
        action={
          <button type="button" onClick={() => void signOut()} className={stateButtonClass}>
            Đăng xuất
          </button>
        }
      />
    )
  }

  async function handleSubmit(email: string, password: string) {
    if (busy.current) return // chặn bấm đúp
    busy.current = true
    setSubmitting(true)
    setError(null)
    try {
      const result = await signIn(email, password)
      if (!result.ok) setError(result.reason === "invalid_credentials" ? MESSAGES.invalid : MESSAGES.unavailable)
    } finally {
      busy.current = false
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-gradient-to-b from-violet-50 via-white to-violet-50 px-4 py-10 text-slate-900">
      <main className="w-full max-w-md">
        <Link
          to="/"
          className="mb-6 flex w-fit items-center gap-2 rounded-md text-lg font-semibold text-violet-950 outline-none focus-visible:ring-2 focus-visible:ring-violet-600 focus-visible:ring-offset-2"
        >
          <span aria-hidden="true" className="flex size-8 items-center justify-center rounded-lg bg-violet-700 text-white">
            <Activity className="size-4" />
          </span>
          LearningPulse
        </Link>
        <div className="rounded-2xl border border-violet-200 bg-white p-6 shadow-lg shadow-violet-200/50 sm:p-8">
          <h1 className="text-2xl font-bold tracking-tight text-violet-950">Đăng nhập</h1>
          <p className="mt-1 text-sm text-slate-700">Dành cho lab coach và giảng viên được cấp quyền.</p>

          {status === "expired" && (
            <p role="status" className="mt-4 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950">
              Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại để tiếp tục.
            </p>
          )}
          {status === "forbidden" && (
            <div role="alert" className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-3 text-sm text-red-900">
              <p>
                Tài khoản này chưa nằm trong danh sách được cấp quyền. Hãy dùng tài khoản khác hoặc liên hệ quản trị viên.
              </p>
              <button
                type="button"
                onClick={() => void signOut()}
                className="mt-2 rounded-md font-semibold underline outline-none focus-visible:ring-2 focus-visible:ring-red-700"
              >
                Đăng xuất tài khoản này
              </button>
            </div>
          )}

          <div className="mt-6">
            <LoginForm submitting={submitting} error={error} onSubmit={handleSubmit} />
          </div>
        </div>
        <p className="mt-4 text-center text-sm text-slate-600">Cần tài khoản đã được tạo trong Supabase Auth.</p>
      </main>
    </div>
  )
}
