# Chi phí khi dùng thật

> Điền ở guide bước 4.2, nộp ở CP4 14:30 Thứ Bảy 28/11. Chấm ở rubric R6.
> Số **không điền tay**: lấy từ `cost/simulate-1-summary.md` (sinh bởi `python run.py simulate`).
> Lúc build dùng gói miễn phí vẫn tính theo **giá gói trả phí**.

## 1. Đầu vào

- **Persona** (`cost/personas.yaml`): người dùng là coach / giảng viên AI20K, không phải học viên (`canvas.md` dòng 2). 3 kiểu — `coach_it` 50% · 4 phiên/tháng · 1 lượt hỏi; `coach_vua` 30% · 8 phiên · 2 lượt; `coach_nhieu` 20% · 16 phiên · 3 lượt. Nguồn: *(tự ước tính)* — chưa có phỏng vấn / khảo sát coach.
- **Số người dùng thật** 3 kịch bản: thấp 5 · cơ sở 10 · cao 20 coach. Nguồn: *(tự ước tính)* — repo và đề không ghi số coach của khoá.
- **Giá** (USD / 1 triệu token):
  - `lfm3-1.7b` (rẻ, model đang dùng): vào 0,08 · ra 0,20 — https://www.liquid.ai/pricing · xem 28/11/2026
  - `claude-sonnet-5.5` (mạnh): vào 2,00 · ra 10,00 — https://platform.claude.com/docs/en/about-claude/pricing (chép từ `further-reading/model-prices.md` của repo đề, BTC xem 25/11/2026)
- **Tỉ lệ đạt** dùng để tính: __/20 (__%) — lượt `run-2` *(chờ chấm cột `pass`)*
- Đo token trên model `lfm3-1.7b`, tính giá model `lfm3-1.7b` và `claude-sonnet-5.5` (bộ tách token khác nhau nên số token thật trên Sonnet có thể lệch).

## 2. Kết quả mô phỏng

Lượt mô phỏng: `cost/simulate-1.csv` · run ID `simulate-1@20261128-130838` · 50 phiên (0 phiên lỗi) · seed 42

| Persona | Số phiên | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| coach_it | 23 | 1 | 1375 | 2911 | 1.0 | 2.0 |
| coach_vua | 19 | 2 | 3081 | 5498 | 2.1 | 4.1 |
| coach_nhieu | 8 | 3 | 4708 | 8645 | 3.0 | 6.4 |

| Model | Chi phí / phiên | Chi phí / task thành công | / tháng — thấp (5) | / tháng — cơ sở (10) | / tháng — cao (20) | / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|
| lfm3-1.7b | $0.0012 | $0.0012 ÷ tỉ lệ đạt run-2 = __ | $0.0568 | $0.1135 | $0.2271 | $0.0114 |
| claude-sonnet-5.5 | $0.0532 | $0.0532 ÷ tỉ lệ đạt run-2 = __ | $2.59 | $5.17 | $10.34 | $0.5172 |

Chi phí / task thành công = chi phí trung bình mỗi phiên ÷ tỉ lệ đạt — **không coi như đạt 100%**.

## 3. So với impact

- Impact / người / tháng (`spec.md` §2): __ *(chờ nhóm điền số coach × lần × phút ở §2)*
- Chi phí / người / tháng (cơ sở, model `lfm3-1.7b`): $0.0114 · (`claude-sonnet-5.5`: $0.5172)
- **Kết luận một dòng — đáng làm không:** chi phí model gần như không đáng kể (< $1 / coach / tháng kể cả model mạnh); câu hỏi quyết định là **chất lượng** (tỉ lệ đạt) và giờ công coach duyệt, không phải tiền model. *(Chốt sau khi có tỉ lệ đạt run-2 và impact §2.)*

## 4. *(Muốn sâu hơn, không bắt buộc)*

- Chi phí ngoài model chưa tính: hosting backend/Supabase, giờ công coach duyệt từng đề xuất.
- Token ra lớn hơn token vào ~1,9 lần (2.557 vào · 4.811 ra / phiên trung bình) → giới hạn độ dài câu trả lời là cần gạt rẻ nhất nếu đổi sang model mạnh.
