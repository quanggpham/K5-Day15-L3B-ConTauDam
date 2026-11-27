# LearningPulse full flow — Phần B: việc cho người thứ hai

> Tách từ `2026-11-27-learningpulse-full-flow.md`. Phần A (đang làm) ở `...-part-a-in-progress.md`.
> Các việc dưới đây không đụng file của phần A. Làm trên nhánh riêng từ `origin/main`, một PR nhỏ cho mỗi việc.

## Đọc trước
`AGENTS.md`, `data/DATA_CARD.md`, `docs/learningpulse-design.md`, `spec.md` §7, `docs/superpowers/plans/2026-11-27-learningpulse-full-flow.md`.

## Vùng file của phần B (được sửa)
`supabase/` (chỉ để thử; sửa migration thì báo phần A), `eval/benchmark.csv`, `evidence/`, `data/` (không commit dữ liệu thật), `docs/` (file mới), Railway/CI cấu hình.
**Không sửa:** `codebase/backend/api/`, `codebase/frontend/src/`, `tests/`, `spec.md`.

## Ưu tiên cao (mở khoá phần A)
- [ ] B1. Áp migration `20261127000000` → `…04` lên Supabase **test** (`supabase db reset`). Kiểm RPC `review_recommendation` (xung đột hai tab, ràng buộc, quyền), xoá `analysis_runs` cascade sang bảng audit, DELETE trực tiếp audit bị chặn. Báo lỗi SQL cho phần A. Migration chưa từng chạy thử.
- [ ] B2. Lấy `SUPABASE_SERVICE_ROLE_KEY`, điền `.env` (không commit), kiểm đăng nhập/allowlist với 2 tài khoản coach thật.
- [ ] B3. Kiểm tay H01–H06 trên bản đang chạy (desktop + mobile); ghi mã ca, người kiểm, thao tác, mong đợi, thực tế, Đạt/Trượt/Chưa kiểm, bằng chứng đã che thông tin cá nhân. Lỗi UI báo phần A.

## Benchmark và chấm điểm
- [ ] B4. Bổ sung `eval/benchmark.csv` từ 15 lên 20–30 câu cho CP3. Chỉ thêm câu; không sửa/xoá câu cũ, không sửa `expected` cho khớp output. Chạy `python run.py check`.
- [ ] B5. Chấm tay theo chuẩn CP2: hai người độc lập, 5 output; chỉ điền cột `pass`, `ghi_chu` của `eval/run-N.csv`.

## Điều kiện bật AI (chưa bật cho đến khi đủ)
- [ ] B6. Tìm và xin phép nguồn tài liệu cho Lesson KB; dựng KB (ID, bài/KC, văn bản, phiên bản, thông tin duyệt). Dữ liệu cần nguồn được phép riêng; không commit dữ liệu chưa có phép.
- [ ] B7. Mẫu chấm tay và đề xuất ngưỡng JEV để nhóm duyệt.

## Hạ tầng và bằng chứng
- [ ] B8. Dựng staging (Railway), kiểm Docker CI, kế hoạch rollback (giữ snapshot trước). Merge vào `main` tự deploy: xác nhận môi trường trước.
- [ ] B9. Phỏng vấn/khảo sát trong `evidence/`: không bịa người được phỏng vấn, trích dẫn, số liệu; số không nguồn ghi *(tự ước tính)*.

## Sau khi phần A xong bước tương ứng
- [ ] B10. Thêm test runner frontend (vitest; cần nhóm duyệt dependency).
- [ ] B11. Endpoint catalog riêng cho `/analysis/new` và `/history`.
- [ ] B12. `python run.py simulate` (mô phỏng chi phí; cần model/token thật).
- [ ] B13. Cập nhật README, `docs/architecture.md` theo API đã có.

## Luật nhánh và PR
- Nhánh: `feat|fix|docs|chore/<tên-ngắn>` từ `origin/main`; commit nhỏ; mô tả PR nêu rõ đã test gì, chưa test gì.
- Không commit `.env`, `data/pre_class/`, DuckDB, dữ liệu cá nhân thật.
- Nhờ phần A xem trước khi merge nếu PR chạm file ngoài vùng của phần B.
