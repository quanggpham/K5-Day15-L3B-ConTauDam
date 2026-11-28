import { Sparkles } from "lucide-react"
import { useId, useRef, useState } from "react"
import { Link } from "react-router-dom"
import { ErrorState, LoadingState, stateSecondaryButtonClass } from "@/components/states"
import { Badge } from "@/components/ui/badge"
import { controlClass, labelClass } from "@/components/ui/controls"
import { NOT_RECORDED } from "@/lib/format"
import { apiErrorMessage, isApiError } from "@/services/api"
import { COPILOT_ACTIONS, actionLabel, evidenceFieldLabel, type CopilotAction, type CopilotResult } from "./copilotTypes"
import { useReportRun } from "./ReportRunContext"
import { readStoredSnapshot } from "./snapshot"
import type { RunDetail } from "./types"
import { useCopilot } from "./useCopilot"
import DemoPreview from "./DemoPreview"
import { valueText } from "./values"

const actionButton =
  "w-full rounded-lg border border-violet-300 bg-white px-3 py-2.5 text-left text-sm font-semibold text-violet-950 outline-none transition-colors hover:bg-violet-50 focus-visible:ring-2 focus-visible:ring-violet-700 disabled:cursor-not-allowed disabled:border-slate-300 disabled:bg-slate-100 disabled:text-slate-600 motion-reduce:transition-none"

/**
 * Panel Copilot của /reports/:runId*. Dữ liệu run lấy từ context của route (không gọi API chi tiết lần nữa).
 * Chỉ 4 thao tác cố định; câu trả lời của hai thao tác đầu do code dựng từ snapshot đã lưu.
 */
export default function ReportCopilot() {
  const run = useReportRun()
  let body: React.ReactNode
  if (!run) {
    body = <p className="text-sm text-slate-700">Mở một báo cáo để dùng Copilot.</p>
  } else if (run.phase === "error") {
    const notFound = isApiError(run.error) && run.error.kind === "not_found"
    body = notFound ? (
      <p className="text-sm text-slate-700">Không tìm thấy báo cáo nên Copilot chưa có căn cứ.</p>
    ) : (
      <ErrorState title="Copilot chưa có báo cáo" message={apiErrorMessage(run.error)} onRetry={() => void run.reload()} />
    )
  } else if (run.phase === "loading" || !run.data) {
    body = <LoadingState label="Đang tải báo cáo..." onRetry={() => void run.reload()} />
  } else {
    body = <CopilotBody key={run.runId} detail={run.data} />
  }
  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-base font-semibold text-violet-950">
          <Sparkles aria-hidden="true" className="size-4 text-violet-700" />
          Copilot
        </h2>
        <Badge variant="secondary" className="bg-violet-100 text-violet-900">
          Thao tác cố định
        </Badge>
      </div>
      {body}
    </div>
  )
}

function CopilotBody({ detail }: { detail: RunDetail }) {
  const { run, retry, pending, result, problem, setProblem } = useCopilot(detail.run_id)
  const stored = readStoredSnapshot(detail)
  const kcCodes = stored.state === "ok" ? stored.lesson.kcs.map((kc) => kc.kc_code) : []
  const [kcCode, setKcCode] = useState("")
  const kcRef = useRef<HTMLSelectElement>(null)
  const ids = useId()
  const kcHintId = `${ids}-kc-hint`
  const busy = pending !== null
  const usable = stored.state === "ok"

  function start(action: CopilotAction, kcRequired: boolean) {
    if (kcRequired && !kcCode) {
      setProblem({ message: "Thao tác này cần chọn một KC. Hãy chọn KC ở ô phía trên rồi bấm lại.", retryable: false, kcProblem: true })
      kcRef.current?.focus()
      return
    }
    void run({ action, kcCode: kcCode || null })
  }

  return (
    <div className="space-y-4" aria-busy={busy}>
      <p className="text-xs leading-5 text-slate-700">
        Trả lời chỉ dựa trên snapshot đã lưu của báo cáo bài {detail.lesson_id}. Coach là người quyết định cuối cùng.
      </p>

      {!usable && (
        <p role="note" className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950">
          Báo cáo này không có snapshot số liệu đúng định dạng hiện hành nên Copilot không có căn cứ để trả lời.
        </p>
      )}

      <div>
        <label htmlFor={`${ids}-kc`} className={labelClass}>
          KC
        </label>
        <select
          id={`${ids}-kc`}
          ref={kcRef}
          className={controlClass}
          value={kcCode}
          disabled={!usable || busy}
          aria-describedby={kcHintId}
          aria-invalid={problem?.kcProblem || undefined}
          onChange={(event) => {
            setKcCode(event.target.value)
            if (problem?.kcProblem) setProblem(null)
          }}
        >
          <option value="">{kcCodes.length === 0 ? "Không có KC trong snapshot" : "Chưa chọn KC"}</option>
          {kcCodes.map((code) => (
            <option key={code} value={code}>
              {code}
            </option>
          ))}
        </select>
        <p id={kcHintId} className="mt-1 text-xs text-slate-700">
          Danh sách lấy từ snapshot đã lưu. Chọn KC để giải thích ưu tiên hoặc tạo bản nháp demo.
        </p>
      </div>

      {usable && <DemoPreview runId={detail.run_id} kcCode={kcCode} />}

      <ul className="space-y-3" aria-label="Thao tác Copilot">
        {COPILOT_ACTIONS.filter((def) => !def.generative).map((def) => {
          const descId = `${ids}-${def.id}-desc`
          return (
            <li key={def.id}>
              <button
                type="button"
                className={actionButton}
                disabled={!usable || busy}
                aria-describedby={descId}
                onClick={() => start(def.id, def.kc === "required")}
              >
                <span className="flex items-center gap-2">
                  {def.label}
                  {pending?.action === def.id && <span className="font-normal text-slate-700">(đang xử lý...)</span>}
                </span>
              </button>
              <p id={descId} className="mt-1 text-xs leading-5 text-slate-700">
                {def.description}
              </p>
            </li>
          )
        })}
      </ul>

      {busy && (
        <p role="status" className="text-sm text-slate-700">
          Đang lấy câu trả lời từ snapshot đã lưu...
        </p>
      )}

      {problem && (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-3 text-sm text-red-900">
          <p>{problem.message}</p>
          {problem.retryable && (
            <button type="button" onClick={retry} disabled={busy} className={`${stateSecondaryButtonClass} mt-2 h-9 text-xs`}>
              Thử lại
            </button>
          )}
        </div>
      )}

      <div aria-live="polite">{result && <ResultCard result={result} />}</div>

      <p className="text-xs text-slate-700">
        <Link to={`/reports/${encodeURIComponent(detail.run_id)}`} className="underline">
          Báo cáo
        </Link>
        {" · "}
        <Link to={`/reports/${encodeURIComponent(detail.run_id)}/review`} className="underline">
          Duyệt đề xuất
        </Link>
      </p>
    </div>
  )
}

function unitFor(field: string, units: Record<string, string> | undefined): string | null {
  const key = field.split(".").pop() ?? field
  return units?.[key] ?? null
}

function ResultCard({ result }: { result: CopilotResult }) {
  const insufficient = result.status === "insufficient_comparison_data"
  const byCode = result.generated_by === "code" && result.source === "stored_snapshot"
  return (
    <section aria-label={`Kết quả: ${actionLabel(result.action)}`} className="rounded-xl border border-violet-200 bg-violet-50/60 p-3">
      <h3 className="text-sm font-semibold text-violet-950">
        {actionLabel(result.action)}
        {result.kc_code ? ` · KC ${result.kc_code}` : ""}
      </h3>
      <p
        className={
          insufficient
            ? "mt-2 inline-block rounded-full border border-amber-300 bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-950"
            : "mt-2 inline-block rounded-full border border-violet-200 bg-white px-2.5 py-0.5 text-xs font-medium text-violet-950"
        }
      >
        {insufficient ? "Chưa đủ dữ liệu để so sánh" : result.status === "ok" ? "Có kết quả" : `Trạng thái: ${result.status}`}
      </p>
      <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-slate-900">{result.message}</p>
      <p className="mt-2 text-xs text-slate-700">
        {byCode ? "Tạo bằng code từ snapshot đã lưu (không dùng AI)." : `Nguồn: ${result.source ?? NOT_RECORDED}.`}
        {result.snapshot_version ? ` Phiên bản snapshot: ${result.snapshot_version}.` : ""}
      </p>

      <h4 className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-700">Căn cứ trong snapshot</h4>
      {result.evidence.length === 0 ? (
        <p className="mt-1 text-xs text-slate-700">Không có mục căn cứ nào được ghi cho câu trả lời này.</p>
      ) : (
        <ul className="mt-1 space-y-2">
          {result.evidence.map((item, index) => {
            const unit = unitFor(item.field, result.units)
            return (
              <li key={`${item.kc_code ?? "-"}:${item.field}:${index}`} className="rounded-lg border border-violet-100 bg-white px-2.5 py-2 text-xs">
                <p className="font-medium text-violet-950">
                  {item.kc_code ? `KC ${item.kc_code}` : "Cả bài"} · {evidenceFieldLabel(item.field)}
                </p>
                <p className="text-slate-700">
                  Trường: <code className="break-all">{item.field}</code>
                </p>
                <p className="text-slate-900">
                  Giá trị: <span className="break-all font-semibold tabular-nums">{valueText(item.value)}</span>
                  {unit ? <span className="text-slate-700"> ({unit})</span> : null}
                </p>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
