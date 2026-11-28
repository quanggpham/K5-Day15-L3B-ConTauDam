import { Link } from "react-router-dom"
import { EmptyState, stateSecondaryButtonClass } from "@/components/states"
import { cardClass } from "@/components/ui/controls"
import { DistributionSection, KcRateSection, PrioritySection } from "@/features/dashboard/KcSection"
import { MetricCards } from "@/features/dashboard/MetricCards"
import { NOT_RECORDED, formatDateTime } from "@/lib/format"
import { AiUnavailable } from "./AiUnavailable"
import { EditedFlag, JevScore, ReviewStatusChip, chipClass, kcLabel } from "./RecommendationBits"
import { readStoredSnapshot } from "./snapshot"
import type { RunDetail } from "./types"
import { citationsOf, entriesOf } from "./values"

function Unavailable({ notice }: { notice: string }) {
  return (
    <EmptyState
      title="Chưa có số liệu để hiển thị"
      description={`${notice} Không có số liệu nào được suy diễn hay điền bằng 0.`}
      className="rounded-2xl border border-dashed border-violet-300 bg-white/70"
    />
  )
}

function Banner({ children }: { children: React.ReactNode }) {
  return (
    <p role="status" className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950">
      {children}
    </p>
  )
}

export function OverviewTab({ detail }: { detail: RunDetail }) {
  const stored = readStoredSnapshot(detail)
  if (stored.state !== "ok") return <Unavailable notice={stored.notice} />
  const { lesson, snapshot } = stored
  return (
    <div className="space-y-6">
      <p className="text-xs text-slate-700">
        Số liệu đọc từ snapshot đã lưu lúc tạo báo cáo (tổng hợp lúc {formatDateTime(snapshot.generated_at)}), không tính lại.
        Tỷ lệ tính trên lượt trả lời đầu tiên đã chấm; "người" là học viên duy nhất có lượt chấm.
      </p>
      {lesson.status === "no_graded" && (
        <Banner>Bài {lesson.lesson_id} chưa có lượt chấm lần đầu (mẫu số 0): các tỷ lệ không được tính, không hiển thị là 0%.</Banner>
      )}
      {lesson.status === "insufficient_sample" && (
        <Banner>Bài {lesson.lesson_id} có ít lượt chấm hơn ngưỡng mẫu: chỉ nên dùng số liệu để tham khảo.</Banner>
      )}
      <MetricCards lesson={lesson} units={snapshot.units} minSample={snapshot.min_sample} />
      <DistributionSection lesson={lesson} units={snapshot.units} />
    </div>
  )
}

export function GapsTab({ detail }: { detail: RunDetail }) {
  const stored = readStoredSnapshot(detail)
  if (stored.state !== "ok") return <Unavailable notice={stored.notice} />
  const { lesson, snapshot } = stored
  return (
    <div className="space-y-6">
      <KcRateSection lesson={lesson} minSample={snapshot.min_sample} />
      <PrioritySection lesson={lesson} />
    </div>
  )
}

export function RecommendationsTab({ detail }: { detail: RunDetail }) {
  const { recommendations: recs } = detail
  if (recs.length === 0) {
    return <AiUnavailable context="recommendations" aiStatus={detail.ai_status} aiStatusReason={detail.ai_status_reason} />
  }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-700">
          {recs.length} đề xuất. Coach quyết định cuối cùng: duyệt từng đề xuất ở màn Duyệt.
        </p>
        <Link to={`/reports/${encodeURIComponent(detail.run_id)}/review`} className={stateSecondaryButtonClass}>
          Duyệt đề xuất
        </Link>
      </div>
      <ol className="space-y-3">
        {recs.map((rec) => (
          <li key={rec.id} className={cardClass}>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-semibold text-violet-950">
                {kcLabel(rec)}
                {rec.priority !== null && rec.priority !== undefined && <span className="font-normal text-slate-700"> · ưu tiên {rec.priority}</span>}
              </h3>
              <ReviewStatusChip status={rec.review_status} />
            </div>
            <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-slate-900">{rec.content ?? NOT_RECORDED}</p>
            <div className="mt-3 space-y-2">
              <EditedFlag rec={rec} />
              <JevScore rec={rec} />
              {(rec.not_recorded?.length ?? 0) > 0 && (
                <p className="text-xs text-slate-700">Trạng thái duyệt chưa được ghi nhận: coi như chưa duyệt.</p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}

function passedText(passed: boolean | null): string {
  if (passed === true) return "Đạt"
  if (passed === false) return "Không đạt"
  return NOT_RECORDED
}

export function EvaluationTab({ detail }: { detail: RunDetail }) {
  const { evaluations, recommendations } = detail
  if (evaluations.length === 0 && recommendations.length === 0) {
    return <EmptyState title="Chưa có bản nháp đã lưu"
      description="Trong Copilot, chọn KC và tạo bản nháp. Khi thấy điểm JEV, bấm Lưu bản nháp để duyệt rồi quay lại tab này." />
  }
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-700">Điểm JEV và kết quả kiểm định chỉ là tín hiệu hỗ trợ; coach là người quyết định cuối cùng.</p>
      {evaluations.length > 0 && (
        <section aria-labelledby="eval-results" className="space-y-3">
          <h3 id="eval-results" className="text-lg font-semibold text-violet-950">
            Kết quả kiểm định
          </h3>
          <ul className="space-y-3">
            {evaluations.map((item) => {
              const metrics = entriesOf(item.metrics)
              return (
                <li key={item.id} className={cardClass}>
                  <p className="flex flex-wrap items-center gap-2 text-sm">
                    <span className={chipClass}>Kết quả: {passedText(item.passed)}</span>
                    <span className="text-slate-800">Bộ chấm: {item.judge ?? NOT_RECORDED}</span>
                  </p>
                  {metrics ? (
                    <dl className="mt-3 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
                      {metrics.map(([key, value]) => (
                        <div key={key} className="flex justify-between gap-3 border-b border-violet-100 py-1">
                          <dt className="text-slate-700">{key}</dt>
                          <dd className="break-all text-right tabular-nums">{value}</dd>
                        </div>
                      ))}
                    </dl>
                  ) : (
                    <p className="mt-3 text-sm text-slate-700">Chỉ số chi tiết {NOT_RECORDED}.</p>
                  )}
                </li>
              )
            })}
          </ul>
        </section>
      )}
      <section aria-labelledby="eval-jev" className="space-y-3">
        <h3 id="eval-jev" className="text-lg font-semibold text-violet-950">
          Điểm JEV theo đề xuất
        </h3>
        {recommendations.length > 0 && recommendations.every((rec) => rec.jev_score == null) && (
          <p className="text-sm text-slate-700">
            Các đề xuất đã lưu chưa có điểm cho phiên bản hiện tại. Để xem điểm mới, tạo bản nháp trong Copilot và lưu sau khi thấy điểm JEV.
          </p>
        )}
        {recommendations.length === 0 ? (
          <p className="text-sm text-slate-700">Báo cáo chưa có đề xuất nào nên chưa có điểm JEV.</p>
        ) : (
          <ul className="space-y-2">
            {recommendations.map((rec) => (
              <li key={rec.id} className="rounded-lg border border-violet-100 bg-white px-3 py-2">
                <p className="text-sm font-medium text-violet-950">{kcLabel(rec)}</p>
                <JevScore rec={rec} className="mt-1" />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

export function EvidenceTab({ detail }: { detail: RunDetail }) {
  const stored = readStoredSnapshot(detail)
  const withCitations = detail.recommendations.map((rec) => ({ rec, citations: citationsOf(rec.citations) }))
  const anyCitations = withCitations.some((item) => item.citations.length > 0)
  const modelText = detail.model ?? (detail.ai_status === "not_enabled" ? "không có (AI chưa bật)" : NOT_RECORDED)
  const generatedAt = stored.state === "ok" ? formatDateTime(stored.snapshot.generated_at) : NOT_RECORDED
  let citationBody: React.ReactNode
  if (detail.recommendations.length === 0) {
    citationBody = <AiUnavailable context="evidence" aiStatus={detail.ai_status} aiStatusReason={detail.ai_status_reason} />
  } else if (!anyCitations) {
    citationBody = (
      <p className="rounded-lg bg-violet-50 px-3 py-4 text-sm text-slate-800">
        Các đề xuất hiện có chưa lưu căn cứ nào (căn cứ {NOT_RECORDED}). Không có nguồn nào được thêm hộ.
      </p>
    )
  } else {
    citationBody = (
      <ul className="space-y-3">
        {withCitations.map(({ rec, citations }) => (
          <li key={rec.id} className={cardClass}>
            <p className="font-medium text-violet-950">{kcLabel(rec)}</p>
            {citations.length === 0 ? (
              <p className="mt-1 text-sm text-slate-700">Đề xuất này chưa lưu căn cứ ({NOT_RECORDED}).</p>
            ) : (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-900">
                {citations.map((citation) => (
                  <li key={citation.key} className="break-words">
                    {citation.href ? (
                      <a href={citation.href} target="_blank" rel="noopener noreferrer" className="text-violet-800 underline">
                        {citation.text}
                      </a>
                    ) : (
                      citation.text
                    )}
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    )
  }
  return (
    <div className="space-y-6">
      <section aria-labelledby="evidence-source" className={cardClass}>
        <h3 id="evidence-source" className="text-lg font-semibold text-violet-950">
          Nguồn số liệu
        </h3>
        <dl className="mt-3 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
          <Row label="Phiên bản snapshot" value={detail.snapshot_version ?? NOT_RECORDED} />
          <Row label="Snapshot tổng hợp lúc" value={generatedAt} />
          <Row label="Báo cáo tạo lúc" value={formatDateTime(detail.created_at)} />
          <Row label="Mã yêu cầu tạo báo cáo" value={detail.request_id ?? NOT_RECORDED} />
          <Row label="Model" value={modelText} />
        </dl>
      </section>
      <section aria-labelledby="evidence-citations" className="space-y-3">
        <h3 id="evidence-citations" className="text-lg font-semibold text-violet-950">
          Căn cứ bài giảng của đề xuất
        </h3>
        {citationBody}
      </section>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <dt className="text-xs font-medium text-slate-700">{label}</dt>
      <dd className="break-all text-slate-900">{value}</dd>
    </div>
  )
}

