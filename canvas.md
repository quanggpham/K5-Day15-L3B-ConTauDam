# Canvas — [tên nhóm] · Track [A–F]

> Điền ở guide bước 1.4. CP1 17:00 Thứ Sáu 27/11: nộp bản đầu, đủ 7 dòng (dòng 4 được ghi giả thuyết + nguồn sẽ kiểm).
> CP2 19:30 Thứ Sáu 27/11: cập nhật (số bằng chứng đầu, lát cắt đã chốt) và điền dòng "Đã đổi gì so với CP1".
> Track F: chép thêm thẻ đề của nhóm (khung trong file track F) xuống dưới bảng này.

| # | Dòng | Nhóm điền |
|---|---|---|
| 1 | Track + lát cắt dự kiến | Track A + Lab coach trước buổi học lựa chọn bài học cần phân tích, AI đề xuất kiến thức cần ưu tiên ôn tập, kèm bằng chứng và phương pháp giảng lại để coach xem xét.|
| 2 | Người dùng chính (một vai cụ thể — không phải "học viên nói chung") |Giảng viên và lab coach AI20K |
| 3 | Pain một câu: ai — đang làm gì — vướng đâu — hậu quả |Giảng viên và lab coach gặp khó khăn trong việc tổng hợp kết quả học tập trước buổi học, xác định những kiến thức học viên chưa hiểu và lựa chọn nội dung cần ưu tiên giảng lại.|
| 4 | Bằng chứng đầu — CP1: giả thuyết + nguồn sẽ kiểm · CP2: số đầu tiên + 1 trích dẫn CP2 (đào data `answers.csv`, lọc lượt trả lời lần đầu có chấm đúng/sai): 2.478 lượt từ 123 học viên trải trên 160 ý kiến thức của 13 bài; chỉ 90/160 ý kiến thức có ≥10 lượt để kết luận. Ví dụ Day05: `ai_product_canvas` sai 12/15 lượt (80%), cao nhất trong 13 ý kiến thức có ≥10 lượt của bài này. Trích dẫn người dùng: chưa có, đang hẹn phỏng vấn Lab Coach/giảng viên để kiểm lại giả thuyết. |
| 5 | **Lát cắt MỘT CÂU** (1 người dùng · 1 việc · 1 quyết định AI · 1 kết quả) | Giảng viên/ Lab Coach chọn một bài học cần phân tích, AI quyết định nhóm kiến thức nào cần ưu tiên ôn tập, và kết quả là một teaching brief ngắn kèm bằng chứng dữ liệu và gợi ý cách giảng lại. |
| 6 | AI tự làm đến đâu + 1 dòng lý do: sai thì ai chịu gì | AI tự làm đến bước phân tích dữ liệu học tập, xác định knowledge gap và đề xuất ưu tiên ôn tập; Lab Coach là người quyết định cuối cùng có áp dụng hay không, vì nếu AI kết luận sai thì có thể khiến việc giảng lại lệch trọng tâm.|
| 7 | Phân công có tên |[Nguyễn Công Hoàn] – Product & Data Analytics (pain point, evidence, impact, data analysis); [Nguyễn Minh Phúc] – AI Engineering (RAG, workflow, recommendation engine); [Nguyễn Phi Hoàng] – AI Evaluation & Security (benchmark, JEV, guardrails, cost simulation); [Phạm Quang Dũng] – UI & DevOps (dashboard, integration, deploy, slide/demo).|
| — | *(CP2)* Đã đổi gì so với CP1 | Dòng 4 thay giả thuyết bằng số đầu tiên đào từ data. Chốt hình dạng workflow cố định: số liệu do code tính, AI chỉ đề xuất, Coach chỉ chọn bài (không chat tự do) và duyệt hoặc sửa tay đề xuất. Ý kiến thức có dưới 10 lượt được gắn cờ "chưa đủ dữ liệu", không xếp ưu tiên. |
