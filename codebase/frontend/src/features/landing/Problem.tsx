import { ClipboardList, Target } from "lucide-react"

const PAIN_POINTS = [
  {
    icon: ClipboardList,
    title: "Khó tổng hợp kết quả học tập",
    body: "Tổng hợp kết quả học tập trước buổi học là việc khó, và càng khó để xác định phần kiến thức học viên chưa hiểu.",
  },
  {
    icon: Target,
    title: "Khó chọn nội dung giảng lại",
    body: "Không có cơ sở rõ ràng thì khó chọn nội dung cần giảng lại, và buổi ôn có thể lệch trọng tâm.",
  },
]

/** Mục Bài toán: nêu hai khó khăn của coach (nguồn: docs/learningpulse-design.md). */
export default function Problem() {
  return (
    <section
      id="bai-toan"
      aria-labelledby="landing-problem-title"
      className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8"
    >
      <h2
        id="landing-problem-title"
        className="text-3xl font-bold tracking-tight text-balance text-violet-950 sm:text-4xl"
      >
        Bài toán của lab coach
      </h2>
      <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-700">
        Trước mỗi buổi học, coach phải quyết định nên ôn lại ý nào. Đây là
        giả thuyết về khó khăn của người dùng, nhóm vẫn đang kiểm chứng bằng dữ
        liệu pre-class và phỏng vấn.
      </p>
      <ul className="mt-8 grid gap-4 sm:grid-cols-2 sm:gap-6">
        {PAIN_POINTS.map(({ icon: Icon, title, body }) => (
          <li
            key={title}
            className="rounded-2xl border border-violet-200 bg-white p-6 shadow-sm shadow-violet-100"
          >
            <span
              aria-hidden="true"
              className="flex size-10 items-center justify-center rounded-lg bg-violet-100 text-violet-800"
            >
              <Icon className="size-5" />
            </span>
            <h3 className="mt-4 text-lg font-semibold text-violet-950">
              {title}
            </h3>
            <p className="mt-2 leading-7 text-slate-700">{body}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}
