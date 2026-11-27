# Nghiệm thu thủ công H01–H06

Người kiểm là chính. CI, unit test và JEV chỉ là tín hiệu hỗ trợ. Mỗi dòng ghi: mã ca, người kiểm, bản deploy/snapshot, thao tác, mong đợi, thực tế, kết quả, bằng chứng (đã che thông tin cá nhân).
Kết quả: **Đạt / Trượt / Chưa kiểm**. Chỉ báo đạt khi người đã xác nhận. Cập nhật 2026-11-28: chưa ca nào được kiểm.

| Mã | Thao tác | Mong đợi | Người kiểm | Bản kiểm | Thực tế | Kết quả | Bằng chứng |
|---|---|---|---|---|---|---|---|
| H01a | Đăng nhập sai mật khẩu | Báo lỗi, không vào được | | | | Chưa kiểm | |
| H01b | Đăng nhập đúng, email trong allowlist | Vào `/dashboard` | | | | Chưa kiểm | |
| H01c | Đăng nhập email ngoài allowlist | Thông báo chưa được cấp quyền | | | | Chưa kiểm | |
| H01d | Để hết phiên rồi thao tác | Về `/login`, quay lại đúng đường dẫn nội bộ | | | | Chưa kiểm | |
| H01e | Coach A mở/tải/duyệt/Copilot báo cáo của coach B (đổi `runId`) | 404, không lộ nội dung | | | | Chưa kiểm | |
| H02a | Đối chiếu số lượt/người/tỷ lệ sai của hai bài với DuckDB | Khớp từng KC | | | | Chưa kiểm | |
| H02b | Ca mẫu số 0, dưới 10 lượt, đồng hạng | Trạng thái riêng, không xếp ưu tiên dưới 10 lượt, hiện cả nhóm đồng hạng | | | | Chưa kiểm | |
| H03a | Tạo nháp, bấm nhanh hai lần | Một báo cáo | | | | Chưa kiểm | |
| H03b | Mất mạng giữa chừng rồi thử lại | Cùng nháp, không trùng | | | | Chưa kiểm | |
| H03c | Reload, mở lại từ `/history` sau khi snapshot thay đổi | Số liệu lúc tạo, không đổi | | | | Chưa kiểm | |
| H03d | Lặp H03a–c trên desktop và mobile | Giống nhau | | | | Chưa kiểm | |
| H04a | Mở từng tab báo cáo | Không lỗi; tab chưa có AI nêu lý do | | | | Chưa kiểm | |
| H04b | Tải CSV, mở bằng bảng tính | Tiếng Việt đúng, ô văn bản không chạy như công thức, khớp snapshot | | | | Chưa kiểm | |
| H04c | Copilot: giải thích ưu tiên, so sánh bài trước; hai thao tác tạo nội dung | Hai thao tác đầu có căn cứ đúng snapshot; hai thao tác sau bị khoá kèm lý do chưa có KB | | | | Chưa kiểm | |
| H05a | Chấp nhận, từ chối, yêu cầu sửa | Trạng thái và lịch sử đúng | | | | Chưa kiểm | |
| H05b | Sửa tay sau yêu cầu sửa, rồi duyệt lại | Bản sửa chờ duyệt lại, không có điểm JEV | | | | Chưa kiểm | |
| H05c | Hai tab cùng duyệt một đề xuất | Tab sau nhận xung đột, tải lại, giữ nội dung đang soạn | | | | Chưa kiểm | |
| H06 | (Khi đủ điều kiện AI) kiểm từng trích dẫn và độ phù hợp; thử lỗi provider, thiếu nguồn, đề xuất bị chặn | Báo cáo số liệu vẫn dùng được | | | | Chưa kiểm — AI chưa bật | |

Ghi chú: H05 cần đề xuất để duyệt; khi AI chưa bật chỉ thử được bằng dữ liệu fixture ở môi trường test và phải ghi rõ đó là kiểm thử môi trường test.
