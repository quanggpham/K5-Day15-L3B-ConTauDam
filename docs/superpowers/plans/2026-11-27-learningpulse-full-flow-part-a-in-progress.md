# LearningPulse full flow — Phần A: đang làm (code API + UI)

> Tách từ `2026-11-27-learningpulse-full-flow.md`. Phần B (việc chia cho người thứ hai) ở `...-part-b-teammate.md`. Hai phần không sửa chung file; xem "Vùng file" bên dưới.
> Trạng thái: 2026-11-28 (cập nhật sau review). Chưa kiểm tay trên trình duyệt; hai migration chưa chạy thử trên Postgres thật.

## Vùng file của phần A (người B tránh)
`codebase/backend/`, `tests/`, `spec.md`, và logic frontend (`services/api.ts`, `hooks/`, `features/*/use*.ts`, `types.ts`, `features/auth/`).
Giao diện frontend (bố cục, kiểu dáng, `components/`, `style.css`) chuyển sang phần B (B14–B21); phần A chỉ sửa UI khi đổi hợp đồng API và sẽ báo trước.

## Đã làm xong (code, có test; thứ tự PR đề xuất)
- [x] A1. Snapshot v2, catalog, tổng hợp theo KC (mẫu số lượt đầu, <10 lượt gắn cờ, đồng hạng) - `analytics/`
- [x] A2. `GET /api/dashboard` - `api/dashboard.py`
- [x] A3. Migration `…03`: metadata run, audit duyệt, thu hồi quyền ghi của browser - `supabase/migrations/`
- [x] A4. `POST/GET /api/analysis-runs` idempotent + chi tiết - `api/analysis_runs.py`, `run_repository.py`
- [x] A5. `GET /api/analysis-runs/{id}/export` CSV chống công thức - `api/export.py`
- [x] A6. Migration `…04` RPC duyệt + `/reviews` + `/copilot` (4 thao tác cố định, cổng AI đóng) - `api/reviews.py`, `copilot.py`
- [x] A7. Frontend nền: router, auth, AppShell 3 cột, login, profile - `frontend/src/{app,features/auth,components}`
- [x] A8. Dashboard, tạo phân tích, lịch sử - `frontend/src/features/{dashboard,analysis,history}`
- [x] A9. Báo cáo 5 tab, panel Copilot, màn duyệt - `frontend/src/features/{reports,reviews}`
- [x] L1–L4. Landing page (hero, bài toán, luồng, minh hoạ, FAQ), nối route `/` - `frontend/src/features/landing`

## Đã làm thêm sau review (review-code + review-security)
- [x] A10. Test hồi quy 180 ca (quyền sở hữu, idempotency, CSV, 409, riêng tư) + test hợp đồng build_snapshot → báo cáo đã lưu - `tests/`
- [x] A10b. review-code: sửa BLOCKER (run lưu thiếu khoá LessonView → tab Tổng quan trống, Copilot khoá), delta/thứ tự bài (natural sort, chỉ so bài liền trước), KC 0% khỏi ưu tiên, cấu hình snapshot v2 khi deploy
- [x] A10c (một phần). Cursor sai → 422; allowlist cột trả về; replay RPC chỉ khi còn là trạng thái hiện tại

## Đã làm thêm (bảo mật, kiểm tra lại)
- [x] A10d (một phần). Hạn mức tạo run 20/phút/coach (429 + Retry-After); CSP + nosniff + X-Frame-Options + Referrer-Policy; thu hồi TRUNCATE của `service_role` trên bảng audit
- [x] A11. `spec.md` §10 có changelog sau CP2; checklist H01–H06 ở `docs/acceptance-h01-h06.md` (tất cả "Chưa kiểm")
- [x] L5. Landing đối chiếu câu chữ với tính năng thật, sửa thứ tự Tab nav
- [x] Dependency audit: `pip-audit` sạch; `pnpm audit --prod` 9 lỗ hổng đều ở `vite<=6.4.3` (dev server qua `@tailwindcss/vite`, không vào image production)

## Còn lại
- [ ] **Quyết định nhóm (k-anonymity)**: `spec.md` §10 có hai dòng mâu thuẫn (27/11 19:36 che nhóm <5 học viên; 21:01 hiện số tổng hợp mẫu nhỏ). Code đang theo dòng 21:01. KC có 1 học viên lộ đúng/sai của người đó. Chọn: (1) che KC <5 người, (2) che số lượt/tỷ lệ nhưng giữ cờ "mẫu nhỏ", (3) giữ nguyên + ghi chấp nhận rủi ro; rồi thay hai dòng bằng một dòng quyết định
- [ ] Nâng vite: chuyển `@tailwindcss/vite` sang `devDependencies` + override `vite ^6.4.4`, chạy lại `pnpm audit` và `pnpm build` (cần nhóm duyệt dependency)
- [ ] Thử CSP trên trình duyệt ở staging (Console có vi phạm khi vẽ biểu đồ/mở dialog không); thêm HSTS ở proxy Railway
- [ ] Việc nhỏ từ review: test cho replay chặt và đối chiếu allowlist SQL; luồng v1 (`analytics/workflow.py`, CLI) còn xếp KC 0% vào ưu tiên; hạn mức chỉ tính sau insert thành công và dọn khoá cũ; regex cho cursor ISO lạ; response 500 chưa có header bảo mật
- [ ] Chờ B1 (chạy thử migration `…03`/`…04` trên Postgres thật) rồi sửa lỗi SQL nếu có; nếu `…04` đã bị áp ở nơi dùng chung thì chuyển bản sửa sang `…05`
- [ ] Merge chuỗi PR theo thứ tự: #4 ✓, #5 ✓; frontend #7 → #8 → #10 → #11; backend #9 → #12; migration #6 (sau B1)

## Quy ước làm việc
- Mỗi bước một commit nhỏ; PR từng phần theo thứ tự trên, mỗi PR đủ CI (`pytest`, `pnpm build`, `docker build`).
- Merge vào `main` kích hoạt deploy Railway (`.github/workflows/deploy.yml`): chỉ merge khi đã test.
- Không sửa `eval/run-*.csv`, `cost/simulate-*.csv`, `traces/*`, `eval/metric_spec.yaml`, chuẩn "đạt" `spec.md` §7.
