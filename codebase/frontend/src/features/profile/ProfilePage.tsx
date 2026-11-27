import { LogOut } from "lucide-react"
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { stateSecondaryButtonClass } from "@/components/states"
import { useAuth } from "@/features/auth/useAuth"

const dateTime = new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium", timeStyle: "short" })

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 py-3 sm:grid-cols-[180px_1fr] sm:gap-4">
      <dt className="text-sm font-medium text-slate-600">{label}</dt>
      <dd className="break-words text-sm text-slate-900">{children}</dd>
    </div>
  )
}

/** /profile: thông tin phiên (không hiện token) và đăng xuất. */
export default function ProfilePage() {
  const { user, sessionExpiresAt, signOut } = useAuth()
  const navigate = useNavigate()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSignOut() {
    if (pending) return
    setPending(true)
    setError(null)
    try {
      await signOut()
      navigate("/login", { replace: true })
    } catch {
      setError("Không đăng xuất được. Hãy thử lại.")
      setPending(false)
    }
  }

  return (
    <section aria-labelledby="profile-title" className="mx-auto w-full max-w-2xl">
      <h1 id="profile-title" className="text-2xl font-bold tracking-tight text-violet-950">
        Hồ sơ
      </h1>
      <dl className="mt-6 divide-y divide-violet-100 rounded-2xl border border-violet-200 bg-white px-5">
        <Row label="Email">{user?.email ?? "Không có thông tin"}</Row>
        <Row label="Quyền truy cập">Coach trong danh sách được cấp quyền</Row>
        <Row label="Phiên hiện tại hết hạn lúc">
          {sessionExpiresAt ? dateTime.format(new Date(sessionExpiresAt * 1000)) : "Không xác định"}
          <span className="block text-xs text-slate-600">Hệ thống tự làm mới phiên khi bạn còn dùng ứng dụng.</span>
        </Row>
      </dl>
      {error && (
        <p role="alert" className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">
          {error}
        </p>
      )}
      <button type="button" onClick={() => void handleSignOut()} disabled={pending} className={`${stateSecondaryButtonClass} mt-6`}>
        <LogOut aria-hidden="true" className="size-4" />
        {pending ? "Đang đăng xuất..." : "Đăng xuất"}
      </button>
    </section>
  )
}
