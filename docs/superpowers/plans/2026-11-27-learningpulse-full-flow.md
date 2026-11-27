# LearningPulse — Kế hoạch triển khai toàn bộ luồng và UI

Đối tượng: giảng viên và lab coach. Luồng chính: đăng nhập → tổng quan → tạo phân tích → báo cáo và Copilot → duyệt, lưu và xem lại. Dùng bố cục tham chiếu đã duyệt: sidebar trái, báo cáo giữa, Copilot phải, nền sáng tím. Trên mobile, menu và Copilot mở theo yêu cầu. UI lấy tên bài, số liệu, thời gian, trạng thái và điểm đánh giá từ dữ liệu thật.

## Phạm vi đã chốt

- Đăng nhập bằng email và mật khẩu. Chỉ hiện Google sau khi cấu hình và kiểm tra OAuth.
- Một cohort AI20K K5 và nguồn pre-class. In-class và Post-class hiện chưa có dữ liệu.
- Tạo nháp ngay khi bắt đầu phân tích. Retry cùng mã yêu cầu để tránh nháp trùng. Báo cáo chỉ có số liệu vẫn xem và tải được.
- Copilot chỉ có thao tác cố định: giải thích ưu tiên, so sánh bài trước, kế hoạch ôn 15 phút và ba câu hỏi kiểm tra lại. Hai thao tác tạo nội dung cần Lesson KB và hiệu chuẩn JEV.
- Coach chấp nhận, từ chối hoặc yêu cầu chỉnh sửa rồi sửa tay. Lưu người thao tác, thời điểm, trước/sau. Bản sửa chờ duyệt lại và không thừa hưởng điểm JEV.
- CSV UTF-8 tải bởi chủ sở hữu. Chia sẻ không nằm trong bản này. Không gửi thông báo hay ghi LMS.
- Con người nghiệm thu chính. CI, unit test và JEV là tín hiệu hỗ trợ.

## Màn hình

| Màn | Nghiệm thu |
|---|---|
| /login | Email, mật khẩu, hiện mật khẩu, hết phiên, sai mật khẩu và ngoài allowlist. Khôi phục đường dẫn hợp lệ sau đăng nhập. |
| /dashboard | Catalog thật, số học viên có lượt chấm, độ chính xác lần đầu, số KC đủ mẫu, chênh lệch điểm phần trăm so với bài trước. Biểu đồ theo KC và phân bố lượt đúng/sai. CTA giữ bài đang chọn. |
| /analysis/new | Cohort, bài, pre-class, khóa submit và retry idempotent. Chuyển đến báo cáo đã lưu. |
| /reports/:runId | Tổng quan, lỗ hổng, đề xuất, đánh giá AI, căn cứ, export, panel Copilot. Có trạng thái thiếu dữ liệu/nguồn và trợ giúp phù hợp. |
| /history | Danh sách của coach, lọc bài/trạng thái, phân trang và mở lại snapshot đã lưu. |
| /reports/:runId/review | Duyệt từng đề xuất, sửa tay sau yêu cầu chỉnh sửa, lưu nhận xét và xem lịch sử. Báo xung đột phiên bản. |
| /profile | Thông tin phiên và đăng xuất. |

## Hợp đồng và thực thi

1. Mở rộng snapshot local có phiên bản, catalog và tổng hợp theo bài/KC. Mẫu số là lượt đầu có chấm đúng/sai, riêng lượt chưa chấm. Đếm người duy nhất trong mẫu. Dưới 10 lượt gắn cờ, còn số tổng hợp, không xếp ưu tiên. Bằng tỷ lệ thì đồng hạng. Nếu top 3 cắt ngang đồng hạng, hiện cả nhóm và để coach chọn khi cần giới hạn.
2. Giữ Supabase Auth, allowlist, RLS và API cũ. Bổ sung /api/dashboard và /api/analysis-runs (tạo, danh sách, chi tiết, /export, /copilot, /reviews). Backend tạo snapshot báo cáo và xác định chủ sở hữu từ phiên đăng nhập. Khóa ghi trực tiếp của browser vào dữ liệu báo cáo. Thêm migration cho request ID, trạng thái AI, phiên bản và audit duyệt. Bảo toàn bản nháp cũ. CSV chống diễn giải dữ liệu văn bản thành công thức.
3. Hoàn thiện UI và API từ dữ liệu thật. Trạng thái rỗng, tải, lỗi hoặc thử lại cho từng màn. Lịch sử dùng dữ liệu lúc tạo. Không đưa dữ liệu gốc, mã học viên hay dump DuckDB lên cloud.
4. Nhập KB có ID, bài/KC, văn bản, phiên bản và thông tin duyệt. Chỉ gửi mẫu tổng hợp và nguồn hợp lệ đến Liquid/JEV. Dùng LangGraph cố định, truy xuất BM25 rồi kiểm schema, nguồn và JEV, thử lại tối đa một lần. Chưa bật cho đến khi có tài liệu được phép, mẫu chấm tay và ngưỡng được xác nhận. CLI và dashboard dùng chung hàm nghiệp vụ. Giữ trace và lượng token thật. Không chỉ định kết quả theo câu nguyên văn trong benchmark.
5. Kiểm thử ở môi trường thử nghiệm. Sau nghiệm thu mới cập nhật production qua CI/Railway. Giữ bản snapshot trước và phương án rollback.

## Checklist nghiệm thu thủ công

Ghi mã ca, người kiểm, bản deploy/snapshot, thao tác, mong đợi, thực tế, Đạt/Trượt/Chưa kiểm và bằng chứng đã che thông tin cá nhân.

- H01: đăng nhập sai/đúng, ngoài allowlist, hết phiên, và hai coach không đọc, tải hoặc duyệt chéo báo cáo.
- H02: đối chiếu chỉ số hai bài với DuckDB, gồm lượt/người, mẫu số bằng 0, dưới 10 lượt và đồng hạng.
- H03: tạo nháp, retry, mất kết nối, reload và mở lại từ lịch sử sau khi snapshot thay đổi. Thử trên desktop và mobile.
- H04: mở từng tab, kiểm CSV và lần theo căn cứ Copilot. Kiểm tra lý do chưa có KB.
- H05: chấp nhận, từ chối, yêu cầu sửa, sửa tay, duyệt lại và xung đột giữa hai tab.
- H06: khi đủ điều kiện AI, người chấm kiểm từng trích dẫn và độ phù hợp. Thử lỗi provider, thiếu nguồn và đề xuất bị chặn. Báo cáo số liệu vẫn phải dùng được.

Giữ pytest, pnpm build, run.py check và Docker CI. Bổ sung test hồi quy có mục đích. Chấm benchmark bằng người theo chuẩn CP2, hai người chấm độc lập năm output. Chỉ tính eval thật khi có model/token thật. Giữ expected và bằng chứng các lượt đã chạy. Nhóm bổ sung benchmark lên 20–30 câu cho CP3, sau đó kiểm chi phí theo yêu cầu. Ghi thay đổi sau CP2 ở spec.md §10.

## Handoff kỹ thuật cho AI thực thi

Đọc `AGENTS.md`, `data/DATA_CARD.md`, `docs/learningpulse-design.md` và `spec.md` §7 trước khi sửa code. Giữ hợp đồng `answer(text) -> {"output": str}`, `@model_call` và token usage thật. Không sửa khung chạy BTC, dữ liệu đã ghi hay tiêu chí đã đóng băng. Ảnh tham chiếu xác định bố cục, không cấp nguồn cho số liệu hoặc trạng thái.

| API | Dữ liệu vào và kết quả |
|---|---|
| `GET /api/dashboard?lesson_id=…` | Trả catalog và chỉ số bài đang xem. Nếu bỏ mã bài, chọn bài mới nhất có trong catalog. Không có snapshot thì trả trạng thái thiếu dữ liệu, không tạo số 0 thay thế. |
| `POST /api/analysis-runs` | Nhận `lesson_id`, `request_id`. Xác định chủ sở hữu từ session, chụp snapshot, trả `run_id`. Cùng mã và bài trả cùng bản nháp. Mã đã dùng cho bài khác trả xung đột. |
| `GET /api/analysis-runs` | Liệt kê báo cáo của coach đã xác thực, có lọc bài/trạng thái và phân trang. |
| `GET /api/analysis-runs/{id}` | Đọc snapshot đã lưu, trạng thái AI, đề xuất, kiểm định và lịch sử duyệt. Bản nháp cũ không có metadata mới vẫn mở được và ghi rõ trường nào chưa được ghi nhận. |
| `GET /api/analysis-runs/{id}/export` | Xuất CSV UTF-8 từ dữ liệu đã lưu, chứa số liệu, nguồn có thật và trạng thái duyệt. Không để văn bản từ người dùng hoặc model bị bảng tính thực thi như công thức. |
| `POST /api/analysis-runs/{id}/copilot` | Nhận mã thao tác cố định và `kc_code` nếu thao tác cần một KC. Kết quả giải thích hoặc so sánh phải chỉ đúng căn cứ trong **snapshot đã lưu**. Điều kiện mở AI được kiểm tại server. |
| `POST /api/analysis-runs/{id}/reviews` | Nhận ID đề xuất, phiên bản, quyết định, nhận xét hoặc nội dung sửa. Ghi trạng thái và lịch sử trong cùng transaction. Phiên bản cũ nhận 409 và UI yêu cầu tải lại trước khi lưu tiếp. |

Giữ API cấu hình, xác thực và bài học đang dùng. Với API nghiệp vụ, session thiếu hoặc hết hạn trả 401, ngoài allowlist trả 403, ID báo cáo không tồn tại hoặc không thuộc coach trả 404. Dùng credential đặc quyền chỉ ở backend khi cần, luôn kiểm sở hữu và không cho browser ghi trực tiếp dữ liệu dẫn xuất. Migration tiến về phía trước, giữ các nháp cũ và RLS.

## Điều kiện chuyển giai đoạn

- **Luồng số liệu:** coach kiểm thử bằng tài khoản thật, tạo rồi mở lại báo cáo từ lịch sử và đối chiếu CSV với snapshot đã lưu. Chỉ số tỷ lệ dùng mẫu chấm lần đầu, chú thích đơn vị lượt/người, có trạng thái riêng cho mẫu số 0 và dưới 10 lượt. Kiểm cả màn hẹp lẫn desktop.
- **Luồng duyệt:** người test xác nhận accept, reject, yêu cầu sửa, lưu phiên bản sửa, duyệt lại và lỗi hai tab. Bản sửa không mang điểm JEV của bản gốc. Test bằng fixture nếu chưa có KB và ghi rõ đây là kiểm thử môi trường test.
- **Luồng AI:** có Lesson KB được phép và có nguồn truy vết, bộ mẫu đã được người chấm kiểm, ngưỡng JEV được nhóm duyệt. Lưu riêng kiểm tra bằng code, điểm từng tiêu chí và lý do không có đề xuất. Thiếu căn cứ, AI lỗi hoặc không đạt kiểm định thì giữ báo cáo số liệu. Không dùng kết quả smoke test để công bố chất lượng.
- **Bàn giao:** ghi căn cứ nghiệm thu thủ công cho H01–H06 và đánh dấu phần chưa kiểm. Dùng test tự động để hỗ trợ hồi quy quyền sở hữu, idempotency và trích dẫn. Chỉ báo đạt khi con người đã xác nhận các ca bắt buộc. Đưa thay đổi sau CP2 vào `spec.md` §10, không sửa chuẩn đạt. Staging được nghiệm thu trước khi mở production qua CI/Railway.

