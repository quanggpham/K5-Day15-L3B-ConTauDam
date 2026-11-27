import { cardClass } from "@/components/ui/controls"
import { NOT_RECORDED, formatCount } from "@/lib/format"
import { DistributionChart } from "./DistributionChart"
import { KcChart } from "./KcChart"
import { deltaText, kcKind, kcStatusLabel, rateText, toChartRows } from "./kcData"
import type { LessonView } from "./types"

function Legend() {
  return (
    <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-700">
      <li className="flex items-center gap-2">
        <span aria-hidden="true" className="inline-block h-3 w-5 rounded-sm bg-violet-700" />
        Cột đặc: đủ mẫu
      </li>
      <li className="flex items-center gap-2">
        <span aria-hidden="true" className="inline-block h-3 w-5 rounded-sm border border-dashed border-violet-700 bg-violet-200" />
        Cột nhạt viền nét đứt: chưa đủ dữ liệu (không xếp ưu tiên)
      </li>
    </ul>
  )
}

export function KcRateSection({ lesson, minSample }: { lesson: LessonView; minSample?: number | null }) {
  const rows = toChartRows(lesson.kcs)
  const emptyCount = lesson.kcs.filter((kc) => kcKind(kc) === "empty").length
  return (
    <section aria-labelledby="kc-rate-title" className={cardClass}>
      <h2 id="kc-rate-title" className="text-lg font-semibold text-violet-950">
        Tỷ lệ sai lần đầu theo KC
      </h2>
      <p className="mt-1 text-sm text-slate-700">Đơn vị: tỷ lệ trên lượt chấm lần đầu của từng KC.</p>

      {lesson.kcs.length === 0 ? (
        <p className="mt-4 rounded-lg bg-violet-50 px-3 py-4 text-sm text-slate-800">Bài này chưa có KC nào trong dữ liệu tổng hợp.</p>
      ) : (
        <>
          {rows.length > 0 ? (
            <div
              role="img"
              aria-label={`Biểu đồ cột ngang tỷ lệ sai lần đầu của ${rows.length} KC. Số liệu đầy đủ có trong bảng ngay bên dưới.`}
              className="mt-4"
            >
              <KcChart rows={rows} />
              <Legend />
            </div>
          ) : (
            <p className="mt-4 rounded-lg bg-violet-50 px-3 py-4 text-sm text-slate-800">
              Chưa có KC nào có lượt chấm (mẫu số 0) nên không vẽ biểu đồ.
            </p>
          )}
          {emptyCount > 0 && (
            <p className="mt-2 text-xs text-slate-700">
              {emptyCount} KC có mẫu số 0 (chưa có lượt chấm): không vẽ cột và không có tỷ lệ, xem trong bảng.
            </p>
          )}

          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse text-left text-sm">
              <caption className="pb-2 text-left text-sm font-medium text-slate-800">
                Bảng số liệu theo KC (lượt = lượt trả lời đầu tiên đã chấm)
              </caption>
              <thead>
                <tr className="border-b border-violet-200 text-xs uppercase tracking-wide text-slate-600">
                  <th scope="col" className="py-2 pr-3 font-semibold">KC</th>
                  <th scope="col" className="py-2 pr-3 font-semibold">Trạng thái</th>
                  <th scope="col" className="py-2 pr-3 text-right font-semibold">Lượt chấm</th>
                  <th scope="col" className="py-2 pr-3 text-right font-semibold">Người</th>
                  <th scope="col" className="py-2 pr-3 text-right font-semibold">Lượt sai</th>
                  <th scope="col" className="py-2 pr-3 text-right font-semibold">Tỷ lệ sai</th>
                  <th scope="col" className="py-2 text-right font-semibold">So với bài trước</th>
                </tr>
              </thead>
              <tbody>
                {lesson.kcs.map((kc) => (
                  <tr key={kc.kc_code} className="border-b border-violet-100 align-top">
                    <th scope="row" className="py-2 pr-3 font-semibold text-violet-950">{kc.kc_code}</th>
                    <td className="py-2 pr-3 text-slate-800">{kcStatusLabel(kc, minSample)}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">{formatCount(kc.graded_count)}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">{formatCount(kc.learner_count)}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">{formatCount(kc.incorrect_count)}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">{rateText(kc)}</td>
                    <td className="py-2 text-right tabular-nums">{deltaText(kc)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}

export function PrioritySection({ lesson }: { lesson: LessonView }) {
  const groups = new Map<number, typeof lesson.priority>()
  for (const kc of lesson.priority) {
    const rank = typeof kc.rank === "number" ? kc.rank : 0
    groups.set(rank, [...(groups.get(rank) ?? []), kc])
  }
  return (
    <section aria-labelledby="priority-title" className={cardClass}>
      <h2 id="priority-title" className="text-lg font-semibold text-violet-950">
        KC ưu tiên xem lại
      </h2>
      <p className="mt-1 text-sm text-slate-700">Chỉ xếp KC đủ mẫu, theo tỷ lệ sai giảm dần. Bằng tỷ lệ thì đồng hạng và hiện cả nhóm.</p>
      {groups.size === 0 ? (
        <p className="mt-3 rounded-lg bg-violet-50 px-3 py-4 text-sm text-slate-800">Chưa có KC đủ mẫu để xếp ưu tiên.</p>
      ) : (
        <ol className="mt-3 space-y-2">
          {[...groups.entries()].map(([rank, kcs]) => (
            <li key={rank} className="rounded-lg border border-violet-100 px-3 py-2 text-sm">
              <span className="font-semibold text-violet-950">{rank > 0 ? `Hạng ${rank}` : `Hạng ${NOT_RECORDED}`}</span>
              {kcs.length > 1 && <span className="text-slate-700"> · đồng hạng {kcs.length} KC</span>}
              <span className="text-slate-800">: {kcs.map((kc) => `${kc.kc_code} (${rateText(kc)})`).join(", ")}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

export function DistributionSection({ lesson, units }: { lesson: LessonView; units?: Record<string, string> }) {
  const { distribution, sample } = lesson
  const hasGraded = sample.responses !== undefined && sample.responses !== null && sample.responses > 0
  return (
    <section aria-labelledby="dist-title" className={cardClass}>
      <h2 id="dist-title" className="text-lg font-semibold text-violet-950">
        Phân bố lượt đúng và sai
      </h2>
      <p className="mt-1 text-sm text-slate-700">Đơn vị: {units?.correct ?? "lượt"}, tính trên lượt trả lời đầu tiên đã chấm.</p>
      {hasGraded ? (
        <>
          <div
            role="img"
            aria-label={`Biểu đồ cột phân bố lượt trả lời đầu tiên đã chấm: ${distribution.correct} lượt đúng, ${distribution.incorrect} lượt sai.`}
            className="mt-3"
          >
            <DistributionChart correct={distribution.correct} incorrect={distribution.incorrect} />
          </div>
          <table className="mt-2 w-full max-w-sm border-collapse text-left text-sm">
            <caption className="sr-only">Số lượt đúng, sai và chưa chấm</caption>
            <tbody>
              <tr className="border-b border-violet-100">
                <th scope="row" className="py-1.5 pr-3 font-medium">Lượt đúng</th>
                <td className="py-1.5 text-right tabular-nums">{formatCount(distribution.correct)}</td>
              </tr>
              <tr className="border-b border-violet-100">
                <th scope="row" className="py-1.5 pr-3 font-medium">Lượt sai</th>
                <td className="py-1.5 text-right tabular-nums">{formatCount(distribution.incorrect)}</td>
              </tr>
              <tr>
                <th scope="row" className="py-1.5 pr-3 font-medium">Lượt chưa chấm (ngoài mẫu số)</th>
                <td className="py-1.5 text-right tabular-nums">{formatCount(distribution.ungraded)}</td>
              </tr>
            </tbody>
          </table>
        </>
      ) : (
        <p className="mt-3 rounded-lg bg-violet-50 px-3 py-4 text-sm text-slate-800">
          Chưa có lượt chấm (mẫu số 0) nên không vẽ phân bố.
          {" "}Lượt chưa chấm: {formatCount(distribution.ungraded)}.
        </p>
      )}
    </section>
  )
}
