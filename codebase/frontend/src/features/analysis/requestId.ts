/**
 * request_id idempotency cho POST /api/analysis-runs.
 * Một id cho mỗi (coach, bài): giữ nguyên khi thử lại, chỉ tạo mới sau khi tạo thành công, khi 409, hoặc khi đổi bài (khoá khác).
 * Lưu sessionStorage để reload không tạo bản nháp trùng; nếu storage bị chặn thì dùng bộ nhớ tạm.
 */
const memory = new Map<string, string>()

function storage(): Storage | null {
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}

const storageKey = (userId: string, lessonId: string) => `lp:analysis-request:${userId}:${lessonId}`

export function generateRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID()
  // Ngữ cảnh không an toàn (http thường) không có randomUUID: UUID v4 từ getRandomValues.
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 0x0f) | 0x40
  bytes[8] = (bytes[8] & 0x3f) | 0x80
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("")
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

function read(key: string): string | null {
  try {
    return storage()?.getItem(key) ?? memory.get(key) ?? null
  } catch {
    return memory.get(key) ?? null
  }
}

function write(key: string, value: string): void {
  memory.set(key, value)
  try {
    storage()?.setItem(key, value)
  } catch {
    // Storage đầy/bị chặn: đã có bản trong bộ nhớ.
  }
}

/** Id hiện có của (coach, bài); chưa có thì tạo và lưu. */
export function getRequestId(userId: string, lessonId: string): string {
  const key = storageKey(userId, lessonId)
  const existing = read(key)
  if (existing) return existing
  const created = generateRequestId()
  write(key, created)
  return created
}

/** Bỏ id sau khi tạo thành công: lần phân tích kế tiếp là thao tác mới. */
export function clearRequestId(userId: string, lessonId: string): void {
  const key = storageKey(userId, lessonId)
  memory.delete(key)
  try {
    storage()?.removeItem(key)
  } catch {
    // bỏ qua
  }
}

/** Thay bằng id mới (khi 409: id cũ đã gắn với bài khác). */
export function replaceRequestId(userId: string, lessonId: string): string {
  const created = generateRequestId()
  write(storageKey(userId, lessonId), created)
  return created
}
