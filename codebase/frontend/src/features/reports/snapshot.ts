import type { LessonView } from "@/features/dashboard/types"
import { NOT_RECORDED } from "@/lib/format"
import { RUN_SNAPSHOT_SCHEMA, type RunDetail, type StoredSnapshot } from "./types"

export type StoredSnapshotResult =
  | { state: "ok"; snapshot: StoredSnapshot; lesson: LessonView }
  | { state: "unavailable"; notice: string }

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

/** Đủ các trường mà MetricCards/KcSection cần; thiếu thì coi là không dùng được (không điền 0). */
export function isLessonView(value: unknown): value is LessonView {
  if (!isObject(value)) return false
  return isObject(value.sample) && isObject(value.distribution) && Array.isArray(value.kcs) && Array.isArray(value.priority)
}

/** Chỉ snapshot đúng định dạng hiện hành mới hiển thị số liệu; còn lại hiện thông báo của backend, không quy đổi. */
export function readStoredSnapshot(detail: RunDetail): StoredSnapshotResult {
  const view = detail.snapshot
  if (view?.format === RUN_SNAPSHOT_SCHEMA && isObject(view.data) && isLessonView(view.data.lesson)) {
    return { state: "ok", snapshot: view.data as unknown as StoredSnapshot, lesson: view.data.lesson }
  }
  if (view?.notice) return { state: "unavailable", notice: view.notice }
  if (view?.format === RUN_SNAPSHOT_SCHEMA) {
    return { state: "unavailable", notice: "Snapshot đã lưu thiếu dữ liệu bài học nên không hiển thị được số liệu." }
  }
  return { state: "unavailable", notice: `Snapshot số liệu ${NOT_RECORDED}.` }
}
