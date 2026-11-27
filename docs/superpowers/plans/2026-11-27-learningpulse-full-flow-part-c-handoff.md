# LearningPulse full flow — Phần C: bàn giao việc A chưa xong

> Người C làm tiếp những việc còn dang dở của phần A (xem `...-part-a-in-progress.md`). Phần B (benchmark, KB, hạ tầng, UI) giữ nguyên.
> Trạng thái: 2026-11-28. Toàn bộ code của A đã nằm trong PR, **chưa merge** (trừ #4, #5). Chưa deploy hạ tầng thật.

## Đọc trước
`AGENTS.md`, `.claude/rules/learningpulse.md` nếu có, `data/DATA_CARD.md`, `spec.md` §7 và §10, `docs/acceptance-h01-h06.md`, README mục "Bảo mật và vận hành" (PR #17).

## Bản đồ PR (xếp chồng: merge theo thứ tự; đều đã xanh CI khi mở)
- Migration: #6 (độc lập; **giữ cho tới khi B1 xong**)
- Frontend: #7 → #8 → #10 → #11 → #14 → #15 (nâng vite + nhãn nhóm nhỏ)
- Backend: #9 → #12 → #16 (k-anonymity + việc nhỏ) → #17 (README)
- Tài liệu: #13 (spec §10, checklist H01–H06, Part A/B/C)
Mỗi PR chỉ đổi một vùng; PR sau nằm trên nhánh của PR trước, merge #7 trước rồi GitHub tự dồn base về `main`.

## Việc còn lại (theo thứ tự ưu tiên)
- [ ] C1. **Chạy thử migration `…03`/`…04` trên Postgres/Supabase test** nếu B1 chưa làm (`supabase db reset`): RPC `review_recommendation` (xung đột hai tab, replay, quyền), xoá `analysis_runs` cascade sang bảng audit, DELETE/TRUNCATE trực tiếp audit bị chặn. Lỗi SQL: sửa trong migration nếu chưa áp ở nơi dùng chung, nếu đã áp thì thêm `…05`.
- [ ] C2. **Kế hoạch triển khai an toàn**: code mới cần migration; áp migration trước sẽ làm code cũ (ghi trực tiếp từ browser) lỗi, deploy code trước thì API ghi trả 503. Làm trên **staging** trước: áp migration + deploy chuỗi PR cùng lúc, chạy H01–H06, rồi mới production. Merge vào `main` tự deploy Railway (`deploy.yml`), không tự chạy migration. Cần giữ snapshot trước và phương án rollback.
- [ ] C3. Điền `SUPABASE_SERVICE_ROLE_KEY` (chỉ backend), đặt `AGGREGATE_SNAPSHOT_PATH` và `AGGREGATE_SNAPSHOT_V2_PATH` trỏ vào volume `/data`, tạo và tải `aggregate.v2.json` lên volume (xem README).
- [ ] C4. Kiểm CSP trên trình duyệt ở staging (Console có báo vi phạm khi vẽ biểu đồ/mở hộp thoại không); thêm HSTS ở proxy Railway.
- [ ] C5. Chạy `pnpm dev` một lần sau khi nâng vite (PR #15): HMR và proxy `/api`.
- [ ] C6. Nhóm xác nhận: (a) quy tắc ẩn KC <5 học viên (dòng quyết định ở `spec.md` §10, `MIN_LEARNERS` trong `analytics/metrics.py`), (b) nâng vite. Quyết định có áp quy tắc cho luồng CLI v1 (`analytics/workflow.py`, benchmark) hay không; hiện chưa áp.
- [ ] C7. Kiểm tay H01–H06 và 4 điều kiện chuyển giai đoạn; chỉ báo "Đạt" khi người đã xác nhận.
- [ ] C8. Việc nhỏ chưa làm: test frontend (vitest, cần duyệt dependency); `pnpm`/`uv` bản khớp CI (máy dev có thể thiếu Python 3.13: dùng `uv run --python 3.12`).

## Lệnh
```
uv run --python 3.12 python -m pytest -q            # backend (366 test)
corepack pnpm --dir codebase/frontend build         # frontend
docker build -t learningpulse:local .               # đúng Dockerfile CI/Railway dùng
```
Không commit `.env`, `data/pre_class/`, DuckDB. Không sửa `eval/run-*.csv`, `cost/simulate-*.csv`, `traces/*`, `eval/metric_spec.yaml`, chuẩn "đạt" `spec.md` §7. Không merge #6 trước khi C1 xong.
