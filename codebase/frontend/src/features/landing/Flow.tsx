import { Check, Clock, CircleDashed } from "lucide-react"

type Status = "available" | "partial" | "planned"

interface FlowStep {
  title: string
  body: string
  status: Status
}

// Trạng thái theo README: đã có báo cáo số liệu và lưu bản nháp;
// RAG, khuyến nghị AI, JEV chưa tích hợp.
const STEPS: FlowStep[] = [
  {
    title: "Số liệu",
    body: "Code tính tỷ lệ sai ở lần trả lời đầu theo bài học và theo ý kiến thức.",
    status: "available",
  },
  {
    title: "Lỗ hổng",
    body: "Code xếp hạng ý kiến thức đang hổng. Ý kiến thức có quá ít lượt trả lời được gắn cờ chưa đủ dữ liệu, không xếp ưu tiên.",
    status: "available",
  },
  {
    title: "Căn cứ",
    body: "Lấy đoạn bài giảng liên quan bằng BM25 và lọc theo bài. Cần nguồn bài giảng được phép dùng trước khi bật.",
    status: "planned",
  },
  {
    title: "Đề xuất",
    body: "LLM đề xuất thứ tự ưu tiên và cách giảng lại, kèm trích dẫn số liệu và đoạn bài, sau đó được kiểm tra.",
    status: "planned",
  },
  {
    title: "Coach duyệt",
    body: "Hiện coach có thể lưu báo cáo số liệu thành bản nháp. Chấp nhận, từ chối hay sửa tay từng đề xuất sẽ có khi có đề xuất AI.",
    status: "partial",
  },
]

const STATUS_LABEL: Record<Status, string> = {
  available: "Đã có",
  partial: "Có một phần",
  planned: "Chưa bật",
}

const STATUS_STYLE: Record<Status, string> = {
  available: "bg-violet-700 text-white",
  partial: "bg-violet-100 text-violet-900 border border-violet-300",
  planned: "bg-white text-slate-700 border border-dashed border-slate-400",
}

function StatusIcon({ status }: { status: Status }) {
  if (status === "available") return <Check aria-hidden="true" className="size-3.5" />
  if (status === "partial") return <Clock aria-hidden="true" className="size-3.5" />
  return <CircleDashed aria-hidden="true" className="size-3.5" />
}

/** Mục Luồng 5 bước, đánh dấu rõ bước nào đã có và bước nào chưa bật. */
export default function Flow() {
  return (
    <section
      id="luong-xu-ly"
      aria-labelledby="landing-flow-title"
      className="border-y border-violet-200/70 bg-violet-100/50"
    >
      <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
        <h2
          id="landing-flow-title"
          className="text-3xl font-bold tracking-tight text-balance text-violet-950 sm:text-4xl"
        >
          Luồng 5 bước từ dữ liệu đến quyết định
        </h2>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-700">
          Một quy trình cố định, thứ tự các bước luôn giống nhau. Mỗi bước ghi rõ
          đã có trong ứng dụng hay chưa bật.
        </p>
        <ol className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          {STEPS.map((step, index) => (
            <li
              key={step.title}
              className="flex flex-col rounded-2xl border border-violet-200 bg-white p-5 shadow-sm shadow-violet-100"
            >
              <div className="flex items-center justify-between gap-2">
                <span
                  aria-hidden="true"
                  className="flex size-8 items-center justify-center rounded-full bg-violet-100 text-sm font-bold text-violet-900"
                >
                  {index + 1}
                </span>
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLE[step.status]}`}
                >
                  <StatusIcon status={step.status} />
                  {STATUS_LABEL[step.status]}
                </span>
              </div>
              <h3 className="mt-4 text-lg font-semibold text-violet-950">
                <span className="sr-only">Bước {index + 1}: </span>
                {step.title}
              </h3>
              <p className="mt-2 text-sm leading-6 text-slate-700">{step.body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
