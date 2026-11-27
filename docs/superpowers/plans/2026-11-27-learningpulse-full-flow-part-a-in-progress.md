# LearningPulse full flow — Phần A: đang làm (code API + UI)

> Tách từ `2026-11-27-learningpulse-full-flow.md`. Phần B (việc chia cho người thứ hai) ở `...-part-b-teammate.md`. Hai phần không sửa chung file; xem "Vùng file" bên dưới.
> Trạng thái: 2026-11-28. Chưa kiểm tay trên trình duyệt; hai migration chưa chạy thử trên Postgres thật.

## Vùng file của phần A (người B tránh)
`codebase/backend/api/`, `codebase/backend/analytics/`, `codebase/frontend/src/`, `tests/`, `spec.md`.

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

## Đang làm / còn lại
- [ ] A10. Test hồi quy (quyền sở hữu, idempotency, CSV, 409) - `tests/` (test-unit-lead đang chạy)
- [ ] A10b. `review-code` toàn diff (đang chạy)
- [ ] A10c. Sửa các phát hiện mức thấp của review-security:
  cursor sai → 400 thay vì 503; hạn mức tạo run/coach; allowlist cột trả về (recommendation/evaluations);
  `replayed` chỉ khi `new_version` = version hiện tại; ngưỡng số học viên (k-anonymity) cho trạng thái `ok`;
  CSP và header bảo mật cho SPA; cân nhắc revoke TRUNCATE trên bảng audit.
- [ ] A11. Ghi thay đổi sau CP2 vào `spec.md` §10; dựng bảng checklist H01–H06 (đánh dấu "Chưa kiểm")
- [ ] L5. Landing: đối chiếu lại câu "Hiện đã có", thứ tự Tab nav desktop, chụp thử desktop/mobile
- [ ] Chạy `pnpm audit --prod` và `pip-audit` (review-security chưa chạy được)

## Quy ước làm việc
- Mỗi bước một commit nhỏ; PR từng phần theo thứ tự trên, mỗi PR đủ CI (`pytest`, `pnpm build`, `docker build`).
- Merge vào `main` kích hoạt deploy Railway (`.github/workflows/deploy.yml`): chỉ merge khi đã test.
- Không sửa `eval/run-*.csv`, `cost/simulate-*.csv`, `traces/*`, `eval/metric_spec.yaml`, chuẩn "đạt" `spec.md` §7.
