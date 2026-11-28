import { Activity, BookOpen, FilePlus2, History, LayoutDashboard, UserRound, type LucideIcon } from "lucide-react"
import { NavLink, Link } from "react-router-dom"
import { cn } from "@/lib/utils"
import { useAuth } from "@/features/auth/useAuth"

const ITEMS: { to: string; label: string; icon: LucideIcon }[] = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/analysis/new", label: "Tạo phân tích", icon: FilePlus2 },
  { to: "/history", label: "Lịch sử", icon: History },
  { to: "/knowledge", label: "KB bài giảng", icon: BookOpen },
  { to: "/profile", label: "Hồ sơ", icon: UserRound },
]

/** Nội dung sidebar: thương hiệu, điều hướng, tài khoản. Dùng cho cột desktop và drawer mobile. */
export function SidebarNav({ showBrand = true }: { showBrand?: boolean }) {
  const { user } = useAuth()
  return (
    <div className="flex h-full flex-col gap-6 p-4">
      {showBrand && (
        <Link
          to="/"
          className="flex w-fit items-center gap-2 rounded-md text-lg font-semibold tracking-tight text-violet-950 outline-none focus-visible:ring-2 focus-visible:ring-violet-600 focus-visible:ring-offset-2"
        >
          <span aria-hidden="true" className="flex size-8 items-center justify-center rounded-lg bg-violet-700 text-white">
            <Activity className="size-4" />
          </span>
          LearningPulse
        </Link>
      )}
      <nav aria-label="Điều hướng chính">
        <ul className="space-y-1">
          {ITEMS.map(({ to, label, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                className={({ isActive }) =>
                  cn(
                    "flex h-11 items-center gap-3 rounded-lg px-3 text-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-violet-600 motion-reduce:transition-none",
                    isActive ? "bg-violet-100 text-violet-950" : "text-slate-700 hover:bg-violet-50 hover:text-violet-950",
                  )
                }
              >
                <Icon aria-hidden="true" className="size-5 shrink-0" />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      {user?.email && (
        <p className="mt-auto break-all border-t border-violet-100 pt-4 text-xs text-slate-600">
          Đăng nhập: <span className="font-medium text-slate-800">{user.email}</span>
        </p>
      )}
    </div>
  )
}
