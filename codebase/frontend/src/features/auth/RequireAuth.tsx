import { Navigate, Outlet, useLocation } from "react-router-dom"
import { ErrorState, LoadingState, stateSecondaryButtonClass } from "@/components/states"
import { safeInternalPath } from "@/lib/safe-path"
import { useAuth } from "./useAuth"

/**
 * Route layout bảo vệ vùng đã đăng nhập.
 * Chưa đăng nhập/hết phiên/ngoài allowlist => /login, kèm đường dẫn đích (chỉ đường dẫn nội bộ).
 */
export default function RequireAuth() {
  const { status, signedOutByUser, retry, signOut } = useAuth()
  const location = useLocation()

  switch (status) {
    case "authenticated":
      return <Outlet />
    case "loading":
      return <LoadingState fullPage label="Đang kiểm tra phiên đăng nhập..." onRetry={retry} />
    case "unconfigured":
      return (
        <ErrorState
          fullPage
          title="Chưa cấu hình đăng nhập"
          message="Backend chưa có cấu hình Supabase. Hãy liên hệ quản trị viên."
          onRetry={retry}
        />
      )
    case "backend_unreachable":
      return (
        <ErrorState
          fullPage
          title="Không kết nối được backend"
          message="Không tải được cấu hình ứng dụng. Hãy kiểm tra mạng hoặc thử lại sau."
          onRetry={retry}
        />
      )
    case "verify_failed":
      return (
        <ErrorState
          fullPage
          title="Chưa xác minh được quyền truy cập"
          message="Hệ thống tạm thời không kiểm tra được quyền của bạn. Hãy thử lại."
          onRetry={retry}
          action={
            <button
              type="button"
              onClick={() => void signOut()}
              className={stateSecondaryButtonClass}
            >
              Đăng xuất
            </button>
          }
        />
      )
    default: {
      // signed_out | expired | forbidden
      const from = signedOutByUser ? null : safeInternalPath(`${location.pathname}${location.search}${location.hash}`)
      return <Navigate to="/login" replace state={from ? { from } : undefined} />
    }
  }
}
