import { safeInternalPath } from "@/lib/safe-path"

export type ApiErrorKind =
  | "unauthorized" // 401: thiếu hoặc hết phiên
  | "forbidden" // 403: ngoài allowlist
  | "not_found" // 404: không tồn tại hoặc không thuộc coach
  | "conflict" // 409: xung đột (phiên bản cũ, request_id đã dùng)
  | "validation" // 400/422
  | "server" // 5xx
  | "network" // không tới được backend
  | "unknown"

export class ApiError extends Error {
  readonly kind: ApiErrorKind
  readonly status: number
  /** Thông điệp `detail` dạng chuỗi từ backend (nếu có). Không chứa token. */
  readonly detail: string | null
  /** `detail` dạng object từ backend (vd {code, message, ...} của 409/422), không có thì null. */
  readonly payload: Record<string, unknown> | null

  constructor(kind: ApiErrorKind, status: number, detail: string | null, payload: Record<string, unknown> | null = null) {
    super(detail ?? kind)
    this.name = "ApiError"
    this.kind = kind
    this.status = status
    this.detail = detail
    this.payload = payload
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError"
}

interface ApiHandlers {
  getAccessToken: () => string | null
  /** Gọi khi backend trả 401 cho request có gửi token (phiên hết hạn). */
  onUnauthorized: () => void
}

let handlers: ApiHandlers = { getAccessToken: () => null, onUnauthorized: () => {} }

/** AuthProvider đăng ký cách lấy token và xử lý 401. Không lưu token ở nơi khác. */
export function configureApi(next: Partial<ApiHandlers>): void {
  handlers = { ...handlers, ...next }
}

export interface RequestOptions {
  signal?: AbortSignal
  headers?: Record<string, string>
  /** Mặc định true: gửi Bearer nếu đang có phiên. */
  auth?: boolean
  query?: Record<string, string | number | undefined | null>
}

interface InternalOptions extends RequestOptions {
  method: "GET" | "POST"
  body?: unknown
}

function kindFromStatus(status: number): ApiErrorKind {
  if (status === 401) return "unauthorized"
  if (status === 403) return "forbidden"
  if (status === 404) return "not_found"
  if (status === 409) return "conflict"
  if (status === 400 || status === 422) return "validation"
  if (status >= 500) return "server"
  return "unknown"
}

async function readDetail(response: Response): Promise<{ detail: string | null; payload: Record<string, unknown> | null }> {
  try {
    const data: unknown = await response.json()
    if (data && typeof data === "object" && "detail" in data) {
      const { detail } = data as { detail: unknown }
      if (typeof detail === "string") return { detail, payload: null }
      if (detail && typeof detail === "object" && !Array.isArray(detail)) {
        return { detail: null, payload: detail as Record<string, unknown> }
      }
    }
  } catch {
    // Thân phản hồi không phải JSON: bỏ qua.
  }
  return { detail: null, payload: null }
}

/** Mã lỗi nghiệp vụ (`detail.code`) của 409/422 nếu backend có trả. */
export function apiErrorCode(error: unknown): string | null {
  if (!isApiError(error)) return null
  const code = error.payload?.code
  return typeof code === "string" ? code : null
}

/** Tên tệp từ Content-Disposition (ưu tiên filename*), đã bỏ ký tự đường dẫn; null nếu không có. */
export function filenameFromDisposition(header: string | null): string | null {
  if (!header) return null
  let name: string | null = null
  const star = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(header)
  if (star) {
    try {
      name = decodeURIComponent(star[1].trim())
    } catch {
      name = null
    }
  }
  if (!name) {
    const plain = /filename\s*=\s*(?:"([^"]*)"|([^;]+))/i.exec(header)
    name = (plain?.[1] ?? plain?.[2] ?? "").trim() || null
  }
  if (!name) return null
  const cleaned = name.replace(/[\\/:*?"<>|\u0000-\u001f]/g, "_").replace(/^\.+/, "").slice(0, 120)
  return cleaned || null
}

function buildUrl(path: string, query: RequestOptions["query"]): string {
  const safe = safeInternalPath(path)
  // Chặn gửi Bearer tới origin khác: chỉ nhận đường dẫn nội bộ.
  if (!safe) throw new ApiError("unknown", 0, "Đường dẫn API không hợp lệ")
  if (!query) return safe
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value))
  }
  const qs = params.toString()
  return qs ? `${safe}${safe.includes("?") ? "&" : "?"}${qs}` : safe
}

async function request(path: string, options: InternalOptions): Promise<Response> {
  const headers: Record<string, string> = { ...options.headers }
  const token = options.auth === false ? null : handlers.getAccessToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let body: BodyInit | undefined
  if (options.body !== undefined) {
    if (options.body instanceof FormData) body = options.body
    else {
      headers["Content-Type"] = "application/json"
      body = JSON.stringify(options.body)
    }
  }
  let response: Response
  try {
    response = await fetch(buildUrl(path, options.query), {
      method: options.method,
      headers,
      body,
      signal: options.signal,
    })
  } catch (error) {
    if (isAbortError(error)) throw error
    throw new ApiError("network", 0, null)
  }
  if (response.ok) return response
  const kind = kindFromStatus(response.status)
  const { detail, payload } = await readDetail(response)
  if (kind === "unauthorized" && token) handlers.onUnauthorized()
  throw new ApiError(kind, response.status, detail, payload)
}

async function requestJson<T>(path: string, options: InternalOptions): Promise<T> {
  const response = await request(path, options)
  if (response.status === 204) return undefined as T
  try {
    return (await response.json()) as T
  } catch {
    throw new ApiError("unknown", response.status, "Phản hồi không đọc được")
  }
}

export const api = {
  get: <T>(path: string, options: RequestOptions = {}) => requestJson<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options: RequestOptions = {}) =>
    requestJson<T>(path, { ...options, method: "POST", body }),
  /** Tải tệp (vd CSV export) kèm Bearer; trả Blob để UI tự kích hoạt tải xuống. */
  blob: async (path: string, options: RequestOptions = {}): Promise<Blob> =>
    (await request(path, { ...options, method: "GET" })).blob(),
  /** Như `blob` nhưng kèm tên tệp từ Content-Disposition (null nếu không có hoặc không đọc được header). */
  download: async (path: string, options: RequestOptions = {}): Promise<{ blob: Blob; filename: string | null }> => {
    const response = await request(path, { ...options, method: "GET" })
    try {
      return { blob: await response.blob(), filename: filenameFromDisposition(response.headers.get("Content-Disposition")) }
    } catch (error) {
      if (isAbortError(error)) throw error
      throw new ApiError("network", 0, null)
    }
  },
}

/** Thông điệp tiếng Việt, có hướng xử lý tiếp, cho từng loại lỗi. */
export function apiErrorMessage(error: unknown): string {
  if (!isApiError(error)) return "Có lỗi không xác định. Hãy thử lại."
  switch (error.kind) {
    case "unauthorized":
      return "Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại."
    case "forbidden":
      return "Tài khoản chưa được cấp quyền truy cập."
    case "not_found":
      return "Không tìm thấy dữ liệu, hoặc dữ liệu không thuộc tài khoản của bạn."
    case "conflict":
      return "Dữ liệu đã thay đổi hoặc bị trùng. Hãy tải lại rồi thử lại."
    case "validation":
      return "Yêu cầu không hợp lệ. Hãy kiểm tra thông tin rồi thử lại."
    case "server":
      return "Máy chủ đang gặp sự cố. Hãy thử lại sau ít phút."
    case "network":
      return "Không kết nối được backend. Hãy kiểm tra mạng rồi thử lại."
    default:
      return "Có lỗi không xác định. Hãy thử lại."
  }
}
