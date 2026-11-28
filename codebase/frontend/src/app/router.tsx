import { createBrowserRouter, type RouteObject } from "react-router-dom"
import RequireAuth from "@/features/auth/RequireAuth"
import { ReportCopilotRoute } from "@/features/reports/ReportCopilotRoute"
import { ReportRunScope } from "@/features/reports/ReportRunContext"
import { NotFoundPage, RouteErrorPage } from "./pages"
import type { RouteHandle } from "./routeHandle"

const handle = (value: RouteHandle) => value

/**
 * Vùng đã đăng nhập: RequireAuth -> ReportRunScope -> AppShell -> màn hình.
 * Màn lớn dùng `lazy` (tách chunk theo route). Muốn panel Copilot riêng thì thêm `copilot` vào handle.
 * ReportRunScope nằm trên AppShell vì panel Copilot (trong shell) và trang báo cáo dùng chung một lần tải /reports/:runId.
 */
export const routes: RouteObject[] = [
  {
    errorElement: <RouteErrorPage />,
    children: [
      { path: "/", lazy: async () => ({ Component: (await import("@/features/landing/LandingPage")).default }) },
      { path: "/login", lazy: async () => ({ Component: (await import("@/features/auth/LoginPage")).default }) },
      {
        element: <RequireAuth />,
        children: [
          {
            element: <ReportRunScope />,
            children: [
              {
                lazy: async () => ({ Component: (await import("@/components/layout/AppShell")).default }),
                children: [
                  { path: "/dashboard", lazy: async () => ({ Component: (await import("@/features/dashboard/DashboardPage")).default }), handle: handle({ title: "Dashboard" }) },
                  { path: "/analysis/new", lazy: async () => ({ Component: (await import("@/features/analysis/NewAnalysisPage")).default }), handle: handle({ title: "Tạo phân tích" }) },
                  { path: "/history", lazy: async () => ({ Component: (await import("@/features/history/HistoryPage")).default }), handle: handle({ title: "Lịch sử" }) },
                  { path: "/reports/:runId", lazy: async () => ({ Component: (await import("@/features/reports/ReportPage")).default }), handle: handle({ title: "Báo cáo", copilot: ReportCopilotRoute }) },
                  { path: "/reports/:runId/review", lazy: async () => ({ Component: (await import("@/features/reviews/ReviewPage")).default }), handle: handle({ title: "Duyệt báo cáo", copilot: ReportCopilotRoute }) },
                  { path: "/knowledge", lazy: async () => ({ Component: (await import("@/features/knowledge/KnowledgePage")).default }), handle: handle({ title: "KB bài giảng" }) },
                  { path: "/profile", lazy: async () => ({ Component: (await import("@/features/profile/ProfilePage")).default }), handle: handle({ title: "Hồ sơ" }) },
                ],
              },
            ],
          },
        ],
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
