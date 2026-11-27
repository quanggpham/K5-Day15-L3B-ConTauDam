export type AuthStatus =
  | "loading" // đang lấy cấu hình / phiên / xác minh quyền
  | "unconfigured" // backend chưa có SUPABASE_URL/KEY
  | "backend_unreachable" // không gọi được /api/config
  | "signed_out" // chưa đăng nhập
  | "expired" // từng đăng nhập nhưng phiên hết hạn (401)
  | "forbidden" // có phiên nhưng /api/me trả 403 (ngoài allowlist)
  | "verify_failed" // /api/me lỗi tạm thời (5xx/mạng)
  | "authenticated"

export interface AuthUser {
  id: string
  email: string | null
}

export type SignInResult =
  | { ok: true }
  | { ok: false; reason: "invalid_credentials" | "unavailable" }

export interface AuthContextValue {
  status: AuthStatus
  /** Chỉ có khi status === "authenticated". */
  user: AuthUser | null
  /** Thời điểm hết hạn của access token hiện tại (epoch giây), để hiển thị ở /profile. */
  sessionExpiresAt: number | null
  /** true sau khi người dùng chủ động đăng xuất (để không khôi phục đường dẫn cũ). */
  signedOutByUser: boolean
  signIn: (email: string, password: string) => Promise<SignInResult>
  signOut: () => Promise<void>
  /** Thử lại bước đang lỗi (cấu hình hoặc xác minh quyền). */
  retry: () => void
}
