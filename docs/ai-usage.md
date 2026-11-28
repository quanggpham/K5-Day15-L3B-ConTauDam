# Khai báo dùng AI

README của nhóm có mục "Dùng AI vào việc gì" (2–3 dòng, bắt buộc). Ghi chi tiết vào bảng dưới đây.

> Luật của đề: dùng AI để làm bài thoải mái, nhưng **ai không giải thích được phần có tên mình thì phần đó nhận 0 điểm**. Khai thiếu không bị trừ; giấu mới bị.

| Việc | Công cụ AI | AI làm gì | Người kiểm/sửa gì | Ai phụ trách |
|---|---|---|---|---|
| Code bản chạy thử (CLI, API, frontend) | Claude Code; công cụ khác *(nhóm xác nhận)* | Viết phần lớn code theo yêu cầu; agent thực thi theo kế hoạch trong `docs/superpowers/plans/` | Người phụ trách đọc diff, chạy test *(nhóm xác nhận chi tiết)* | Nguyễn Minh Phúc, Phạm Quang Dũng |
| Prompt / thiết kế lời gọi mô hình | Claude Code | Viết prompt hệ thống và phần kiểm số trong `codebase/agent.py` (28/11) | Đối chiếu từng số trong `eval/run-1.csv` với benchmark *(nhóm xác nhận)* | Nguyễn Phi Hoàng *(nhóm xác nhận)* |
| Đào data (viết script đếm, gợi ý nhãn) | Claude Code | Viết `evidence/count.py`; truy vấn trong `analytics/metrics.py` *(nhóm xác nhận công cụ)* | Chạy lại script, đối chiếu với `data/DATA_CARD.md` (khớp 424/2.478, 90/160) *(nhóm xác nhận)* | Nguyễn Công Hoàn |
| Rà câu hỏi phỏng vấn / khảo sát | chưa làm | — | — | Nguyễn Công Hoàn |
| Viết câu thử (benchmark) | *(nhóm xác nhận)* | *(nhóm xác nhận câu nào AI gợi ý, vd B18–B20)* | Mỗi câu có `source`; B05 sửa lỗi gõ 6/10 → 4/10 sau khi đếm lại (spec §10) | Nguyễn Phi Hoàng |
| Sinh data `synthetic` | không dùng | — | — | — |
| Chấm cột `pass` | Claude Code (agent) | Lập `eval/grading-sheet-run-1.md`: so số trong output với `expected` bằng code và gợi ý đạt/trượt. Không điền cột `pass` | Người chấm tự điền `pass` trong `eval/run-1.csv` *(nhóm ghi tên người chấm)* | *(nhóm xác nhận)* |
| Slide, văn bản | chưa làm | — | — | Phạm Quang Dũng |

**Không dùng AI để:** tạo người được phỏng vấn, trích dẫn, câu trả lời khảo sát; sửa kết quả các lượt đã chạy (`eval/run-*.csv`, `cost/simulate-*.csv`, `traces/`).
