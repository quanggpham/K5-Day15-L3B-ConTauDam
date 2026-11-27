import { Activity, ArrowRight } from "lucide-react"
import { Link } from "react-router-dom"
import { useLandingCta } from "./useLandingCta"

const SECTION_LINKS = [
  { href: "#bai-toan", label: "Bài toán" },
  { href: "#luong-xu-ly", label: "Luồng xử lý" },
  { href: "#minh-hoa", label: "Minh hoạ" },
  { href: "#nguyen-tac", label: "Nguyên tắc an toàn" },
  { href: "#hoi-dap", label: "Hỏi đáp" },
]

/** Thanh điều hướng đơn giản: thương hiệu bên trái, nút Đăng nhập bên phải. */
export default function LandingNav() {
  const cta = useLandingCta()
  return (
    <header className="border-b border-violet-200/70 bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <nav
        aria-label="Điều hướng chính"
        className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-y-1 px-4 py-3 sm:px-6 md:h-16 md:flex-nowrap md:py-0 lg:px-8"
      >
        <Link
          to="/"
          className="flex items-center gap-2 rounded-md text-lg font-semibold tracking-tight text-violet-950 outline-none focus-visible:ring-2 focus-visible:ring-violet-600 focus-visible:ring-offset-2"
        >
          <span
            aria-hidden="true"
            className="flex size-8 items-center justify-center rounded-lg bg-violet-700 text-white"
          >
            <Activity className="size-4" />
          </span>
          LearningPulse
        </Link>
        <ul className="order-3 -mx-1 flex w-full items-center gap-1 overflow-x-auto pb-1 md:order-none md:mx-0 md:w-auto md:overflow-visible md:pb-0">
          {SECTION_LINKS.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="block whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium text-slate-700 outline-none transition-colors hover:text-violet-900 focus-visible:ring-2 focus-visible:ring-violet-600 motion-reduce:transition-none"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>
        <Link
          to={cta.to}
          className="inline-flex h-10 items-center gap-1.5 rounded-lg border border-violet-300 bg-white px-4 text-sm font-medium text-violet-900 outline-none transition-colors hover:bg-violet-50 focus-visible:ring-2 focus-visible:ring-violet-600 focus-visible:ring-offset-2 motion-reduce:transition-none"
        >
          {cta.label}
          <ArrowRight aria-hidden="true" className="size-4" />
        </Link>
      </nav>
    </header>
  )
}
