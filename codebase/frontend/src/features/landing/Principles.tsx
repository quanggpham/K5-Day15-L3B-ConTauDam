import { Database, ShieldCheck, UserCheck, Ban, EyeOff } from "lucide-react"

const PRINCIPLES = [
  {
    icon: Database,
    title: "Số do code tính",
    body: "DuckDB và Pandas tính mọi con số. Mô hình ngôn ngữ chỉ đề xuất, không tự đọc hay tự tính dữ liệu.",
  },
  {
    icon: ShieldCheck,
    title: "LLM không viết SQL",
    body: "Truy vấn dữ liệu là mã cố định của nhóm. Không có đường nào để mô hình tự sinh truy vấn.",
  },
  {
    icon: EyeOff,
    title: "Không gửi dữ liệu thô lên mô hình",
    body: "Mô hình chỉ nhận số liệu đã tổng hợp và đoạn bài giảng. Không có dữ liệu dòng hay mã học viên, và không có chức năng xếp hạng từng học viên.",
  },
  {
    icon: UserCheck,
    title: "Coach quyết định cuối",
    body: "Màn duyệt đã có: coach chấp nhận, từ chối, yêu cầu sửa hoặc sửa tay từng đề xuất, và lịch sử được lưu. Hiện chưa có đề xuất AI để duyệt.",
  },
  {
    icon: Ban,
    title: "Không gửi gì cho học viên hay LMS",
    body: "LearningPulse không nhắn tin, không giao bài và không ghi ngược vào LMS.",
  },
]

/** Mục Nguyên tắc an toàn (nguồn: docs/learningpulse-design.md). */
export default function Principles() {
  return (
    <section
      id="nguyen-tac"
      aria-labelledby="landing-principles-title"
      className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8"
    >
      <h2
        id="landing-principles-title"
        className="text-3xl font-bold tracking-tight text-balance text-violet-950 sm:text-4xl"
      >
        Nguyên tắc an toàn
      </h2>
      <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-700">
        Đây là nguyên tắc thiết kế của nhóm. Các lớp kiểm tra cho đề xuất AI
        chưa được bật, vì khuyến nghị AI chưa tích hợp vào ứng dụng.
      </p>
      <ul className="mt-8 flex flex-wrap justify-center gap-4 sm:gap-6">
        {PRINCIPLES.map(({ icon: Icon, title, body }) => (
          <li
            key={title}
            className="w-full rounded-2xl border border-violet-200 bg-white p-6 shadow-sm shadow-violet-100 sm:w-[calc((100%-1.5rem)/2)] lg:w-[calc((100%-3rem)/3)]"
          >
            <span
              aria-hidden="true"
              className="flex size-10 items-center justify-center rounded-lg bg-violet-100 text-violet-800"
            >
              <Icon className="size-5" />
            </span>
            <h3 className="mt-4 text-lg font-semibold text-violet-950">{title}</h3>
            <p className="mt-2 leading-7 text-slate-700">{body}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}
