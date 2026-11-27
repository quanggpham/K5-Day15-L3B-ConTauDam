# Data card — dữ liệu bản chạy thử dùng

> Điền ở guide bước 2.4 (bản đầu ở CP2, đủ ở CP3). Ôn lại: ngày 6 · lab ngày 6. Chấm ở rubric R4.
> Một trang. Mỗi dataset một mục. Dữ liệu chạy thử (bài mẫu, thông báo mẫu, đoạn transcript…) để trong thư mục `data/` này.
> Không commit nguyên tài liệu khoá, dữ liệu cá nhân thật hay nguyên file data BTC cấp — chỉ đoạn trích ngắn, bản viết lại, hoặc số đã tổng hợp.

## Dataset 1 · [tên]

| | |
|---|---|
| Dùng để làm gì | nguồn cho công cụ `…` · bộ câu thử · đào bằng chứng |
| Từ đâu | data BTC cấp (`…` trong repo đề) · tài liệu khoá (trích / viết lại) · nhóm tự viết · sinh có seed |
| Xử lý những bước gì | lọc __ · làm sạch __ · ẩn danh __ · chia __ (script: `…`) |
| Số dòng / số đoạn | __ |
| Phiên bản / ngày lấy | __ |
| Nhãn | thật · `synthetic` |
| Giới hạn | thiếu gì, lệch về phía nào |

**Data `synthetic` (nhóm tự sinh):** ghi cách sinh (prompt / script), seed, người kiểm, số dòng đã kiểm tay. Data tự dựng **không phải bằng chứng pain**.

## Dataset 2 · [tên]

…

## Dữ liệu pre-class local

Nguồn: dữ liệu BTC trong `data/pre_class/`; năm file CSV được nạp bằng `uv run python -m codebase.backend.analytics.ingest` vào DuckDB local. Bản gốc và database không được commit. Chưa kiểm tra tính đại diện, chất lượng hay quyền sử dụng để gửi tới dịch vụ bên ngoài; chưa dùng làm bằng chứng pain. Nội dung bài học cho RAG cần nguồn riêng được phép.

Import yêu cầu các cột chính theo từng file và kiểm tra số cột từng dòng. `column_dictionary.csv` cho phép thiếu ô cuối `gia_tri`; dữ liệu gốc hiện có một dòng như vậy. Số dòng được in khi import; đây là mô tả dữ liệu, chưa phải bằng chứng pain.
