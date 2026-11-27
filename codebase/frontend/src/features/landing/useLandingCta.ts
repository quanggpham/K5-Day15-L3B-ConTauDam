import { useAuth } from "@/features/auth/useAuth"

/**
 * CTA chính của landing: "Mở dashboard" khi đã đăng nhập, "Đăng nhập" khi chưa.
 * Trong lúc đang xác định phiên (loading) dùng nhãn trung tính để không nhảy sai chữ.
 */
export function useLandingCta(): { to: string; label: string; authenticated: boolean } {
  const { status } = useAuth()
  const authenticated = status === "authenticated"
  if (status === "loading") {
    return { to: "/dashboard", label: "Vào ứng dụng", authenticated: false }
  }
  return authenticated
    ? { to: "/dashboard", label: "Mở dashboard", authenticated }
    : { to: "/login", label: "Đăng nhập", authenticated }
}
