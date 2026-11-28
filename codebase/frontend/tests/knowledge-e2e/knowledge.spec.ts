import { test, expect } from "@playwright/test"

type Row = { id: string; lesson_id: string; kc_code: string; source: string; text: string; approved: boolean; version: number; reviewed_by: string | null; reviewed_at: string | null }

for (const screen of [{ name: "desktop", width: 1280, height: 800 }, { name: "mobile", width: 390, height: 844 }]) {
  test(`coach nạp, sửa, duyệt và tìm KB trên ${screen.name}`, async ({ page }) => {
    await page.setViewportSize({ width: screen.width, height: screen.height })
    let docs: Row[] = []
    const errors: string[] = []
    page.on("pageerror", error => errors.push(error.message))
    await page.route("**/api/knowledge**", async route => {
      const url = new URL(route.request().url())
      let payload: unknown
      if (url.pathname.endsWith("/catalog")) payload = [{ lesson_id: "L1", kc_code: "K1" }, { lesson_id: "L1", kc_code: "K2" }]
      else if (url.pathname.endsWith("/upload")) {
        docs = [{ id: "synthetic:1", lesson_id: "L1", kc_code: "K1", source: "Nguồn thử", text: "Khái niệm ban đầu", approved: false, version: 1, reviewed_by: null, reviewed_at: null }]
        payload = { chunks: 1, message: "Đã xử lý; các đoạn mới chờ duyệt." }
      } else if (url.pathname.endsWith("/edit")) {
        docs = docs.map(doc => ({ ...doc, ...route.request().postDataJSON(), approved: false, version: doc.version + 1 }))
        payload = docs[0]
      } else if (url.pathname.endsWith("/approve")) {
        docs = docs.map(doc => ({ ...doc, approved: true, reviewed_by: "synthetic-coach", reviewed_at: "2026-11-28T00:00:00Z", version: doc.version + 1 }))
        payload = docs[0]
      } else if (url.pathname.endsWith("/search")) payload = docs.filter(doc => doc.approved)
      else if (url.pathname.endsWith("/history")) payload = []
      else payload = { items: docs, has_more: false }
      await route.fulfill({ json: payload })
    })

    await page.goto("/tests/knowledge-e2e/")
    await expect(page.getByRole("heading", { name: "KB bài giảng" })).toBeVisible()
    await page.getByLabel("Nguồn được phép").fill("Nguồn thử")
    await page.getByLabel("Tệp PDF hoặc Markdown").setInputFiles({ name: "lesson.md", mimeType: "text/markdown", buffer: Buffer.from("Synthetic lesson") })
    await page.getByLabel("Tôi xác nhận có quyền sử dụng tài liệu này.").check()
    await page.getByRole("button", { name: "Tải lên" }).click()
    await expect(page.getByText(/Chờ coach duyệt · Phiên bản 1/)).toBeVisible()
    await page.getByRole("textbox", { name: "Nội dung", exact: true }).fill("Khái niệm đã sửa")
    await expect(page.getByRole("button", { name: "Duyệt bản đã lưu" })).toBeDisabled()
    await page.getByRole("button", { name: "Lưu thay đổi" }).click()
    await expect(page.getByText(/Chờ coach duyệt · Phiên bản 2/)).toBeVisible()
    await page.getByRole("button", { name: "Duyệt bản đã lưu" }).click()
    await expect(page.getByText(/Coach đã duyệt · Phiên bản 3/)).toBeVisible()
    await page.getByRole("combobox", { name: "KC", exact: true }).selectOption("K1")
    await page.getByRole("textbox", { name: "Nội dung cần tìm", exact: true }).fill("khái niệm")
    await page.getByRole("button", { name: "Tìm căn cứ" }).click()
    await expect(page.getByRole("listitem").getByText("Khái niệm đã sửa", { exact: true })).toBeVisible()
    await page.getByRole("button", { name: "Xem lịch sử" }).click()
    await expect(page.getByText("Chưa có phiên bản trước.")).toBeVisible()
    expect(errors).toEqual([])
  })
}
