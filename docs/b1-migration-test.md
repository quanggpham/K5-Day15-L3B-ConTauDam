# B1: kiểm thử migration 20261127000000 → …04 (Supabase local)

- Ngày: 2026-11-28. Môi trường: Supabase CLI 3.4.0 (`npx supabase start`), Postgres 17.12, Docker local. **Chưa chạy trên project Supabase test trên cloud.**
- Lệnh: `npx supabase start` sẽ áp cả 5 migration và không có lỗi. Sau đó chạy `docker exec -i <supabase_db_container> psql -U postgres -q < supabase/tests/review_rpc_check.sql`. Script chạy trong một transaction rồi rollback, in `ALL PASS`.

| Ca | Kết quả |
|---|---|
| Đầu vào sai (decision lạ; có content khi không sửa) → `invalid_input` | Đạt |
| Coach khác gọi trên run không phải của mình → `not_found` | Đạt |
| Chuyển trạng thái không hợp lệ (pending→edited, changes_requested→accept) → `invalid_transition` | Đạt |
| accept → reject cùng version (hai tab, tuần tự) → `version_conflict` | Đạt |
| Gửi lại đúng request → `replayed`; gửi lại sau khi đã bị ghi đè → `version_conflict` | Đạt |
| Bản sửa tay: `is_edited`, `needs_rereview` = true, `jev_score` = null | Đạt |
| Kết quả RPC không lộ `actor_email` | Đạt |
| Hai phiên **song song** (phiên 1 giữ khoá 3 giây): phiên 1 `ok`, phiên 2 `version_conflict`, chỉ 1 dòng audit | Đạt |
| service_role: DELETE / UPDATE / TRUNCATE trực tiếp audit bị chặn | Đạt |
| authenticated: không gọi được RPC, không INSERT được audit; owner có allowlist đọc được audit; người ngoài allowlist đọc được 0 dòng | Đạt |
| Xoá `analysis_runs` → recommendations + audit bị xoá cascade; xoá `auth.users` → cascade tới audit | Đạt |

Không phát hiện lỗi SQL nào cần báo phần A.
