import { Link } from "react-router-dom"
import { useLandingCta } from "./useLandingCta"

/** Footer gọn: tên dự án và link đăng nhập / mở dashboard. */
export default function Footer() {
  const cta = useLandingCta()
  return (
    <footer className="border-t border-violet-200/70 bg-white/70">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-3 px-4 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
        <div>
          <p className="font-semibold text-violet-950">LearningPulse</p>
          <p className="text-sm text-slate-600">
            Hỗ trợ lab coach và giảng viên AI20K chọn nội dung ôn lại trước buổi học.
          </p>
        </div>
        <Link
          to={cta.to}
          className="inline-flex h-10 w-fit items-center rounded-lg border border-violet-300 bg-white px-4 text-sm font-medium text-violet-900 outline-none transition-colors hover:bg-violet-50 focus-visible:ring-2 focus-visible:ring-violet-600 focus-visible:ring-offset-2 motion-reduce:transition-none"
        >
          {cta.label}
        </Link>
      </div>
    </footer>
  )
}
