# Đào data — cách đếm và kết quả

Chạy lại: `.venv/Scripts/python.exe -B evidence/count.py` (đọc `data/learning_pulse.duckdb` ở chế độ chỉ đọc; tạo DB bằng `python -m codebase.backend.analytics.ingest`, xem `data/DATA_CARD.md`). Script chỉ in số tổng hợp, không in mã học viên.

## 1. Cách đếm

- Data dùng: `answers.csv` và `chat.csv` trong data pre-class AI20K khoá 5 do BTC cấp, dữ liệu 05/11–25/11/2026 (Day01–Day13), mô tả ở `data/DATA_CARD.md`.
- Đếm gì: lượt trả lời **lần đầu** đã được chấm đúng/sai, theo `kc_code` và `lesson_id`.
- Lọc: `lan_thu = 1`; `lesson_id`, `kc_code` không trống; `was_correct` không trống.
- **Mẫu số là gì:** số lượt trả lời lần đầu đã chấm đúng/sai (2.478). Không phải số học viên; không gồm 1.280 lượt lần đầu chưa chấm và 18 lượt từ lần hai trở đi.
- Ngưỡng "đủ mẫu" để xếp ưu tiên: KC có ít nhất 10 lượt chấm.
- Script: `evidence/count.py`; cùng cách lọc với `codebase/backend/analytics/metrics.py`.

## 2. Đọc trước, đếm sau

Các kiểu hành vi trong data (theo `data/DATA_CARD.md`, mục Giới hạn):
- Lượt có chấm chủ yếu từ ôn tập cuối ngày (`pre_post_post` 1.970 dòng) và mini lab (`thuc_hanh` 519); `video_quiz` chỉ 7.
- Câu hỏi học viên nhắn AI chỉ gắn tới module: 1.259/1.260 dòng `chat` trống `lesson_id`; bài chỉ suy được từ tiền tố `DayNN/` của `transcript`.
- Không có câu chữ học viên viết, chỉ có độ dài.

## 3. Kết quả (đếm ngày 28/11/2026)

| Đếm gì | x / N | % | Ghi chú |
|---|---|---|---|
| Lượt lần đầu trả lời sai | 424 / 2.478 | 17,11% | mẫu số: lượt lần đầu có chấm |
| KC đủ mẫu để kết luận (≥ 10 lượt chấm) | 90 / 160 | 56,25% | 160 KC có ít nhất một lượt chấm (trong 225 KC có lượt lần đầu) |
| Học viên có ít nhất một lượt chấm | 123 / 173 | 71,10% | 173 = người có dòng trong `answers` |
| Dòng chat có tiền tố `Day01/` | 376 | — | chỉ là số lượt nhắn, không cho biết hiểu sai KC nào |

## 4. ≥5 ví dụ cụ thể (mã KC, không có dữ liệu cá nhân)

1. Day05 `ai_product_canvas`: 12/15 sai (80%).
2. Day07 `tool_definition_context_cost`: 6/10 sai (60%).
3. Day03 `react_reasoning_acting_pattern`: 9/18 sai (50%).
4. Day08 `multi_agent_token_cost`: 4/10 sai (40%).
5. Day09 `paired_bootstrap_interpretation`: 3/3 sai (100%) nhưng dưới ngưỡng 10 lượt, không kết luận được.

## 5. Giới hạn của data

Data cho biết học viên trả lời sai ở đâu, không cho biết vì sao. Mẫu mỏng (70/160 KC dưới 10 lượt chấm) và lệch về học viên tích cực (173 người có dòng trong `answers` so với 721 tài khoản).
→ Kiểm lại bằng phỏng vấn Lab Coach *(chưa có; nhóm điền khi phỏng vấn xong)*.
