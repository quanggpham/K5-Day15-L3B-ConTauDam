import { Menu, Sparkles } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { Outlet, useLocation, useMatches } from "react-router-dom"
import { isRouteHandle } from "@/app/routeHandle"
import { useMediaQuery } from "@/hooks/useMediaQuery"
import { CopilotPanel } from "./CopilotPanel"
import { Drawer } from "./Drawer"
import { SidebarNav } from "./SidebarNav"

const iconButton =
  "flex size-11 items-center justify-center rounded-lg text-violet-900 outline-none hover:bg-violet-100 focus-visible:ring-2 focus-visible:ring-violet-600"

/**
 * Khung vùng đã đăng nhập: sidebar trái, nội dung giữa (<Outlet/>), panel Copilot phải.
 * Desktop (>= lg): 3 cột. Mobile: menu và Copilot mở theo yêu cầu bằng drawer.
 * Mỗi nội dung chỉ được mount một lần (desktop hoặc drawer), tránh gọi dữ liệu hai lần.
 */
export default function AppShell() {
  const isDesktop = useMediaQuery("(min-width: 1024px)")
  const [menuOpen, setMenuOpen] = useState(false)
  const [copilotOpen, setCopilotOpen] = useState(false)
  const { pathname } = useLocation()
  const matches = useMatches()
  const mainRef = useRef<HTMLElement>(null)
  const firstRender = useRef(true)

  const handle = [...matches].reverse().map((m) => m.handle).find(isRouteHandle)
  const Copilot = handle?.copilot ?? CopilotPanel

  // Đổi route: đóng drawer, cập nhật tiêu đề tab, đưa focus về vùng nội dung (SPA a11y).
  useEffect(() => {
    setMenuOpen(false)
    setCopilotOpen(false)
    document.title = handle?.title ? `${handle.title} · LearningPulse` : "LearningPulse"
    if (firstRender.current) firstRender.current = false
    else mainRef.current?.focus()
  }, [pathname, handle?.title])

  return (
    <div className="min-h-dvh bg-gradient-to-b from-violet-50 via-white to-violet-50 text-slate-900 antialiased lg:grid lg:grid-cols-[240px_minmax(0,1fr)_320px]">
      <a
        href="#app-main"
        onClick={(event) => {
          event.preventDefault()
          mainRef.current?.focus()
        }}
        className="sr-only rounded-md bg-white px-4 py-2 font-medium text-violet-900 focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:ring-2 focus:ring-violet-700"
      >
        Bỏ qua điều hướng
      </a>

      <aside aria-label="Thanh bên" className="hidden border-r border-violet-200/70 bg-white/80 lg:sticky lg:top-0 lg:block lg:h-dvh lg:overflow-y-auto">
        {isDesktop && <SidebarNav />}
      </aside>

      <div className="min-w-0">
        <header className="flex items-center justify-between border-b border-violet-200/70 bg-white/80 px-2 py-2 lg:hidden">
          <button
            type="button"
            className={iconButton}
            aria-label="Mở menu"
            aria-haspopup="dialog"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(true)}
          >
            <Menu aria-hidden="true" className="size-5" />
          </button>
          <span className="font-semibold text-violet-950">LearningPulse</span>
          <button
            type="button"
            className={iconButton}
            aria-label="Mở Copilot"
            aria-haspopup="dialog"
            aria-expanded={copilotOpen}
            onClick={() => setCopilotOpen(true)}
          >
            <Sparkles aria-hidden="true" className="size-5" />
          </button>
        </header>
        <main
          id="app-main"
          ref={mainRef}
          tabIndex={-1}
          className="px-4 py-6 outline-none sm:px-6 lg:px-8 lg:py-8"
        >
          <Outlet />
        </main>
      </div>

      <aside aria-label="Copilot" className="hidden border-l border-violet-200/70 bg-white/80 lg:sticky lg:top-0 lg:block lg:h-dvh lg:overflow-y-auto">
        {isDesktop && <Copilot />}
      </aside>

      {!isDesktop && (
        <>
          <Drawer open={menuOpen} onOpenChange={setMenuOpen} side="left" title="Menu">
            <SidebarNav showBrand={false} />
          </Drawer>
          <Drawer open={copilotOpen} onOpenChange={setCopilotOpen} side="right" title="Copilot">
            <Copilot />
          </Drawer>
        </>
      )}
    </div>
  )
}
