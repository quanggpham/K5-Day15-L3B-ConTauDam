import { Badge } from "@/components/ui/badge"
import { EmptyState } from "@/components/states"

/** Màn hình chưa làm: không có số liệu hay trạng thái giả. */
export function ComingSoon({ title, description, detail }: { title: string; description: string; detail?: string }) {
  return (
    <section aria-labelledby="coming-soon-title" className="mx-auto w-full max-w-3xl">
      <div className="flex flex-wrap items-center gap-3">
        <h1 id="coming-soon-title" className="text-2xl font-bold tracking-tight text-violet-950">
          {title}
        </h1>
        <Badge variant="secondary" className="bg-violet-100 text-violet-900">
          Sắp có
        </Badge>
      </div>
      {detail && <p className="mt-2 break-all text-sm text-slate-600">{detail}</p>}
      <div className="mt-6 rounded-2xl border border-dashed border-violet-300 bg-white/70">
        <EmptyState title="Màn hình này chưa có dữ liệu để hiển thị" description={description} />
      </div>
    </section>
  )
}
