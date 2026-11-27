import { NOT_RECORDED } from "@/lib/format"

/** Chuỗi hiển thị cho giá trị jsonb (điểm JEV, metrics, evidence): giữ nguyên số liệu, không làm tròn hay suy diễn. */
export function valueText(value: unknown): string {
  if (value === null || value === undefined) return NOT_RECORDED
  if (typeof value === "string") return value
  if (typeof value === "number" || typeof value === "boolean") return String(value)
  try {
    return JSON.stringify(value)
  } catch {
    return NOT_RECORDED
  }
}

/** Object phẳng -> các cặp [khoá, giá trị]; không phải object (hoặc rỗng) -> null. */
export function entriesOf(value: unknown): Array<[string, string]> | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null
  const entries = Object.entries(value as Record<string, unknown>)
  return entries.length ? entries.map(([key, item]) => [key, valueText(item)]) : null
}

export interface CitationView {
  key: string
  text: string
  /** Chỉ http(s) mới thành liên kết; còn lại hiện dạng chữ. */
  href: string | null
}

const CITATION_KEYS = ["source_id", "title", "source"] as const

/** Căn cứ thật sự có trong đề xuất; không có -> mảng rỗng (không bịa nguồn). */
export function citationsOf(value: unknown): CitationView[] {
  if (!Array.isArray(value)) return []
  const out: CitationView[] = []
  value.forEach((item, index) => {
    if (typeof item === "string") {
      if (item.trim()) out.push({ key: `${index}:${item}`, text: item, href: null })
      return
    }
    if (typeof item === "object" && item !== null) {
      const record = item as Record<string, unknown>
      const parts = CITATION_KEYS.flatMap((key) => (typeof record[key] === "string" && record[key] ? [record[key] as string] : []))
      const url = typeof record.url === "string" && /^https?:\/\//i.test(record.url) ? record.url : null
      const text = parts.join(" · ") || (typeof record.url === "string" ? record.url : valueText(item))
      out.push({ key: `${index}:${text}`, text, href: url })
    }
  })
  return out
}
