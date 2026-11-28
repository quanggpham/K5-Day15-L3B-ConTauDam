import { useEffect, useState, type FormEvent } from "react"
import { api, apiErrorMessage, isApiError } from "@/services/api"

type Target = { lesson_id: string; kc_code: string }
type Document = { id: string; lesson_id: string; kc_code: string; text: string; source: string; approved: boolean; version: number; reviewed_by: string | null; reviewed_at: string | null }

export default function KnowledgePage() {
  const [catalog, setCatalog] = useState<Target[]>([])
  const [documents, setDocuments] = useState<Document[]>([])
  const [page, setPage] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [saved, setSaved] = useState<Record<string, string>>({})
  const [history, setHistory] = useState<Record<string, { version: number; changed_at: string; changed_by: string | null }[]>>({})
  const [lesson, setLesson] = useState("")
  const [source, setSource] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [searchKc, setSearchKc] = useState("")
  const [searchText, setSearchText] = useState("")
  const [results, setResults] = useState<Document[] | null>(null)
  const [permission, setPermission] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")
  const lessons = [...new Set(catalog.map(item => item.lesson_id))]

  async function load() {
    try {
      const [targets, rows] = await Promise.all([api.get<Target[]>("/api/knowledge/catalog"), api.get<{ items: Document[]; has_more: boolean }>("/api/knowledge", { query: { page } })])
      setCatalog(targets)
      setDocuments(rows.items)
      setHasMore(rows.has_more)
      setSaved(Object.fromEntries(rows.items.map(row => [row.id, JSON.stringify([row.text, row.lesson_id, row.kc_code, row.source])])))
      setLesson(current => current || targets[0]?.lesson_id || "")
      setError("")
    } catch (e) { setError(isApiError(e) && e.detail ? e.detail : apiErrorMessage(e)) }
  }
  useEffect(() => { void load() }, [page])

  async function upload(e: FormEvent) {
    e.preventDefault()
    if (!file || !permission) return
    const form = new FormData()
    form.append("file", file)
    form.append("lesson_id", lesson)
    form.append("source", source)
    form.append("permission_confirmed", "true")
    setBusy(true); setError(""); setMessage("")
    try {
      const result = await api.post<{ chunks: number; message: string }>("/api/knowledge/upload", form)
      setMessage(`${result.message} Đã xử lý ${result.chunks} đoạn.`)
      setResults(null)
      if (page === 0) await load()
      else setPage(0)
    } catch (e) { setError(isApiError(e) && e.detail ? e.detail : apiErrorMessage(e)) }
    finally { setBusy(false) }
  }

  async function save(doc: Document, approve: boolean) {
    setBusy(true); setError(""); setMessage("")
    try {
      const path = `/api/knowledge/${approve ? "approve" : "edit"}?document_id=${encodeURIComponent(doc.id)}`
      const body = approve ? { version: doc.version } : { version: doc.version, text: doc.text, lesson_id: doc.lesson_id, kc_code: doc.kc_code, source: doc.source }
      await api.post(path, body)
      setMessage(approve ? "Đã duyệt đoạn." : "Đã lưu; nếu nội dung thay đổi, đoạn cần duyệt lại.")
      setResults(null)
      await load()
    } catch (e) { setError(isApiError(e) && e.detail ? e.detail : apiErrorMessage(e)) }
    finally { setBusy(false) }
  }
  async function search(e: FormEvent) {
    e.preventDefault()
    setBusy(true); setError("")
    try {
      const matches = await api.get<Document[]>("/api/knowledge/search", { query: { lesson_id: lesson, kc_code: searchKc, query: searchText } })
      setResults(matches)
    } catch (e) { setError(isApiError(e) && e.detail ? e.detail : apiErrorMessage(e)) }
    finally { setBusy(false) }
  }
  async function showHistory(id: string) {
    try {
      const rows = await api.get<{ version: number; changed_at: string; changed_by: string | null }[]>(`/api/knowledge/history?document_id=${encodeURIComponent(id)}`)
      setHistory(current => ({ ...current, [id]: rows }))
    } catch (e) { setError(isApiError(e) && e.detail ? e.detail : apiErrorMessage(e)) }
  }
  function change(index: number, patch: Partial<Document>) {
    setDocuments(rows => rows.map((row, i) => i === index ? { ...row, ...patch } : row))
  }

  return <section className="mx-auto max-w-5xl space-y-6">
    <div><h1 className="text-2xl font-bold text-violet-950">KB bài giảng</h1><p className="mt-2 text-sm text-slate-600">Chỉ đoạn đã được coach xác nhận mới được dùng làm căn cứ. PDF scan chưa hỗ trợ OCR.</p></div>
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-800">{error}</p>}
    {message && <p role="status" className="rounded-lg bg-green-50 p-3 text-green-800">{message}</p>}
    <form onSubmit={upload} className="space-y-3 rounded-xl border border-violet-200 bg-white p-5">
      <h2 className="font-semibold">Tải tài liệu</h2>
      <label className="block text-sm">Bài học<select required value={lesson} onChange={e => { setLesson(e.target.value); setSearchKc(""); setResults(null) }} className="mt-1 block w-full rounded border p-2">{lessons.map(x => <option key={x}>{x}</option>)}</select></label>
      <label className="block text-sm">Nguồn được phép<input required maxLength={256} value={source} onChange={e => setSource(e.target.value)} className="mt-1 block w-full rounded border p-2" /></label>
      <label className="block text-sm">Tệp PDF hoặc Markdown<input required type="file" accept=".pdf,.md" onChange={e => setFile(e.target.files?.[0] ?? null)} className="mt-1 block w-full" /></label>
      <label className="flex gap-2 text-sm"><input required type="checkbox" checked={permission} onChange={e => setPermission(e.target.checked)} />Tôi xác nhận có quyền sử dụng tài liệu này.</label>
      <button disabled={busy || !lessons.length} className="rounded bg-violet-700 px-4 py-2 text-white disabled:opacity-50">{busy ? "Đang xử lý…" : "Tải lên"}</button>
    </form>
    <form onSubmit={search} className="space-y-3 rounded-xl border border-violet-200 bg-white p-5">
      <h2 className="font-semibold">Tìm trong KB đã duyệt</h2>
      <p className="text-sm text-slate-600">Tìm theo bài đang chọn ở trên và KC tương ứng.</p>
      <label className="block text-sm">KC<select required value={searchKc} onChange={e => setSearchKc(e.target.value)} className="mt-1 block w-full rounded border p-2"><option value="">Chọn KC</option>{catalog.filter(x => x.lesson_id === lesson).map(x => <option key={x.kc_code}>{x.kc_code}</option>)}</select></label>
      <label className="block text-sm">Nội dung cần tìm<input required maxLength={500} value={searchText} onChange={e => setSearchText(e.target.value)} className="mt-1 block w-full rounded border p-2" /></label>
      <button disabled={busy || !searchKc} className="rounded border border-violet-700 px-4 py-2 text-violet-800 disabled:opacity-50">Tìm căn cứ</button>
      {results && (results.length ? <ul className="space-y-3">{results.map(row => <li key={row.id} className="rounded bg-violet-50 p-3 text-sm"><p className="font-medium">{row.source}</p><p className="whitespace-pre-wrap">{row.text}</p></li>)}</ul> : <p role="status" className="text-sm">Chưa có căn cứ đã duyệt cho bài và KC này.</p>)}
    </form>
    <h2 className="text-lg font-semibold">Các đoạn ({documents.length})</h2>
    {documents.length === 0 && <p className="text-sm text-slate-600">Chưa có đoạn bài giảng.</p>}
    <div className="flex items-center gap-3"><button disabled={page === 0 || busy} onClick={() => setPage(page - 1)} className="rounded border px-3 py-2 disabled:opacity-50">Trang trước</button><span>Trang {page + 1}</span><button disabled={!hasMore || busy} onClick={() => setPage(page + 1)} className="rounded border px-3 py-2 disabled:opacity-50">Trang sau</button></div>
    {documents.map((doc, index) => <article key={doc.id} className="space-y-3 rounded-xl border border-violet-200 bg-white p-5">
      <p className="text-sm font-medium">{doc.approved ? "Đã duyệt" : "Chờ duyệt"} · Phiên bản {doc.version}{doc.reviewed_at ? ` · ${new Date(doc.reviewed_at).toLocaleString("vi-VN")} · người duyệt: ${doc.reviewed_by ?? "không xác định"}` : ""}</p>
      <label className="block text-sm">Nguồn<input value={doc.source} maxLength={256} onChange={e => change(index, { source: e.target.value })} className="mt-1 block w-full rounded border p-2" /></label>
      <label className="block text-sm">Bài học<select value={doc.lesson_id} onChange={e => change(index, { lesson_id: e.target.value, kc_code: catalog.find(x => x.lesson_id === e.target.value)?.kc_code ?? "" })} className="mt-1 block w-full rounded border p-2">{lessons.map(x => <option key={x}>{x}</option>)}</select></label>
      <label className="block text-sm">KC (đề xuất; hãy kiểm tra)<select value={doc.kc_code} onChange={e => change(index, { kc_code: e.target.value })} className="mt-1 block w-full rounded border p-2">{catalog.filter(x => x.lesson_id === doc.lesson_id).map(x => <option key={x.kc_code}>{x.kc_code}</option>)}</select></label>
      <label className="block text-sm">Nội dung<textarea value={doc.text} maxLength={8000} rows={5} onChange={e => change(index, { text: e.target.value })} className="mt-1 block w-full rounded border p-2" /></label>
      <div className="flex gap-3"><button disabled={busy} onClick={() => void save(doc, false)} className="rounded border border-violet-700 px-3 py-2 text-violet-800 disabled:opacity-50">Lưu thay đổi</button><button disabled={busy || doc.approved || saved[doc.id] !== JSON.stringify([doc.text, doc.lesson_id, doc.kc_code, doc.source])} onClick={() => void save(doc, true)} className="rounded bg-violet-700 px-3 py-2 text-white disabled:opacity-50">Duyệt bản đã lưu</button></div>
    <button onClick={() => void showHistory(doc.id)} className="text-sm text-violet-800 underline">Xem lịch sử</button>
      {history[doc.id] && <ul className="space-y-1 text-sm">{history[doc.id].length === 0 ? <li>Chưa có phiên bản trước.</li> : history[doc.id].map((entry, i) => <li key={`${entry.version}-${i}`}>Phiên bản {entry.version} · {new Date(entry.changed_at).toLocaleString("vi-VN")} · người thay đổi: {entry.changed_by ?? "không xác định"}</li>)}</ul>}
    </article>)}
  </section>
}
