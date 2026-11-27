import { safeInternalPath } from "@/lib/safe-path"

export const DEFAULT_AFTER_LOGIN = "/dashboard"

/** Đường dẫn đích sau đăng nhập: chỉ đường dẫn nội bộ hợp lệ, không quay lại /login. */
export function resolveReturnPath(from: unknown): string {
  const safe = safeInternalPath(from)
  if (!safe || safe === "/login" || safe.startsWith("/login?") || safe.startsWith("/login#")) {
    return DEFAULT_AFTER_LOGIN
  }
  return safe
}
