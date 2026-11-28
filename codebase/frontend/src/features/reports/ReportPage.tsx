import { Download, ListChecks } from "lucide-react"
import { Link } from "react-router-dom"
import { ErrorState, LoadingState, stateButtonClass, stateSecondaryButtonClass } from "@/components/states"
import { runStatusLabel } from "@/features/history/labels"
import { NOT_RECORDED, formatDateTime } from "@/lib/format"
import { apiErrorMessage, isApiError } from "@/services/api"
import { notRecordedFieldLabel } from "./labels"
import { ReportNotFound } from "./ReportNotFound"
import { useReportRun } from "./ReportRunContext"
import { EvaluationTab, EvidenceTab, GapsTab, OverviewTab, RecommendationsTab } from "./ReportTabs"
import { Tabs, type TabDef } from "./Tabs"
import type { RunDetail } from "./types"
import { useExportCsv } from "./useExportCsv"

/** /reports/:runId: container. Dữ liệu từ context (cùng một lần gọi API với panel Copilot). */
export default function ReportPage() {
  const run = useReportRun()
  if (!run) {
    return <ErrorState title="Không mở được báo cáo" message="Đường dẫn báo cáo không hợp lệ." />
  }
  if (run.phase === "error") {
    if (isApiError(run.error) && run.error.kind === "not_found") return <ReportNotFound />
    return <ErrorState title="Không tải được báo cáo" message={apiErrorMessage(run.error)} onRetry={() => void run.reload()} />
  }
  if (run.phase === "loading" || !run.data) {
    return <LoadingState label="Đang tải báo cáo..." onRetry={() => void run.reload()} />
  }
  return <ReportView detail={run.data} />
}

function ReportView({ detail }: { detail: RunDetail }) {
  const csv = useExportCsv(detail.run_id, detail.lesson_id)

  const tabs: TabDef[] = [
    { id: "overview", label: "Tổng quan", render: () => <OverviewTab detail={detail} /> },
    { id: "gaps", label: "Lỗ hổng", render: () => <GapsTab detail={detail} /> },
    { id: "recommendations", label: "Đề xuất", render: () => <RecommendationsTab detail={detail} /> },
    { id: "evaluation", label: "Đánh giá AI", render: () => <EvaluationTab detail={detail} /> },
    { id: "evidence", label: "Căn cứ", render: () => <EvidenceTab detail={detail} /> },
  ]

  return (
    <section aria-labelledby="report-title" className="mx-auto w-full max-w-5xl">
      <h1 id="report-title" className="text-2xl font-bold tracking-tight text-violet-950">
        Báo cáo bài {detail.lesson_id}
      </h1>
      <dl className="mt-3 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <Meta label="Tạo lúc" value={formatDateTime(detail.created_at)} />
        <Meta label="Trạng thái" value={runStatusLabel(detail.status)} />
        <Meta label="Có điểm JEV" value={`${detail.recommendations.filter((rec) => rec.jev_score != null).length} / ${detail.recommendations.length} đề xuất đã lưu`} />
        <Meta label="Phiên bản snapshot" value={detail.snapshot_version ?? NOT_RECORDED} />
      </dl>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button type="button" onClick={() => void csv.start()} disabled={csv.pending} className={stateButtonClass}>
          <Download aria-hidden="true" className="size-4" />
          {csv.pending ? "Đang tải CSV..." : "Tải CSV"}
        </button>
        <Link to={`/reports/${encodeURIComponent(detail.run_id)}/review`} className={stateSecondaryButtonClass}>
          <ListChecks aria-hidden="true" className="size-4" />
          Duyệt đề xuất
        </Link>
      </div>
      <div role="status" className="mt-2 empty:hidden">
        {csv.done && <p className="text-sm text-emerald-900">Đã tạo tệp {csv.done}. Kiểm tra thư mục tải xuống của trình duyệt.</p>}
      </div>
      {csv.error && (
        <p role="alert" className="mt-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">
          {csv.error}
        </p>
      )}

      {(detail.not_recorded.length > 0 || detail.snapshot.notice) && (
        <div role="note" className="mt-4 space-y-1 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950">
          {detail.not_recorded.length > 0 && (
            <p>
              Bản nháp cũ thiếu thông tin. Chưa được ghi nhận:{" "}
              <strong>{detail.not_recorded.map(notRecordedFieldLabel).join(", ")}</strong>. Các mục này không được suy diễn.
            </p>
          )}
          {detail.snapshot.notice && <p>{detail.snapshot.notice}</p>}
        </div>
      )}

      <div className="mt-6">
        <Tabs tabs={tabs} label="Nội dung báo cáo" />
      </div>
    </section>
  )
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <dt className="text-xs font-medium text-slate-700">{label}</dt>
      <dd className="break-words text-slate-900">{value}</dd>
    </div>
  )
}
