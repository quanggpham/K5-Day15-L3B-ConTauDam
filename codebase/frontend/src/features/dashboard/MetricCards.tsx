import { cardClass } from "@/components/ui/controls"
import { NOT_RECORDED, formatCount, formatRate, formatSignedPp, isNum } from "@/lib/format"
import type { LessonView } from "./types"

interface MetricCardsProps {
  lesson: LessonView
  units?: Record<string, string>
  minSample?: number | null
}

function Card({ label, value, children }: { label: string; value: string; children?: React.ReactNode }) {
  return (
    <div className={cardClass}>
      <dt className="text-sm font-medium text-slate-700">{label}</dt>
      <dd className="mt-2">
        <p className="text-3xl font-bold tracking-tight text-violet-950">{value}</p>
        {children && <div className="mt-2 space-y-1 text-xs leading-5 text-slate-700">{children}</div>}
      </dd>
    </div>
  )
}

/** Bốn thẻ chỉ số của bài đang chọn. Thiếu dữ liệu -> nhãn riêng, không đổi thành 0. */
export function MetricCards({ lesson, units, minSample }: MetricCardsProps) {
  const { sample, distribution } = lesson
  const accuracy = formatRate(lesson.first_attempt_accuracy)
  const delta = formatSignedPp(lesson.delta_vs_previous_pp)
  const noDenominator = isNum(sample.responses) && sample.responses === 0

  return (
    <dl className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-4">
      <Card label="Học viên có lượt chấm" value={isNum(sample.learners) ? `${formatCount(sample.learners)} người` : NOT_RECORDED}>
        <p>Đơn vị: {units?.learners ?? "người (học viên duy nhất có lượt chấm)"}.</p>
      </Card>

      <Card label="Độ chính xác lần đầu" value={accuracy ?? (noDenominator ? "Chưa có lượt chấm" : NOT_RECORDED)}>
        {accuracy ? (
          <p>
            {formatCount(distribution.correct)} đúng / {formatCount(sample.responses)} lượt chấm lần đầu.
          </p>
        ) : (
          <p>{noDenominator ? "Mẫu số bằng 0 lượt nên không tính được tỷ lệ (không phải 0%)." : "Backend không trả tỷ lệ cho bài này."}</p>
        )}
        <p>Đơn vị: {units?.first_attempt_accuracy ?? "tỷ lệ trên lượt"}.</p>
      </Card>

      <Card
        label="KC đủ mẫu"
        value={isNum(lesson.sufficient_kc_count) && isNum(lesson.kc_count) ? `${lesson.sufficient_kc_count} / ${lesson.kc_count} KC` : NOT_RECORDED}
      >
        <p>
          KC đủ mẫu có từ {isNum(minSample) ? formatCount(minSample) : "?"} lượt chấm lần đầu; KC còn lại chỉ để tham khảo, không xếp ưu tiên.
        </p>
      </Card>

      <Card label="Chênh lệch so với bài trước" value={delta ? `${delta} điểm %` : "—"}>
        {delta ? (
          <>
            <p>Của tỷ lệ sai, so với bài {lesson.previous_lesson_id ?? NOT_RECORDED}.</p>
            <p>Dấu âm: tỷ lệ sai giảm; dấu dương: tỷ lệ sai tăng.</p>
          </>
        ) : (
          <p>
            {lesson.previous_lesson_id
              ? `Chưa tính được so với bài ${lesson.previous_lesson_id} (thiếu tỷ lệ ở một trong hai bài).`
              : "Không có bài trước để so sánh."}
          </p>
        )}
      </Card>
    </dl>
  )
}
