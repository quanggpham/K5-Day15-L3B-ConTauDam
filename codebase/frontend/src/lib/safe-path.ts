const PROBE_ORIGIN = "http://internal.invalid"

/**
 * Chỉ chấp nhận đường dẫn nội bộ của app (bắt đầu bằng "/", không phải "//").
 * Trả về null nếu giá trị có thể dẫn ra ngoài (open redirect) hoặc chứa ký tự lạ.
 */
export function safeInternalPath(value: unknown): string | null {
  if (typeof value !== "string" || value.length === 0 || value.length > 2048) return null
  if (!value.startsWith("/") || value.startsWith("//")) return null
  // Chặn "\" (trình duyệt coi như "/") và ký tự điều khiển (tab, xuống dòng...).
  // eslint-disable-next-line no-control-regex
  if (/[\\\u0000-\u001f\u007f]/.test(value)) return null
  try {
    if (new URL(value, PROBE_ORIGIN).origin !== PROBE_ORIGIN) return null
  } catch {
    return null
  }
  return value
}
