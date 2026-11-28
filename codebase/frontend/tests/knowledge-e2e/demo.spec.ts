import { test, expect } from "@playwright/test"

test("bản nháp demo hiển thị cảnh báo, output và nguồn", async ({ page }) => {
  await page.route("**/api/analysis-runs/*/demo-preview", async route => {
    expect(route.request().postDataJSON()).toEqual({ kc_code: "K1" })
    await route.fulfill({ json: { save_token: "synthetic-token", status: "demo_unvalidated", kc_code: "K1", content: "Ôn tập bằng ví dụ.",
      model: "lfm3-1.7b", tokens_in: 10, tokens_out: 5, sources: [{ id: "d1", text: "Ví dụ đã duyệt", source: "Bài giảng" }] } })
  })
  await page.route("**/api/analysis-runs/*/demo-preview/save", async route => {
    expect(route.request().postDataJSON()).toEqual({ token: "synthetic-token" })
    await route.fulfill({ json: { recommendation_id: "synthetic-rec" } })
  })
  await page.goto("/tests/knowledge-e2e/demo.html")
  await expect(page.getByText(/Chưa hiệu chuẩn JEV/)).toBeVisible()
  await page.getByRole("button", { name: "Tạo bản nháp cho KC đã chọn" }).click()
  await expect(page.getByText("Ôn tập bằng ví dụ.")).toBeVisible()
  await expect(page.getByText("Ví dụ đã duyệt")).toBeVisible()
  await expect(page.getByText(/Token vào\/ra: 10\/5/)).toBeVisible()
  await page.getByRole("button", { name: "Lưu bản nháp để duyệt" }).click()
  await expect(page.getByRole("heading", { name: "Duyệt đề xuất" })).toBeVisible()
})
