import { ArrowRight, Check, Clock } from "lucide-react"
import { Link } from "react-router-dom"
import { useLandingCta } from "./useLandingCta"

// Nội dung lấy từ docs/learningpulse-design.md và README (trạng thái hiện tại).
const AVAILABLE_NOW = [
  "Số liệu tổng hợp theo bài học và theo ý kiến thức",
  "Xếp thứ tự theo tỷ lệ sai ở lần trả lời đầu",
  "Gắn cờ ý kiến thức chưa đủ dữ liệu, không xếp ưu tiên",
  "Lưu bản nháp báo cáo để coach xem lại",
]

const NOT_YET = ["Khuyến nghị AI", "Truy xuất bài giảng (RAG)", "Chấm JEV"]

/** Hero: tiêu đề h1 duy nhất, mô tả ngắn, CTA Đăng nhập và thẻ trạng thái thật. */
export default function Hero() {
  const cta = useLandingCta()
  return (
    <section
      aria-labelledby="landing-hero-title"
      className="mx-auto grid w-full max-w-6xl gap-10 px-4 py-12 sm:px-6 sm:py-16 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:gap-14 lg:px-8 lg:py-24"
    >
      <div>
        <p className="inline-flex items-center rounded-full border border-violet-200 bg-violet-100 px-3 py-1 text-sm font-medium text-violet-900">
          Dành cho lab coach và giảng viên AI20K
        </p>
        <h1
          id="landing-hero-title"
          className="mt-5 text-4xl font-bold tracking-tight text-balance text-violet-950 sm:text-5xl lg:text-6xl"
        >
          Biết nên ôn lại ý nào trước buổi học
        </h1>
        <p className="mt-5 max-w-xl text-lg leading-8 text-slate-700">
          LearningPulse tính số liệu từ dữ liệu pre-class thật, chỉ ra ý kiến
          thức học viên đang hổng, để bạn quyết định dựa trên dữ liệu thay vì
          cảm nhận. Mọi con số do code tính, coach là người quyết định cuối.
        </p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
          <Link
            to={cta.to}
            className="inline-flex h-12 items-center justify-center gap-2 rounded-lg bg-violet-700 px-6 text-base font-semibold text-white shadow-sm shadow-violet-700/30 outline-hidden transition-colors hover:bg-violet-800 focus-visible:ring-2 focus-visible:ring-violet-700 focus-visible:ring-offset-2 motion-reduce:transition-none"
          >
            {cta.label}
            <ArrowRight aria-hidden="true" className="size-5" />
          </Link>
          <p className="text-sm text-slate-600">
            {cta.authenticated
              ? "Bạn đã đăng nhập."
              : "Chỉ email trong danh sách cho phép mới vào được."}
          </p>
        </div>
      </div>

      <aside
        aria-labelledby="landing-status-title"
        className="rounded-2xl border border-violet-200 bg-white p-6 shadow-lg shadow-violet-200/50 sm:p-8"
      >
        <h2
          id="landing-status-title"
          className="text-base font-semibold text-violet-950"
        >
          Hiện đã có trong ứng dụng
        </h2>
        <ul className="mt-4 space-y-3">
          {AVAILABLE_NOW.map((item) => (
            <li key={item} className="flex gap-3 text-slate-700">
              <span
                aria-hidden="true"
                className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-violet-100 text-violet-800"
              >
                <Check className="size-3.5" />
              </span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
        <div className="mt-6 rounded-xl bg-violet-50 p-4">
          <p className="flex items-center gap-2 text-sm font-semibold text-violet-950">
            <Clock aria-hidden="true" className="size-4" />
            Chưa bật
          </p>
          <p className="mt-1 text-sm text-slate-700">
            {NOT_YET.join(", ")}. LearningPulse không gửi gì cho học viên hay
            LMS.
          </p>
        </div>
      </aside>
    </section>
  )
}
