import type { Session, SupabaseClient } from "@supabase/supabase-js"
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { api, configureApi, isAbortError, isApiError } from "@/services/api"
import { AuthContext } from "./AuthContext"
import type { AuthContextValue, AuthStatus, AuthUser, SignInResult } from "./types"

interface PublicConfig {
  supabase_url?: string
  supabase_publishable_key?: string
}

let cachedClient: { key: string; client: SupabaseClient } | null = null

/** Dùng lại client cho cùng url/key để tránh nhiều GoTrueClient (StrictMode, thử lại). */
async function getSupabaseClient(url: string, key: string): Promise<SupabaseClient> {
  const cacheKey = `${url}|${key}`
  if (cachedClient?.key !== cacheKey) {
    const { createClient } = await import("@supabase/supabase-js") // tách chunk, không nằm trong bundle đầu
    cachedClient = { key: cacheKey, client: createClient(url, key) }
  }
  return cachedClient.client
}

type BootPhase = "loading" | "unconfigured" | "unreachable" | "ready"
type VerifyPhase = "idle" | "checking" | "ok" | "forbidden" | "failed"

/**
 * Lấy /api/config, tạo Supabase client, theo dõi phiên và xác minh quyền bằng /api/me.
 * Token chỉ nằm trong Supabase client và ref nội bộ; không log, không đưa ra context.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [boot, setBoot] = useState<BootPhase>("loading")
  const [bootKey, setBootKey] = useState(0)
  const [sessionReady, setSessionReady] = useState(false)
  const [session, setSession] = useState<Session | null>(null)
  const [expired, setExpired] = useState(false)
  const [signedOutByUser, setSignedOutByUser] = useState(false)
  const [verify, setVerify] = useState<VerifyPhase>("idle")
  const [verifyKey, setVerifyKey] = useState(0)
  const [user, setUser] = useState<AuthUser | null>(null)

  const clientRef = useRef<SupabaseClient | null>(null)
  const tokenRef = useRef<string | null>(null)
  const userSignOutRef = useRef(false)

  const applySession = useCallback((next: Session | null) => {
    tokenRef.current = next?.access_token ?? null
    setSession(next)
  }, [])

  // Cấu hình + client + phiên.
  useEffect(() => {
    const controller = new AbortController()
    let unsubscribe = () => {}
    setBoot("loading")
    setSessionReady(false)
    api
      .get<PublicConfig>("/api/config", { auth: false, signal: controller.signal })
      .then(async (config) => {
        if (!config?.supabase_url || !config?.supabase_publishable_key) {
          setBoot("unconfigured")
          return
        }
        const client = await getSupabaseClient(config.supabase_url, config.supabase_publishable_key)
        if (controller.signal.aborted) return
        clientRef.current = client
        const { data } = client.auth.onAuthStateChange((event, next) => {
          if (controller.signal.aborted) return
          if (event === "SIGNED_OUT") {
            // Đăng xuất không do người dùng (hết hạn refresh token, tab khác) => hết phiên.
            if (!userSignOutRef.current) setExpired(true)
          } else if (next) {
            setExpired(false)
          }
          applySession(next)
        })
        unsubscribe = () => data.subscription.unsubscribe()
        setBoot("ready")
        return client.auth.getSession().then(({ data: current }) => {
          if (controller.signal.aborted) return
          applySession(current.session)
          setSessionReady(true)
        })
      })
      .catch((error: unknown) => {
        if (isAbortError(error)) return
        setBoot("unreachable")
      })
    return () => {
      controller.abort()
      unsubscribe()
    }
  }, [bootKey, applySession])

  // Backend trả 401 cho request có token: xoá phiên cục bộ, báo hết phiên.
  useEffect(() => {
    configureApi({
      getAccessToken: () => tokenRef.current,
      onUnauthorized: () => {
        if (!tokenRef.current) return
        setExpired(true)
        applySession(null)
        void clientRef.current?.auth.signOut({ scope: "local" }).catch(() => {})
      },
    })
    return () => configureApi({ getAccessToken: () => null, onUnauthorized: () => {} })
  }, [applySession])

  // Xác minh quyền (allowlist) mỗi khi đổi tài khoản; làm mới token không gọi lại.
  const userId = session?.user.id ?? null
  useEffect(() => {
    if (!userId) {
      setVerify("idle")
      setUser(null)
      return
    }
    const controller = new AbortController()
    setVerify("checking")
    api
      .get<AuthUser>("/api/me", { signal: controller.signal })
      .then((me) => {
        setUser(me)
        setVerify("ok")
      })
      .catch((error: unknown) => {
        if (isAbortError(error)) return
        if (isApiError(error) && error.kind === "unauthorized") return // đã xử lý ở onUnauthorized
        setUser(null)
        setVerify(isApiError(error) && error.kind === "forbidden" ? "forbidden" : "failed")
      })
    return () => controller.abort()
  }, [userId, verifyKey])

  const signIn = useCallback(async (email: string, password: string): Promise<SignInResult> => {
    const client = clientRef.current
    if (!client) return { ok: false, reason: "unavailable" }
    userSignOutRef.current = false
    setSignedOutByUser(false)
    const { error } = await client.auth.signInWithPassword({ email, password })
    if (!error) return { ok: true }
    const invalid = error.code === "invalid_credentials" || error.status === 400
    return { ok: false, reason: invalid ? "invalid_credentials" : "unavailable" }
  }, [])

  const signOut = useCallback(async () => {
    userSignOutRef.current = true
    setSignedOutByUser(true)
    setExpired(false)
    const client = clientRef.current
    try {
      const result = await client?.auth.signOut()
      // Gọi máy chủ lỗi (mạng) vẫn phải xoá phiên cục bộ.
      if (result?.error) await client?.auth.signOut({ scope: "local" })
    } catch {
      await client?.auth.signOut({ scope: "local" }).catch(() => {})
    } finally {
      applySession(null)
    }
  }, [applySession])

  const retry = useCallback(() => {
    if (boot === "ready") setVerifyKey((key) => key + 1)
    else setBootKey((key) => key + 1)
  }, [boot])

  const status: AuthStatus = useMemo(() => {
    if (boot === "unconfigured") return "unconfigured"
    if (boot === "unreachable") return "backend_unreachable"
    if (boot === "loading" || !sessionReady) return "loading"
    if (!session) return expired ? "expired" : "signed_out"
    if (verify === "forbidden") return "forbidden"
    if (verify === "failed") return "verify_failed"
    if (verify === "ok") return "authenticated"
    return "loading"
  }, [boot, sessionReady, session, expired, verify])

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user: status === "authenticated" ? user : null,
      sessionExpiresAt: session?.expires_at ?? null,
      signedOutByUser,
      signIn,
      signOut,
      retry,
    }),
    [status, user, session, signedOutByUser, signIn, signOut, retry],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
