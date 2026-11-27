import { Suspense, lazy } from "react"
import { LoadingState } from "@/components/states"

const ReportCopilot = lazy(() => import("./ReportCopilot"))

/** Gắn vào `handle.copilot` của route báo cáo; panel tải theo nhu cầu để không nằm trong bundle đầu. */
export function ReportCopilotRoute() {
  return (
    <Suspense fallback={<LoadingState label="Đang tải Copilot..." />}>
      <ReportCopilot />
    </Suspense>
  )
}
