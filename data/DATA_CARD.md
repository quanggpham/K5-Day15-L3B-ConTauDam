# Data card — dữ liệu bản chạy thử dùng

> Điền ở guide bước 2.4 (bản đầu ở CP2, đủ ở CP3). Ôn lại: ngày 6 · lab ngày 6. Chấm ở rubric R4.
> Một trang. Mỗi dataset một mục. Dữ liệu chạy thử (bài mẫu, thông báo mẫu, đoạn transcript…) để trong thư mục `data/` này.
> Không commit nguyên tài liệu khoá, dữ liệu cá nhân thật hay nguyên file data BTC cấp — chỉ đoạn trích ngắn, bản viết lại, hoặc số đã tổng hợp.

## Dataset 1 · Nhật ký pre-class AI20K khoá 5

| | |
|---|---|
| Dùng để làm gì | nguồn cho bước phân tích và phát hiện lỗ hổng (`codebase/backend/analytics/`) · nguồn sự thật của câu thử B01–B10 · đào bằng chứng |
| Từ đâu | data BTC cấp (`data/preclass/` trong repo đề `K5-L3-Day15-AI-Product-Hackathon`, commit `cebf442`) |
| Xử lý những bước gì | chép vào `data/pre_class/` (gitignore) · `uv run python -m codebase.backend.analytics.ingest` kiểm cột bắt buộc và số cột từng dòng (`column_dictionary.csv` được thiếu ô cuối `gia_tri`), nạp `answers`, `events`, `completed_items`, `chat`, `column_dictionary` vào `data/learning_pulse.duckdb` (gitignore) · ẩn danh do BTC làm, nhóm không xử lý thêm · phân tích lỗ hổng lọc `lan_thu = 1` và `was_correct` không trống |
| Số dòng / số đoạn | `events` 107.709 · `answers` 3.776 · `completed_items` 2.472 · `chat` 1.260 · `class_events` 849 · `learners` 721 · `rewards` 228 · `column_dictionary` 71 · `event_types` 38. Sau lọc để phân tích lỗ hổng: 2.478 lượt trả lời lần đầu có chấm, 123 học viên, 160 `kc_code`, 13 bài |
| Phiên bản / ngày lấy | dữ liệu 05/11–25/11/2026 (Day01–Day13) · lấy ngày 27/11/2026 |
| Nhãn | thật (BTC đã ẩn danh) |
| Giới hạn | mẫu mỏng: 70/160 KC có dưới 10 lượt trả lời lần đầu (trung vị 10, tối đa 95) · lệch về học viên tích cực: 173 người có dòng trong `answers` so với 436 có hoạt động và 721 tài khoản · câu có chấm chủ yếu từ ôn tập cuối ngày (`pre_post_post` 1.970 dòng) và mini lab (`thuc_hanh` 519), `video_quiz` chỉ 7, `quiz_module`/`checkpoint`/`pre_post_pre` 0 dòng · không có câu chữ học viên viết, chỉ có độ dài · câu nhắn AI chỉ gắn tới module, 1.259/1.260 dòng `chat` trống `lesson_id` · không có lời giảng hay slide · `learning_mode` chỉ có từ 25/11 (22 dòng `answers`) · giờ là UTC; mỗi loại dữ liệu bắt đầu ghi từ ngày khác nhau · chưa kiểm quyền gửi ra dịch vụ ngoài, nên chỉ số tổng hợp theo bài/KC (không có `hv`) mới được gửi lên LLM · luật BTC: không đoán danh tính, không xếp hạng học viên, không đăng lại nguyên file |

**Data `synthetic` (nhóm tự sinh):** bản chạy thử không dùng data sinh bằng prompt hay script. Câu thử B11–B15 trong `eval/benchmark.csv` do nhóm viết tay, không có seed. Data tự dựng **không phải bằng chứng pain**.

## Dataset 2 · Lesson KB (nội dung bài giảng cho RAG)

| | |
|---|---|
| Dùng để làm gì | nguồn cho bước truy xuất bài giảng (embedding pgvector, fallback BM25; lọc metadata `lesson_id`, `kc_code`) |
| Từ đâu | notes + quiz do thành viên nhóm (MinPhuc) tự soạn (xác nhận 2026-11-28). Notes được mở rộng bằng agent từ notes gốc + kiến thức chung, không thêm số liệu mới (`docs/notes-detailed/`); Day 06/08 soạn từ quiz, chưa có slide gốc |
| Xử lý những bước gì | `chunk_notes`/`chunk_quiz` → đề xuất ánh xạ KC bằng BM25 (`data/kb_mapping.csv`) → `scripts/export_kb_chunks.py` → embed `intfloat/multilingual-e5-small` (384 chiều, chuẩn hoá) bằng `kaggle/embed_kb.py` → `scripts/load_kb_embeddings.py` |
| Số dòng / số đoạn | 684 đoạn từ 26 nguồn (175 notes, 509 quiz), 2026-11-28 |
| Phiên bản / ngày lấy | 2026-11-28 |
| Nhãn | `lesson_id`/`kc_code` là đề xuất máy, chưa duyệt; mọi đoạn `approved=false` nên chưa được truy xuất cho tới khi coach duyệt |
| Giới hạn | khi chưa có KB, hệ thống vẫn nêu lỗ hổng từ số liệu và ghi rõ "chưa có căn cứ bài giảng" |
