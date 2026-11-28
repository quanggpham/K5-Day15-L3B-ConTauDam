import { useEffect, useId, useRef, useState } from "react"
import { Link } from "react-router-dom"
import { stateButtonClass, stateSecondaryButtonClass } from "@/components/states"
import { cardClass, controlClass, labelClass } from "@/components/ui/controls"
import { EditedFlag, JevScore, ReviewStatusChip, kcLabel } from "@/features/reports/RecommendationBits"
import { decisionLabel, reviewStatusLabel, type ReviewDecision } from "@/features/reports/labels"
import type { RecommendationItem, ReviewItem, ReviewResponse } from "@/features/reports/types"
import { NOT_RECORDED } from "@/lib/format"
import { ReviewHistory } from "./ReviewHistory"
import { MAX_COMMENT, MAX_CONTENT, allowedDecisions } from "./reviewMachine"
import { useSubmitReview, type SubmitOutcome } from "./useSubmitReview"

type Feedback =
  | SubmitOutcome
  | { kind: "client"; message: string }
  | { kind: "reloaded"; draftKept: boolean }
  | { kind: "reload_failed" }

interface Props {
  runId: string
  rec: RecommendationItem
  reviews: ReviewItem[]
  currentUserId: string | null
  onApplied: (result: ReviewResponse) => void
  /** Tải lại chi tiết báo cáo; true nếu thành công. */
  onReload: () => Promise<boolean>
}

const textareaClass =
  "w-full rounded-lg border border-violet-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-violet-600 disabled:cursor-not-allowed disabled:bg-slate-100"

/**
 * Duyệt một đề xuất. Giữ nội dung đang soạn (nhận xét, bản sửa) qua mọi lỗi và qua lần tải lại sau xung đột,
 * không ghi đè im lặng. Quyết định gửi kèm `version` của đề xuất đang hiển thị.
 */
export function RecommendationReviewCard({ runId, rec, reviews, currentUserId, onApplied, onReload }: Props) {
  const ids = useId()
  const [comment, setComment] = useState("")
  const [contentDraft, setContentDraft] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [reloading, setReloading] = useState(false)
  const feedbackRef = useRef<HTMLDivElement>(null)
  const contentRef = useRef<HTMLTextAreaElement>(null)
  const { submit, retry, pending } = useSubmitReview(runId, onApplied)

  // Nút vừa bấm bị khoá khi đang gửi nên mất focus: đưa focus tới kết quả để bàn phím/đọc màn hình không bị lạc.
  useEffect(() => {
    if (feedback && !pending) feedbackRef.current?.focus()
  }, [feedback, pending])

  const allowed = allowedDecisions(rec.review_status)
  const canEdit = allowed.includes("edited")
  const conflict = feedback?.kind === "conflict"
  const version = typeof rec.version === "number" ? rec.version : null
  const locked = pending || reloading || conflict || version === null
  const demoSources = Array.isArray(rec.citations) ? rec.citations.filter(
    (source) => source?.origin === "demo_unvalidated"
  ) : []
  const contentValue = contentDraft ?? rec.content ?? ""
  const hasDraft = contentDraft !== null && contentDraft !== (rec.content ?? "")

  function handleOutcome(outcome: SubmitOutcome | null) {
    if (!outcome) return
    if (outcome.kind === "saved") {
      setComment("")
      setContentDraft(null)
    }
    setFeedback(outcome)
  }

  async function decide(decision: ReviewDecision) {
    if (locked || version === null) return
    const trimmed = comment.trim()
    if (comment.length > MAX_COMMENT) {
      setFeedback({ kind: "client", message: `Nhận xét dài quá ${MAX_COMMENT} ký tự. Hãy rút gọn.` })
      return
    }
    const payload = { recommendation_id: rec.id, version, decision, ...(trimmed ? { comment: trimmed } : {}) }
    if (decision === "edited") {
      if (!contentValue.trim()) {
        setFeedback({ kind: "client", message: "Nội dung bản sửa không được để trống." })
        contentRef.current?.focus()
        return
      }
      if (contentValue.length > MAX_CONTENT) {
        setFeedback({ kind: "client", message: `Nội dung bản sửa dài quá ${MAX_CONTENT} ký tự. Hãy rút gọn.` })
        contentRef.current?.focus()
        return
      }
      handleOutcome(await submit({ ...payload, content: contentValue }))
      return
    }
    handleOutcome(await submit(payload))
  }

  async function reload() {
    if (reloading) return
    setReloading(true)
    const ok = await onReload()
    setReloading(false)
    setFeedback(ok ? { kind: "reloaded", draftKept: hasDraft || comment.trim() !== "" } : { kind: "reload_failed" })
  }

  const statusKnown = allowed.length > 0
  const titleId = `${ids}-title`
  return (
    <article aria-labelledby={titleId} className={`${cardClass} space-y-4`}>
      <header className="flex flex-wrap items-center gap-2">
        <h2 id={titleId} className="text-base font-semibold text-violet-950">
          {kcLabel(rec)}
          {demoSources.length === 0 && rec.priority != null && <span className="font-normal text-slate-700"> · ưu tiên {rec.priority}</span>}
        </h2>
        <ReviewStatusChip status={rec.review_status} />
        <span className="text-xs text-slate-700">Phiên bản {version ?? NOT_RECORDED}</span>
      </header>

      {demoSources.length > 0 && <p className="text-sm font-medium text-amber-900">Bản nháp AI demo · Chưa hiệu chuẩn JEV</p>}
      <p className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-900">{rec.content ?? NOT_RECORDED}</p>
      {demoSources.length > 0 && <details className="text-sm">
        <summary className="cursor-pointer font-medium">Nguồn đã trích dẫn</summary>
        <ul className="space-y-2">{demoSources.map((source) => <li key={source.source_id}>
          <p className="font-medium">{source.source} · {source.source_id}</p>
          <p className="whitespace-pre-wrap break-words">{source.text}</p>
        </li>)}</ul>
      </details>}
      <div className="space-y-2">
        <EditedFlag rec={rec} />
        <JevScore rec={rec} />
        {(rec.not_recorded?.length ?? 0) > 0 && (
          <p className="text-xs text-slate-700">Trạng thái duyệt chưa được ghi nhận: coi như chưa duyệt.</p>
        )}
      </div>

      {!statusKnown ? (
        <p role="note" className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950">
          Trạng thái duyệt "{reviewStatusLabel(rec.review_status)}" chưa được giao diện nhận diện nên chưa thể duyệt ở đây.
          <button type="button" onClick={() => void reload()} disabled={reloading} className="ml-2 font-medium underline">
            Tải lại
          </button>
        </p>
      ) : version === null ? (
        <p role="note" className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950">
          Phiên bản của đề xuất {NOT_RECORDED} nên chưa thể gửi quyết định.
        </p>
      ) : (
        <form
          className="space-y-3"
          aria-label={`Duyệt ${kcLabel(rec)}`}
          onSubmit={(event) => event.preventDefault()}
          aria-busy={pending}
        >
          <div>
            <label htmlFor={`${ids}-comment`} className={labelClass}>
              Nhận xét (tuỳ chọn, tối đa {MAX_COMMENT} ký tự)
            </label>
            <textarea
              id={`${ids}-comment`}
              rows={2}
              maxLength={MAX_COMMENT}
              value={comment}
              disabled={pending}
              onChange={(event) => setComment(event.target.value)}
              className={textareaClass}
            />
            <p className="mt-1 text-right text-xs text-slate-700">
              {comment.length}/{MAX_COMMENT}
            </p>
          </div>

          {canEdit && (
            <div className="space-y-2 rounded-lg border border-violet-100 bg-violet-50/50 p-3">
              <label htmlFor={`${ids}-content`} className={labelClass}>
                Nội dung bản sửa tay (tối đa {MAX_CONTENT} ký tự)
              </label>
              <p className="text-xs text-slate-700">
                {rec.review_status === "changes_requested"
                  ? "Bạn đã yêu cầu chỉnh sửa: hãy sửa tay nội dung rồi lưu, hoặc từ chối đề xuất."
                  : "Bản sửa tay cần được duyệt lại và không có điểm JEV của bản gốc."}
              </p>
              <textarea
                id={`${ids}-content`}
                ref={contentRef}
                rows={6}
                maxLength={MAX_CONTENT}
                value={contentValue}
                disabled={pending}
                onChange={(event) => setContentDraft(event.target.value)}
                className={textareaClass}
              />
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs text-slate-700">
                  {contentValue.length}/{MAX_CONTENT}
                </span>
                <button type="button" onClick={() => void decide("edited")} disabled={locked} className={stateButtonClass}>
                  {pending ? "Đang lưu..." : decisionLabel("edited")}
                </button>
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            {allowed
              .filter((decision) => decision !== "edited")
              .map((decision) => (
                <button
                  key={decision}
                  type="button"
                  onClick={() => void decide(decision)}
                  disabled={locked}
                  className={decision === "accept" ? stateButtonClass : stateSecondaryButtonClass}
                >
                  {decisionLabel(decision)}
                </button>
              ))}
          </div>
          {conflict && (
            <p className="text-xs text-slate-700">Các nút quyết định tạm khoá cho tới khi bạn tải lại đề xuất.</p>
          )}
        </form>
      )}

      {feedback?.kind === "reloaded" && feedback.draftKept && !canEdit && contentDraft !== null && (
        <div className="rounded-lg border border-violet-200 bg-violet-50 p-3">
          <p className="text-xs font-semibold text-slate-700">Bản sửa bạn đang soạn (giữ lại để đối chiếu, chưa được lưu)</p>
          <p className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-900">{contentDraft}</p>
        </div>
      )}

      <div ref={feedbackRef} tabIndex={-1} className="outline-none focus-visible:ring-2 focus-visible:ring-violet-700">
        <FeedbackMessage
          feedback={feedback}
          rec={rec}
          reloading={reloading}
          pending={pending}
          onReload={() => void reload()}
          onRetry={() => void retry().then(handleOutcome)}
        />
      </div>

      <ReviewHistory reviews={reviews} currentUserId={currentUserId} />
    </article>
  )
}

const alertClass = "rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900"
const warnClass = "rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950"
const okClass = "rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-950"
const inlineButton = `${stateSecondaryButtonClass} mt-2 h-9 text-xs`

function FeedbackMessage({
  feedback,
  rec,
  reloading,
  pending,
  onReload,
  onRetry,
}: {
  feedback: Feedback | null
  rec: RecommendationItem
  reloading: boolean
  pending: boolean
  onReload: () => void
  onRetry: () => void
}) {
  if (reloading) return <p role="status" className="text-sm text-slate-700">Đang tải lại đề xuất mới nhất...</p>
  if (pending) return <p role="status" className="text-sm text-slate-700">Đang lưu quyết định...</p>
  if (!feedback) return null
  switch (feedback.kind) {
    case "saved":
      return (
        <p role="status" className={okClass}>
          {feedback.replayed
            ? `Quyết định "${decisionLabel(feedback.decision)}" đã được ghi nhận trước đó, không ghi trùng.`
            : `Đã lưu: ${decisionLabel(feedback.decision)}.`}
        </p>
      )
    case "client":
      return <p role="alert" className={alertClass}>{feedback.message}</p>
    case "conflict":
      return (
        <div role="alert" className={warnClass}>
          <p className="font-semibold">Đã có người thay đổi đề xuất này.</p>
          <p className="mt-1">
            Bạn đang xem phiên bản {rec.version ?? NOT_RECORDED}
            {feedback.currentVersion !== null ? `, phiên bản hiện tại là ${feedback.currentVersion}` : ""}
            {feedback.currentStatus ? ` (trạng thái: ${reviewStatusLabel(feedback.currentStatus)})` : ""}. Quyết định của bạn chưa được lưu. Nhận xét và bản sửa
            đang soạn được giữ nguyên; hãy tải lại, đối chiếu rồi chọn lại.
          </p>
          <button type="button" onClick={onReload} className={inlineButton}>
            Tải lại
          </button>
        </div>
      )
    case "reloaded":
      return (
        <p role="status" className={okClass}>
          Đã tải lại đề xuất mới nhất (phiên bản {rec.version ?? NOT_RECORDED}, trạng thái: {reviewStatusLabel(rec.review_status)}).{" "}
          {feedback.draftKept
            ? "Nội dung bạn đang soạn vẫn được giữ lại để đối chiếu; chưa có gì bị ghi đè."
            : "Hãy đối chiếu rồi chọn quyết định."}
        </p>
      )
    case "reload_failed":
      return (
        <div role="alert" className={alertClass}>
          <p>Chưa tải lại được đề xuất. Nội dung đang soạn của bạn vẫn còn nguyên.</p>
          <button type="button" onClick={onReload} className={inlineButton}>
            Tải lại
          </button>
        </div>
      )
    case "invalid_transition":
      return (
        <div role="alert" className={warnClass}>
          <p>
            Quyết định này không còn hợp lệ ở trạng thái hiện tại
            {feedback.status ? ` (${reviewStatusLabel(feedback.status)})` : ""}. Hãy tải lại để xem trạng thái mới nhất.
          </p>
          <button type="button" onClick={onReload} className={inlineButton}>
            Tải lại
          </button>
        </div>
      )
    case "invalid_input":
      return (
        <p role="alert" className={alertClass}>
          Dữ liệu duyệt không hợp lệ (nhận xét tối đa {MAX_COMMENT} ký tự, bản sửa tối đa {MAX_CONTENT} ký tự và không được trống). Hãy kiểm tra rồi thử lại.
        </p>
      )
    case "not_found":
      return (
        <div role="alert" className={alertClass}>
          <p>Không tìm thấy đề xuất hoặc báo cáo này. Hãy mở lại từ Lịch sử.</p>
          <Link to="/history" className={inlineButton}>
            Về Lịch sử
          </Link>
        </div>
      )
    case "retryable":
      return (
        <div role="alert" className={alertClass}>
          <p>{feedback.message}</p>
          <button type="button" onClick={onRetry} className={inlineButton}>
            Thử lại
          </button>
        </div>
      )
    case "error":
      return <p role="alert" className={alertClass}>{feedback.message}</p>
  }
}
