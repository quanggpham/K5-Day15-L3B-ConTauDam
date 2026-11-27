import { useAuth } from "@/features/auth/useAuth"

/** CTA chính của landing: "Mở dashboard" khi đã đăng nhập, ngược lại "Đăng nhập". */
export function useLandingCta(): { to: string; label: string; authenticated: boolean } {
  const { status } = useAuth()
  const authenticated = status === "authenticated"
  return authenticated
    ? { to: "/dashboard", label: "Mở dashboard", authenticated }
    : { to: "/login", label: "Đăng nhập", authenticated }
}
