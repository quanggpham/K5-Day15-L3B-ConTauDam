import { Activity, ArrowRight } from "lucide-react"

/** Thanh điều hướng đơn giản: thương hiệu bên trái, nút Đăng nhập bên phải. */
export default function LandingNav() {
  return (
    <header className="border-b border-violet-200/70 bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <nav
        aria-label="Điều hướng chính"
        className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8"
      >
        <a
          href="/"
          className="flex items-center gap-2 rounded-md text-lg font-semibold tracking-tight text-violet-950 outline-none focus-visible:ring-2 focus-visible:ring-violet-600 focus-visible:ring-offset-2"
        >
          <span
            aria-hidden="true"
            className="flex size-8 items-center justify-center rounded-lg bg-violet-700 text-white"
          >
            <Activity className="size-4" />
          </span>
          LearningPulse
        </a>
        <a
          href="/login"
          className="inline-flex h-10 items-center gap-1.5 rounded-lg border border-violet-300 bg-white px-4 text-sm font-medium text-violet-900 outline-none transition-colors hover:bg-violet-50 focus-visible:ring-2 focus-visible:ring-violet-600 focus-visible:ring-offset-2 motion-reduce:transition-none"
        >
          Đăng nhập
          <ArrowRight aria-hidden="true" className="size-4" />
        </a>
      </nav>
    </header>
  )
}
