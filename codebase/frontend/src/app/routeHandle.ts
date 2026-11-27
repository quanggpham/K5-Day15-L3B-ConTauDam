import type { ComponentType } from "react"

/** Metadata gắn vào route (`handle`) để AppShell đọc. */
export interface RouteHandle {
  /** Dùng cho document.title. */
  title: string
  /**
   * Nội dung panel Copilot cho route này (mặc định: placeholder).
   * Component tự đọc `useParams()` (vd `runId`) nếu cần.
   */
  copilot?: ComponentType
}

export function isRouteHandle(value: unknown): value is RouteHandle {
  return typeof value === "object" && value !== null && typeof (value as RouteHandle).title === "string"
}
