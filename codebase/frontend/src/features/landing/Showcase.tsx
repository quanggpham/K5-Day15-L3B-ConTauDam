import { AlertCircle } from "lucide-react"

interface SampleRow {
  kc: string
  level: string
  barClass?: string
  rank?: number
  insufficient?: boolean
}

// Dữ liệu MẪU để minh hoạ bố cục, không phải số liệu thật, không có con số nào.
const SAMPLE_ROWS: SampleRow[] = [
  { kc: "KC-A", level: "Tỷ lệ sai: cao", barClass: "w-4/5", rank: 1 },
  { kc: "KC-B", level: "Tỷ lệ sai: trung bình", barClass: "w-3/5", rank: 2 },
  { kc: "KC-C", level: "Tỷ lệ sai: thấp", barClass: "w-1/5", rank: 3 },
  { kc: "KC-D", level: "Chưa đủ dữ liệu", insufficient: true },
]

/** Minh hoạ báo cáo bằng CSS tĩnh. Mọi tên và mức độ đều là dữ liệu giả. */
export default function Showcase() {
  return (
    <section
      id="minh-hoa"
      aria-labelledby="landing-showcase-title"
      className="border-y border-violet-200/70 bg-violet-100/50"
    >
      <div className="mx-auto grid w-full max-w-6xl gap-8 px-4 py-12 sm:px-6 sm:py-16 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:gap-14 lg:px-8">
        <div>
          <h2
            id="landing-showcase-title"
            className="text-3xl font-bold tracking-tight text-balance text-violet-950 sm:text-4xl"
          >
            Báo cáo trông như thế nào
          </h2>
          <p className="mt-4 text-lg leading-8 text-slate-700">
            Trên dashboard và trong báo cáo đã lưu, coach chọn một bài học và xem
            các ý kiến thức xếp theo tỷ lệ sai ở lần trả lời đầu. Ý kiến thức có quá ít lượt trả lời được tách riêng,
            gắn cờ chưa đủ dữ liệu và không xếp hạng.
          </p>
        </div>

        <figure className="rounded-2xl border border-violet-200 bg-white p-5 shadow-lg shadow-violet-200/50 sm:p-6">
          <p className="inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-sm font-medium text-amber-900">
            <AlertCircle aria-hidden="true" className="size-4" />
            Minh hoạ, không phải số liệu thật
          </p>
          <ul className="mt-5 space-y-4">
            {SAMPLE_ROWS.map((row) => (
              <li key={row.kc}>
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="font-semibold text-violet-950">
                    {row.rank ? `Hạng ${row.rank}: ` : ""}
                    {row.kc}
                  </span>
                  <span
                    className={
                      row.insufficient
                        ? "rounded-full border border-dashed border-slate-400 px-2 py-0.5 text-xs font-medium text-slate-700"
                        : "text-slate-700"
                    }
                  >
                    {row.level}
                  </span>
                </div>
                {row.insufficient ? (
                  <div
                    aria-hidden="true"
                    className="mt-2 h-3 w-full rounded-full border border-dashed border-slate-400"
                  />
                ) : (
                  <div
                    aria-hidden="true"
                    className="mt-2 h-3 w-full overflow-hidden rounded-full bg-violet-100"
                  >
                    <div className={`h-full rounded-full bg-violet-700 ${row.barClass}`} />
                  </div>
                )}
              </li>
            ))}
          </ul>
          <figcaption className="mt-5 text-sm text-slate-600">
            Tên KC-A đến KC-D là giả. Độ dài thanh chỉ để minh hoạ bố cục.
          </figcaption>
        </figure>
      </div>
    </section>
  )
}
