import { formatCount, formatRate, formatSignedPp } from "@/lib/format"
import type { KcStat } from "./types"

export type KcKind = "ok" | "low" | "empty" | "masked"

/** Phân loại hiển thị: đủ mẫu / chưa đủ dữ liệu (<min lượt) / mẫu số 0 / nhóm nhỏ (<5 người, số liệu bị ẩn). */
export function kcKind(kc: KcStat): KcKind {
  if (kc.status === "small_group") return "masked"
  if (kc.status === "no_graded" || kc.incorrect_rate === null) return "empty"
  return kc.status === "insufficient_sample" ? "low" : "ok"
}

export function kcStatusLabel(kc: KcStat, minSample?: number | null): string {
  const kind = kcKind(kc)
  if (kind === "masked") return "Nhóm nhỏ (dưới 5 người): số liệu được ẩn"
  if (kind === "empty") return "Mẫu số 0: chưa có lượt chấm"
  if (kind === "low") return `Chưa đủ dữ liệu (dưới ${formatCount(minSample)} lượt)`
  return "Đủ mẫu"
}

export interface KcChartRow {
  kc: string
  kind: Exclude<KcKind, "empty" | "masked">
  /** Tỷ lệ sai theo phần trăm (0-100). */
  percent: number
  sufficient: number | null
  insufficient: number | null
  graded: number | null | undefined
}

/** Chỉ KC có tỷ lệ (mẫu số > 0) mới được vẽ; mẫu số 0 không vẽ cột 0%. */
export function toChartRows(kcs: KcStat[]): KcChartRow[] {
  return kcs.flatMap((kc) => {
    const kind = kcKind(kc)
    if (kind === "empty" || kind === "masked" || kc.incorrect_rate === null) return []
    const percent = Math.round(kc.incorrect_rate * 1000) / 10
    return [
      {
        kc: kc.kc_code,
        kind,
        percent,
        sufficient: kind === "ok" ? percent : null,
        insufficient: kind === "low" ? percent : null,
        graded: kc.graded_count,
      },
    ]
  })
}

export function rateText(kc: KcStat): string {
  return formatRate(kc.incorrect_rate) ?? "—"
}

export function deltaText(kc: KcStat): string {
  const value = formatSignedPp(kc.delta_vs_previous_pp)
  return value ? `${value} điểm %` : "—"
}

