import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useReportRun } from "./ReportRunContext"
import { api, apiErrorMessage, isAbortError, isApiError } from "@/services/api"

type Preview = { save_token: string; status: string; kc_code: string; content: string; model: string; tokens_in: number; tokens_out: number; sources: { id: string; text: string; source?: string }[] }

export default function DemoPreview({ runId, kcCode }: { runId: string; kcCode: string }) {
  const navigate = useNavigate()
  const run = useReportRun()
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState<Preview | null>(null)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const controller = useRef<AbortController | null>(null)
  useEffect(() => {
    controller.current?.abort()
    setResult(null); setError(""); setBusy(false)
    return () => controller.current?.abort()
  }, [runId, kcCode])

  async function generate() {
    if (!kcCode || busy) return
    const request = new AbortController()
    controller.current = request
    setBusy(true); setError(""); setResult(null)
    try {
      const data = await api.post<Preview>(`/api/analysis-runs/${encodeURIComponent(runId)}/demo-preview`, { kc_code: kcCode }, { signal: request.signal })
      if (!request.signal.aborted) setResult(data)
    } catch (e) {
      if (!isAbortError(e) && !request.signal.aborted) setError(isApiError(e) && e.detail ? e.detail : apiErrorMessage(e))
    } finally {
      if (!request.signal.aborted) setBusy(false)
    }
  }

  async function save() {
    if (!result || saving) return
    setSaving(true); setError("")
    try {
      await api.post(`/api/analysis-runs/${encodeURIComponent(runId)}/demo-preview/save`, { token: result.save_token })
      await run?.reload()
      navigate(`/reports/${encodeURIComponent(runId)}/review`)
    } catch (e) {
      setError(isApiError(e) && e.detail ? e.detail : apiErrorMessage(e))
    } finally { setSaving(false) }
  }

  return <section className="space-y-2 rounded-lg border border-amber-300 bg-amber-50 p-3" aria-label="Bản nháp AI demo">
    <h3 className="text-sm font-semibold text-amber-950">Bản nháp AI demo</h3>
    <p className="text-xs text-amber-950">Chưa hiệu chuẩn JEV, cần coach kiểm tra. Kết quả không tự lưu hoặc duyệt.</p>
    <button type="button" onClick={() => void generate()} disabled={!kcCode || busy || saving}
      className="w-full rounded-lg bg-violet-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">
      {busy ? "Đang gọi AI…" : "Tạo bản nháp cho KC đã chọn"}
    </button>
    {!kcCode && <p className="text-xs text-amber-950">Chọn KC đủ mẫu và có căn cứ đã duyệt ở phía trên.</p>}
    {error && <p role="alert" className="text-sm text-red-800">{error}</p>}
    {result && <div className="space-y-2 text-sm text-slate-900" role="status">
      <p className="whitespace-pre-wrap break-words">{result.content}</p>
      <p className="text-xs">Model: {result.model} · Token vào/ra: {result.tokens_in}/{result.tokens_out}</p>
      <p className="text-xs font-semibold">Nguồn đã trích dẫn:</p>
      <ul className="space-y-2">{result.sources.map(source => <li key={source.id} className="rounded bg-white p-2 text-xs">
        <p className="break-all font-medium">{source.source || source.id}</p>
        <p className="whitespace-pre-wrap break-words">{source.text}</p>
      </li>)}</ul>
      <button type="button" onClick={() => void save()} disabled={saving}
        className="rounded-lg border border-violet-700 px-3 py-2 font-semibold text-violet-800 disabled:opacity-50">
        {saving ? "Đang lưu…" : "Lưu bản nháp để duyệt"}
      </button>
    </div>}
  </section>
}
