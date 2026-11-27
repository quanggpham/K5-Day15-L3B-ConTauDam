# LearningPulse — Kiến trúc AI

> Tài liệu mô tả thiết kế đích. Trạng thái hiện tại: báo cáo số liệu và lưu nháp đã triển khai; chưa bật RAG, khuyến nghị AI hay JEV trong ứng dụng. Xem README để biết giới hạn.

> Phiên bản 1 · 2026-11-27 · Sơ đồ: [architecture-diagram.html](architecture-diagram.html)
> Nguồn: buổi phỏng vấn làm rõ yêu cầu của nhóm. Mục [§10 Việc còn mở](#10-việc-còn-mở) liệt kê những gì chưa chốt.

## 1. Tóm tắt

LearningPulse giúp **lab coach và giảng viên AI20K** chọn ý kiến thức cần ôn lại trước buổi học. Coach chọn một bài học. Hệ thống tính chỉ số học tập từ dữ liệu pre-class, phát hiện các ý kiến thức (KC) mà học viên đang hổng, lấy đoạn bài giảng liên quan, rồi nhờ LLM đề xuất thứ tự ưu tiên và cách giảng lại, kèm bằng chứng. Coach duyệt và sửa đề xuất. AI không tự gửi gì cho ai.

**Lát cắt MVP:** 1 người dùng (lab coach) · 1 việc (chuẩn bị ôn tập cho một bài) · 1 quyết định AI (KC nào ưu tiên, giảng lại thế nào) · 1 kết quả (bản nháp kế hoạch ôn tập đã duyệt).

**Hình dạng:** workflow cố định trên LangGraph. LLM không tự chọn công cụ hay bước tiếp theo. Bài toán có thứ tự rõ ràng (số liệu → lỗ hổng → ngữ cảnh → đề xuất → kiểm tra), nên dùng agent tự do chỉ thêm rủi ro và chi phí mà không đổi kết quả.

## 2. Người dùng, quyền truy cập và người chịu ảnh hưởng

| | Quyết định |
|---|---|
| Người dùng chính | Lab coach và giảng viên AI20K, chung **một vai**, xem được mọi lớp |
| Đăng nhập | Supabase Auth (Google hoặc email) |
| Ai được vào | Chỉ email nằm trong **allowlist**. FastAPI kiểm JWT của Supabase và allowlist ở mọi request |
| Ai không được vào | Học viên, người ngoài. Không có trang đăng ký công khai |
| Quyền của AI | Chỉ đọc số liệu tổng hợp và bài giảng. Không có công cụ nào tác động ra ngoài |
| Quyền của coach | Duyệt, sửa tay, từ chối đề xuất. Bản nháp và lịch sử duyệt lưu ở Supabase Postgres |

**Ai chịu ảnh hưởng khi AI sai:**

- **Coach / giảng viên:** mất thời gian chuẩn bị theo một đề xuất sai.
- **Học viên cả lớp:** buổi ôn lệch trọng tâm, lỗ hổng thật không được lấp.
- **BTC / đội nội dung:** nếu dựa vào báo cáo để sửa bài giảng, số sai dẫn tới sửa sai chỗ.

Từng học viên **không** bị ảnh hưởng trực tiếp, vì hệ thống không hiện, không xếp hạng, không gửi gì theo từng học viên.

## 3. Thành phần

| Thành phần | Công nghệ | Vai trò | Thư mục |
|---|---|---|---|
| Dashboard | React, Vite, TS, Tailwind, shadcn/ui, Redux Toolkit, Recharts | Chọn bài, xem chỉ số, xem/duyệt/sửa đề xuất | `codebase/frontend/` |
| API | FastAPI, Pydantic | Kiểm JWT + allowlist, REST, phục vụ bản build tĩnh của frontend | `codebase/backend/api/`, `main.py` |
| Workflow AI | LangGraph | Luồng cố định: chặn đầu vào → chỉ số → lỗ hổng → RAG → LLM → chặn đầu ra | `codebase/backend/agents/` |
| Phân tích | DuckDB, Pandas | Tính chỉ số theo bài/KC, phát hiện lỗ hổng, gắn cờ mẫu nhỏ | `codebase/backend/analytics/` |
| RAG | BM25 + lọc metadata (bài, KC) | Lấy đoạn bài giảng liên quan đến lỗ hổng | `codebase/backend/rag/` |
| Guardrails + JEV | Code tự viết + JEV (LLM-judge) | Chặn đầu vào, chặn đầu ra, eval offline | `codebase/backend/security/`, `codebase/backend/evaluation/` |
| Schema | Pydantic | Định dạng đầu ra có cấu trúc của LLM, hợp đồng API | `codebase/backend/schemas/` |
| LLM | Liquid API, LFM3-1.7B | Model đề xuất | gọi qua `codebase/ai.py`; JEV dùng TypeSafe API |
| Auth + lưu duyệt | Supabase (Auth + Postgres) | Đăng nhập, bảng đề xuất và lịch sử duyệt | — |
| Quan sát | Langfuse Cloud | Trace từng phiên | — |
| Khung BTC | `run.py`, `codebase/agent.py` | `answer(text)` gọi **chung** workflow với dashboard | không sửa khung |

**Triển khai:** một service trên Railway. FastAPI phục vụ luôn bản build của Vite: một URL, không cần CORS, ít thứ hỏng lúc demo.

**Dùng chung workflow:** `codebase/agent.py` gọi workflow trong `backend/agents`, và mọi lượt gọi model đi qua `call_model` trong `codebase/ai.py` để khung BTC đếm token. Nhờ vậy `run.py eval` chấm đúng thứ coach dùng thật.

## 4. Luồng chính

Xem sơ đồ 2 trong [architecture-diagram.html](architecture-diagram.html).

1. **Đầu vào.**
   - Trên dashboard, coach chỉ **chọn bài học** (`lesson_id`), không có ô nhập chữ tự do cho AI.
   - Bộ eval gửi nguyên chuỗi text vào `answer(text)`.
2. **Chặn đầu vào** (code trước, JEV sau).
   - Code tách `lesson_id` hợp lệ khỏi text và chặn các mẫu rõ ràng: hỏi mã học viên `hv`, đòi xếp hạng, đòi dữ liệu thô, lệnh ghi đè hệ thống.
   - JEV chỉ chạy khi text **còn phần nào ngoài** `lesson_id`. JEV đánh giá ý định, phạm vi nghiệp vụ và nguy cơ vi phạm chính sách dữ liệu.
   - Không đạt thì **từ chối, nêu lý do**, không gọi LLM đề xuất.
3. **Chỉ số + lỗ hổng.**
   - Đọc bảng tổng hợp (DuckDB) theo bài và `kc_code`: tỷ lệ sai ở lần trả lời đầu (`lan_thu = 1`), số lần làm lại, tỷ lệ hoàn thành, hành vi học.
   - Code (không phải LLM) xếp hạng ứng viên lỗ hổng.
   - KC có quá ít lượt trả lời vẫn hiện nhưng **gắn cờ "chưa đủ dữ liệu"** và **không được xếp ưu tiên**.
4. **Truy xuất bài giảng.** BM25 + lọc metadata theo bài/KC trên Lesson KB.
5. **LLM đề xuất.** Đầu vào gồm số đã tổng hợp và đoạn bài giảng. LLM trả kết quả có cấu trúc (schema Pydantic): thứ tự ưu tiên, lý do, phương pháp giảng lại, và trích dẫn tới chỉ số cùng đoạn bài.
6. **Chặn đầu ra.**
   - Code kiểm: mọi con số khớp DuckDB, mọi trích dẫn có trong ngữ cảnh đã đưa vào, đúng schema, không có `hv`.
   - JEV kiểm: đề xuất có căn cứ không, có phù hợp không, có suy diễn vượt bằng chứng không.
7. **Xử lý khi đầu ra lỗi** (cùng một luật cho lỗi của code lẫn của JEV):
   - **Lỗi lần 1:** gọi lại LLM một lần, kèm lý do bị loại.
   - **Lỗi lần 2:** trả **báo cáo chỉ có số liệu** (chỉ số + lỗ hổng, không có đề xuất AI) kèm thông báo.
8. **Coach duyệt.** Coach chấp nhận, từ chối hoặc **sửa tay** từng đề xuất. Coach không ra lệnh cho AI viết lại, nên không mở thêm chỗ cho prompt injection. Bản nháp và lịch sử duyệt (ai, sửa gì, lúc nào) lưu vào Supabase Postgres. Không có gì được gửi tới học viên hay LMS.

**Không cache:** mỗi lần bấm "Phân tích" là một lượt gọi LLM mới.

## 5. Dữ liệu và ranh giới tin cậy

**Nguồn:** dataset pre-class do BTC cung cấp (05/11 → 25/11/2026, Day01 → Day13), gồm 721 tài khoản (436 có hoạt động), 107.709 sự kiện, 3.776 lượt trả lời, 1.260 lượt chat, 2.472 mục đã hoàn thành. Dataset đã thay mã học viên (`L0001…`) và không có câu chữ học viên viết.

**Có sẵn để gom theo ý kiến thức:** `answers.csv` và `events.csv` đều có `lesson_id`, `module_code` và `kc_code`, nên không cần gắn nhãn thủ công. Riêng câu nhắn AI (`nguon = chat`) chỉ biết tới module.

**Pipeline xử lý dữ liệu (ETL):**

```
CSV gốc (chỉ ở máy local, thư mục data-btc/ đã gitignore)
   │  ETL chạy local — DuckDB/Pandas
   ▼
Bảng tổng hợp theo bài / module / KC  (không có hv, không có dòng thô)
   │  commit + đóng gói cùng app
   ▼
Server Railway — chỉ đọc bảng tổng hợp
```

**Ranh giới:**

| Dữ liệu | Server | Liquid API | Langfuse | Supabase |
|---|---|---|---|---|
| CSV gốc, mã `hv` | ✗ | ✗ | ✗ | ✗ |
| Chỉ số tổng hợp theo bài/KC | ✓ | ✓ | ✓ | ✓ (trong đề xuất) |
| Đoạn bài giảng (Lesson KB) | ✓ | ✓ | ✓ | — |
| Email coach | — | ✗ | ✗ | ✓ (auth) |
| Đề xuất + lịch sử duyệt | ✓ | — | ✓ (output) | ✓ |

**Lesson KB:** dataset BTC **không** kèm lời giảng hay slide. Cột `transcript` chỉ có tên file. Vì vậy cơ sở kiến thức phải xây riêng từ nội dung được phép dùng, mỗi đoạn có metadata `lesson_id`, `kc_code`. Nguồn cụ thể chưa chốt.

## 6. Guardrails và JEV

| Lớp | Khi nào | Kiểm gì | Không đạt thì |
|---|---|---|---|
| Input: code | Mọi request | `lesson_id` hợp lệ; mẫu cấm (hỏi `hv`, xếp hạng, đòi dữ liệu thô, ghi đè hệ thống) | Từ chối + lý do |
| Input: JEV | Chỉ khi text còn phần ngoài `lesson_id` | Ý định, phạm vi nghiệp vụ, vi phạm chính sách dữ liệu | Từ chối + lý do |
| Output: code | Mọi đề xuất | Số khớp DuckDB; trích dẫn có trong ngữ cảnh; đúng schema; không có `hv` | Gọi lại 1 lần → báo cáo số liệu |
| Output: JEV | Mọi đề xuất qua được lớp code | Có căn cứ, phù hợp, không suy diễn quá bằng chứng | Gọi lại 1 lần → báo cáo số liệu |
| Offline: JEV | `run.py eval` | Benchmark 25 câu theo rubric | Ghi vào `eval/report.md` |
| CI | Mỗi PR | Promptfoo (tấn công prompt), Gitleaks (lộ secret) | Chặn merge |

**AI không được làm, kể cả khi người dùng yêu cầu:** tiết lộ hay suy đoán danh tính học viên; xếp hạng học viên; trả dữ liệu dòng thô; bịa số không có trong DuckDB; tự gửi hay tự sửa bất cứ thứ gì bên ngoài.

## 7. Edge cases và hành vi mong muốn

| Kịch bản | Lớp | Hành vi mong muốn |
|---|---|---|
| Bài có dữ liệu đầy đủ | — | Đề xuất xếp hạng, có trích dẫn số và đoạn bài, chờ coach duyệt |
| KC có ít lượt trả lời (mẫu nhỏ) | 2 | Hiện riêng với cờ "chưa đủ dữ liệu", không xếp ưu tiên |
| Bài không có dữ liệu / `lesson_id` không tồn tại | 1 | Báo không có dữ liệu cho bài này, không gọi LLM |
| Có chỉ số nhưng Lesson KB không có đoạn liên quan | 1 | Vẫn nêu lỗ hổng từ số liệu; ghi rõ "chưa có căn cứ bài giảng", không bịa nội dung |
| Dữ liệu mâu thuẫn (vd tỷ lệ hoàn thành cao nhưng sai nhiều) | 4 | Nêu cả hai số, không tự kết luận nguyên nhân vượt bằng chứng; đầu ra bị JEV kiểm |
| LLM bịa số / trích dẫn sai | 1 | Code bắt → gọi lại 1 lần → báo cáo số liệu |
| Đòi tên, mã học viên hay danh sách học viên yếu nhất | 3 | Bị chặn đầu vào, từ chối + lý do |
| Prompt injection trong text eval ("bỏ qua hướng dẫn…") | 3 | Code hoặc JEV chặn; không gọi LLM đề xuất |
| Câu hỏi ngoài phạm vi (không liên quan bài học) | 3 | JEV chặn, từ chối + lý do |
| Liquid API lỗi, chậm hoặc hết quota | — | Báo lỗi, đề nghị thử lại sau |
| Coach sửa đề xuất | — | Lưu bản sửa + ai sửa + lúc nào; không gọi lại AI |

## 8. Rủi ro production

| Rủi ro | Hậu quả | Chặn ở đâu |
|---|---|---|
| Lộ dữ liệu học viên ra bên thứ ba | Vi phạm luật dùng dataset | Server chỉ có bảng tổng hợp; code kiểm không có `hv` ở đầu ra; Gitleaks; `.gitignore` cho `data-btc/` |
| LLM bịa số hoặc suy diễn | Coach ôn sai trọng tâm | Số do code tính; chặn đầu ra (code + JEV); coach duyệt |
| Prompt injection | AI làm việc ngoài thẩm quyền | Dashboard không có ô nhập chữ tự do; chặn đầu vào; AI không có công cụ ghi |
| Người ngoài truy cập | Lộ báo cáo nội bộ | Supabase Auth + allowlist kiểm ở FastAPI |
| Liquid API sập lúc demo | Không có đề xuất | Báo lỗi rõ ràng *(xem câu hỏi mở 5)* |
| Chi phí tăng | Vượt ngân sách | Workflow cố định, retry tối đa 1 lần; mô phỏng chi phí ≥ 50 phiên |
| Railway redeploy mất trạng thái | Mất lịch sử duyệt | Trạng thái lưu ở Supabase, server không giữ trạng thái |
| Rò API key | Bị lạm dụng tài khoản | Key nằm trong biến môi trường Railway; Gitleaks trong CI |

**Chi phí mỗi phiên** *(tự ước tính)*: 1 lượt LLM đề xuất + 1 lượt JEV đầu ra, cộng 1 lượt JEV đầu vào nếu có text tự do. Có retry thì tối đa gấp đôi. Không cache nên số lượt gọi tăng tuyến tính theo số lần bấm. Con số chính thức lấy từ `python run.py simulate`.

## 9. Quyết định và lý do

| Quyết định | Phương án đã loại | Lý do |
|---|---|---|
| Workflow cố định | Agent tự do, nhiều agent | Thứ tự bước đã rõ; dễ kiểm, rẻ, ít rủi ro |
| Số do code tính, LLM chỉ đề xuất | LLM tự đọc dữ liệu | Độ chính xác số cần 100%; LLM không đáng tin để tính |
| Dashboard chỉ cho chọn bài | Chat tự do | Gần như không có chỗ cho prompt injection từ người dùng |
| Tiền xử lý offline | Tính ngay mỗi request | Nhanh; số ổn định giữa các lần chạy; server không giữ dữ liệu thô |
| Coach chỉ sửa tay | Coach ra lệnh cho AI viết lại | Không mở thêm đường prompt injection; người quyết định cuối |
| Supabase Auth + Postgres | JWT tự làm, lưu file | Có sẵn đăng nhập Google/email; bền khi Railway redeploy |
| Một service Railway | Tách frontend/backend | Một URL, không cần CORS, ít điểm hỏng |
| Dùng chung workflow với `answer(text)` | Luồng rút gọn riêng để chấm | Eval phản ánh đúng sản phẩm thật |

## 10. Việc còn mở

1. **Nguồn Lesson KB:** nhóm tự viết, hay trích từ tài liệu khoá học được BTC cho phép?
2. **Ngưỡng mẫu nhỏ:** dưới bao nhiêu học viên trả lời lần đầu thì gắn cờ. Chốt sau khi khảo sát phân bố dữ liệu.
3. **Ngưỡng "đạt" của guardrail đầu ra:** JEV chấm theo thang nào, bao nhiêu thì qua. Phải chốt trước CP2 cùng `eval/metric_spec.yaml`.
4. **Nội dung trace trên Langfuse:** đề xuất chỉ ghi số tổng hợp, prompt và output, không ghi dữ liệu thô.
5. **Khi Liquid API sập:** hiện tại chọn "chỉ báo lỗi". Bước chỉ số + lỗ hổng không cần LLM, nên vẫn có thể hiện báo cáo số liệu thay vì chỉ báo lỗi.
6. **Allowlist:** lưu ở biến môi trường hay bảng Supabase, và ai quản lý.
