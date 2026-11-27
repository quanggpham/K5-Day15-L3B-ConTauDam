/** Nhãn dùng khi payload không có trường: không thay bằng 0 hay giá trị suy diễn. */
export const NOT_RECORDED = "chưa được ghi nhận"

const dateTime = new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium", timeStyle: "short" })
const integer = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 })
const oneDecimal = new Intl.NumberFormat("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const signedOneDecimal = new Intl.NumberFormat("vi-VN", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
  signDisplay: "exceptZero",
})

export function isNum(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value)
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return NOT_RECORDED
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? NOT_RECORDED : dateTime.format(date)
}

/** Số đếm; thiếu -> "chưa được ghi nhận" (không phải 0). */
export function formatCount(value: number | null | undefined): string {
  return isNum(value) ? integer.format(value) : NOT_RECORDED
}

/** Tỷ lệ 0-1 -> "42,5%"; thiếu -> null để UI tự chọn trạng thái (vd mẫu số 0). */
export function formatRate(rate: number | null | undefined): string | null {
  return isNum(rate) ? `${oneDecimal.format(rate * 100)}%` : null
}

/** Điểm phần trăm có dấu: "+3,2" / "-30,0". */
export function formatSignedPp(value: number | null | undefined): string | null {
  return isNum(value) ? signedOneDecimal.format(value) : null
}
