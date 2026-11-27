import { ChevronDown } from "lucide-react"

// Trả lời theo docs/learningpulse-design.md và README; không hứa tính năng chưa có.
const FAQS = [
  {
    q: "AI có gửi gì cho học viên không?",
    a: "Không. LearningPulse không nhắn tin, không giao bài cho học viên và không ghi ngược vào LMS. AI không có công cụ nào ghi hay gửi ra ngoài; ứng dụng chỉ lưu bản nháp báo cáo và lịch sử duyệt của coach.",
  },
  {
    q: "Dữ liệu nào được đưa lên mô hình?",
    a: "Theo thiết kế, mô hình chỉ nhận số liệu đã tổng hợp và đoạn bài giảng được phép dùng; không có dữ liệu dòng hay mã học viên. Hiện mô hình chưa được nối vào luồng báo cáo; hai thao tác Copilot đang chạy là do code trả lời từ snapshot đã lưu.",
  },
  {
    q: "Ai quyết định cuối cùng?",
    a: "Coach. Số liệu do code tính, còn quyết định ôn lại ý nào thuộc về coach.",
  },
  {
    q: "Khi nào bật gợi ý AI?",
    a: "Chưa có mốc thời gian. Cần có nguồn bài giảng được phép dùng và chốt cách chấm kiểm tra đầu ra trước khi bật. Hiện ứng dụng có dashboard, báo cáo số liệu đã lưu, Copilot cố định và màn duyệt, nhưng chưa có đề xuất AI để duyệt.",
  },
  {
    q: "Copilot làm được gì?",
    a: "Copilot trong báo cáo có 4 thao tác cố định. Hai thao tác đầu (giải thích ưu tiên, so sánh với bài trước) do code trả lời từ snapshot đã lưu. Hai thao tác tạo nội dung (kế hoạch ôn 15 phút, 3 câu hỏi kiểm tra lại) đang bị khoá cho đến khi có nguồn bài giảng và cách chấm đầu ra.",
  },
  {
    q: "Ai đăng nhập được?",
    a: "Chỉ lab coach và giảng viên có email trong danh sách cho phép. Không có trang đăng ký công khai, học viên và người ngoài không vào được.",
  },
  {
    q: "Có xem được từng học viên không?",
    a: "Không. Báo cáo chỉ theo bài học và ý kiến thức, không hiện, không xếp hạng và không gửi gì theo từng người.",
  },
]

/** FAQ bằng <details>/<summary> gốc, hỗ trợ bàn phím mặc định. */
export default function Faq() {
  return (
    <section
      id="hoi-dap"
      aria-labelledby="landing-faq-title"
      className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8"
    >
      <h2
        id="landing-faq-title"
        className="text-3xl font-bold tracking-tight text-balance text-violet-950 sm:text-4xl"
      >
        Câu hỏi thường gặp
      </h2>
      <div className="mt-8 space-y-3">
        {FAQS.map(({ q, a }) => (
          <details
            key={q}
            className="group rounded-xl border border-violet-200 bg-white shadow-sm shadow-violet-100"
          >
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 rounded-xl px-5 py-4 font-semibold text-violet-950 outline-hidden focus-visible:ring-2 focus-visible:ring-violet-700 [&::-webkit-details-marker]:hidden">
              {q}
              <ChevronDown
                aria-hidden="true"
                className="size-5 shrink-0 text-violet-700 transition-transform group-open:rotate-180 motion-reduce:transition-none"
              />
            </summary>
            <p className="px-5 pb-4 leading-7 text-slate-700">{a}</p>
          </details>
        ))}
      </div>
    </section>
  )
}
