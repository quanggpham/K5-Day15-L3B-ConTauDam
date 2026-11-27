# Hiệu chỉnh JEV: mẫu chấm tay và đề xuất ngưỡng (B7, chờ nhóm duyệt)

> Trạng thái: **đề xuất**, chưa áp dụng. JEV chưa bật trong ứng dụng (xem `docs/architecture.md`).
> Chưa có số liệu chạy thật; mọi ngưỡng dưới đây là *(tự ước tính)* cho tới khi có kết quả chấm tay.

## 1. JEV hiện chấm gì

`codebase/backend/evaluation/jev.py` → `judge_recommendation()` trả hai điểm riêng (số thực), người gọi tự quyết định đạt hay không:

| Tiêu chí | Câu hỏi cho judge |
|---|---|
| `grounded` | Khẳng định thực tế trong đề xuất có được số liệu hoặc đoạn nguồn trong `evidence` hỗ trợ không? (gợi ý hoạt động không tính là khẳng định thực tế) |
| `relevant` | Hoạt động đề xuất có nhắm đúng chủ đề kiến thức trong `evidence.sources` không? |

## 2. Mẫu chấm tay

Mỗi đề xuất do hai người chấm **độc lập** (không xem điểm JEV và không xem phiếu của nhau). Lưu file ở `evidence/jev-manual-N.csv` và chỉ ghi `recommendation_id`, không ghi dữ liệu cá nhân.

```csv
recommendation_id,nguoi_cham,grounded_tay,relevant_tay,suy_dien_vuot_bang_chung,ghi_chu
```

- `grounded_tay`: `1` nếu mọi số và trích dẫn khớp `evidence`; `0` nếu có ít nhất một số sai, một nguồn không có thật, hoặc một nguyên nhân bịa.
- `relevant_tay`: `1` nếu hoạt động ôn nhắm đúng KC trong evidence; `0` nếu lạc sang KC khác hoặc chỉ là lời khuyên chung chung.
- `suy_dien_vuot_bang_chung`: `1` nếu đề xuất kết luận mạnh hơn mức dữ liệu cho phép (ví dụ mẫu < 10 lượt mà khẳng định là gap của cả lớp).
- Hai người lệch nhau thì người thứ ba quyết định và ghi lý do vào `ghi_chu`.

## 3. Cách chọn ngưỡng (đề xuất)

1. Lấy ít nhất 30 đề xuất *(tự ước tính: đủ để thấy xu hướng, chưa đủ để kết luận thống kê)*, trong đó có cả đề xuất cố ý sai: sai số, bịa nguồn, lạc KC.
2. Chạy JEV trên cùng các đề xuất đó và ghép điểm JEV với nhãn chấm tay.
3. Với mỗi tiêu chí, quét ngưỡng `t` từ 0,0 đến 1,0 (bước 0,05). Tính:
   - **lọt lưới**: số đề xuất có nhãn tay = 0 nhưng JEV ≥ t;
   - **chặn nhầm**: số đề xuất có nhãn tay = 1 nhưng JEV < t.
4. Chọn `t` nhỏ nhất mà **lọt lưới = 0** đối với `grounded`, vì số sai làm Coach ôn sai trọng tâm. Với `relevant`, chấp nhận chặn nhầm nhiều hơn, vì đề xuất bị chặn chỉ khiến hệ thống lùi về báo cáo số liệu.
5. Một đề xuất chỉ đạt khi qua cả hai ngưỡng **và** qua lớp kiểm bằng code (`validate_recommendation`). Không đạt thì gọi lại một lần, sau đó hiển thị báo cáo chỉ có số liệu.

Ngưỡng khởi điểm để thử *(tự ước tính, phải thay bằng kết quả bước 3)*: `grounded ≥ 0,8`, `relevant ≥ 0,6`.

## 4. Nhóm cần quyết định

- [ ] Duyệt mẫu chấm ở §2.
- [ ] Ai chấm, và lấy đề xuất từ đâu (cần Lesson KB có nguồn được phép, xem B6).
- [ ] Chốt ngưỡng sau khi có số liệu chấm tay; ghi kết quả vào `eval/report.md`.
