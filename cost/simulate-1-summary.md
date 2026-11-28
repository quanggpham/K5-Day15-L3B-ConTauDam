# Tóm tắt mô phỏng simulate-1@20261128-130838

Do `python run.py simulate` sinh ra — không sửa tay. Chép bảng sang `cost/cost-estimate.md`.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| coach_it | 23 | 1 | 1375 | 2911 | 1.0 | 2.0 |
| coach_vua | 19 | 2 | 3081 | 5498 | 2.1 | 4.1 |
| coach_nhieu | 8 | 3 | 4708 | 8645 | 3.0 | 6.4 |

Tỉ lệ đạt dùng để tính: **chưa có** lượt eval nào chấm xong (`python run.py score eval/run-N.csv`) → chưa tính được chi phí / task thành công

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (5 người) | Chi phí / tháng — cơ sở (10 người) | Chi phí / tháng — cao (20 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| lfm3-1.7b (vào 0.08 · ra 0.2 $/1M) | $0.0012 | — | — | $0.0568 | $0.1135 | $0.2271 | $0.0114 |
| claude-sonnet-5.5 (vào 2.0 · ra 10.0 $/1M) | $0.0532 | — | — | $2.59 | $5.17 | $10.34 | $0.5172 |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (1.7) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: lfm3-1.7b. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 0/50.
