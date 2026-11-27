import { createBrowserRouter, type RouteObject } from "react-router-dom"
import RequireAuth from "@/features/auth/RequireAuth"
import {
  NotFoundPage,
  ReportPage,
  ReportReviewPage,
  RouteErrorPage,
} from "./pages"
import type { RouteHandle } from "./routeHandle"

const handle = (value: RouteHandle) => value

/**
 * Vùng đã đăng nhập: RequireAuth -> AppShell -> màn hình.
 * Màn lớn dùng `lazy` (tách chunk theo route). Thêm màn: đổi `element` của route tương ứng; muốn panel Copilot riêng thì thêm `copilot` vào handle.
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
            lazy: async () => ({ Component: (await import("@/components/layout/AppShell")).default }),
            children: [
              { path: "/dashboard", lazy: async () => ({ Component: (await import("@/features/dashboard/DashboardPage")).default }), handle: handle({ title: "Dashboard" }) },
              { path: "/analysis/new", lazy: async () => ({ Component: (await import("@/features/analysis/NewAnalysisPage")).default }), handle: handle({ title: "Tạo phân tích" }) },
              { path: "/history", lazy: async () => ({ Component: (await import("@/features/history/HistoryPage")).default }), handle: handle({ title: "Lịch sử" }) },
              { path: "/reports/:runId", element: <ReportPage />, handle: handle({ title: "Báo cáo" }) },
              { path: "/reports/:runId/review", element: <ReportReviewPage />, handle: handle({ title: "Duyệt báo cáo" }) },
              { path: "/profile", lazy: async () => ({ Component: (await import("@/features/profile/ProfilePage")).default }), handle: handle({ title: "Hồ sơ" }) },
            ],
          },
        ],
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
