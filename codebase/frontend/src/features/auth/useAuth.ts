import { useContext } from "react"
import { AuthContext } from "./AuthContext"
import type { AuthContextValue } from "./types"

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error("useAuth phải nằm trong <AuthProvider>")
  return value
}
