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

/**
 * Thanh điều hướng: thương hiệu, link neo, nút CTA. Thứ tự DOM = thứ tự nhìn
 * ở mọi cỡ màn hình (WCAG 2.4.3), nên chỉ dùng grid, không dùng `order`.
 * Mobile: hàng 1 thương hiệu, hàng 2 link neo (cuộn ngang) rồi CTA.
 * Desktop (md+): một hàng thương hiệu, link neo, CTA.
 */
export default function LandingNav() {
  const cta = useLandingCta()
  return (
    <header className="border-b border-violet-200/70 bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <nav
        aria-label="Điều hướng chính"
        className="mx-auto grid w-full max-w-6xl grid-cols-[minmax(0,1fr)_auto] items-center gap-x-2 gap-y-1 px-4 py-3 sm:px-6 md:h-16 md:grid-cols-[auto_minmax(0,1fr)_auto] md:gap-x-4 md:py-0 lg:px-8"
      >
        <Link
          to="/"
          className="col-span-2 flex w-fit items-center gap-2 rounded-md text-lg font-semibold tracking-tight text-violet-950 outline-hidden focus-visible:ring-2 focus-visible:ring-violet-600 focus-visible:ring-offset-2 md:col-span-1"
        >
          <span
            aria-hidden="true"
            className="flex size-8 items-center justify-center rounded-lg bg-violet-700 text-white"
          >
            <Activity className="size-4" />
          </span>
          LearningPulse
        </Link>
        <ul className="flex min-w-0 items-center gap-1 overflow-x-auto p-1 md:justify-self-center md:overflow-visible">
          {SECTION_LINKS.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="block whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium text-slate-700 outline-hidden transition-colors hover:text-violet-900 focus-visible:ring-2 focus-visible:ring-violet-600 motion-reduce:transition-none"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>
        <Link
          to={cta.to}
          className="inline-flex h-10 items-center gap-1.5 rounded-lg border border-violet-300 bg-white px-4 text-sm font-medium text-violet-900 outline-hidden transition-colors hover:bg-violet-50 focus-visible:ring-2 focus-visible:ring-violet-600 focus-visible:ring-offset-2 motion-reduce:transition-none"
        >
          {cta.label}
          <ArrowRight aria-hidden="true" className="size-4" />
        </Link>
      </nav>
    </header>
  )
}
