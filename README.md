# ConTauDam — LearningPulse

LearningPulse hỗ trợ lab coach tìm nội dung cần ôn tập từ dữ liệu pre-class. Pain point cần xác minh bằng phỏng vấn và dữ liệu. MVP dự kiến tổng hợp số liệu, truy xuất kiến thức và đề xuất có căn cứ để coach quyết định.

## Trạng thái

CLI và dashboard dùng chung báo cáo số liệu tổng hợp. CLI trả lời câu hỏi tiếng Việt qua model Liquid khi `MODEL_PROVIDER=liquid`, chỉ với số liệu tổng hợp và kiểm từng con số bằng code. Lesson KB đã nạp (xem `data/DATA_CARD.md`) nhưng khuyến nghị AI trên web chưa bật: đề xuất AI và JEV chưa nối vào ứng dụng, Langfuse chưa tích hợp. Dashboard có đăng nhập, chọn bài và lưu bản nháp.

## Cài đặt và chạy

Yêu cầu Python 3.13, uv, Node.js và pnpm. Tại gốc repo:

```powershell
uv sync --locked
Copy-Item .env.example .env
uv run python -m codebase.backend.analytics.ingest
uv run uvicorn codebase.backend.main:app --reload
```

Trong terminal khác:

```powershell
cd codebase/frontend
pnpm install --frozen-lockfile
pnpm dev
```

Lệnh import đọc `data/pre_class/`, tạo `data/learning_pulse.duckdb` local. Database chứa dữ liệu BTC, không commit. Backend hiện chưa đọc database. Knowledge base bài giảng phải xây dựng riêng từ tài liệu được phép sử dụng.

## Lệnh BTC

```powershell
uv run python run.py
uv run python run.py check
uv run python run.py eval --try
uv run python run.py eval
uv run python run.py score eval/run-1.csv
uv run python run.py simulate --try
uv run python run.py simulate
```

Eval và mô phỏng model giả không tính là lượt thật. Không sửa kết quả đã chạy hoặc tiêu chuẩn đạt sau CP2.

## Cấu trúc

`codebase/frontend` là giao diện; `codebase/backend` là API và analytics; `codebase/agent.py`, `ai.py`, `tools.py` là hợp đồng CLI BTC. `data/`, `evidence/`, `eval/`, `cost/`, `validation/`, `reflection/` chứa dữ liệu, bằng chứng và hồ sơ nộp. Thành viên xem [TEAMS.md](TEAMS.md); thiết kế và tiêu chuẩn xem [spec.md](spec.md).

## Dùng AI

Nhóm ghi công cụ, mục đích và người kiểm tra tại [docs/ai-usage.md](docs/ai-usage.md). Không dùng AI để tạo bằng chứng phỏng vấn hoặc số liệu giả.

## Công cụ phát triển

- `uv run python -m pytest tests/test_ingest.py -q`: kiểm thử import DuckDB.
- Trong `codebase/frontend`: `pnpm exec promptfoo --version` và `pnpm build`.
- Windows: tải bản `windows_x64.zip` từ trang releases chính thức https://github.com/gitleaks/gitleaks/releases, giải nén vào `.tools/gitleaks/`; kiểm tra bằng `.\.tools\gitleaks\gitleaks.exe version`. Thư mục này được ignore.

Import kiểm tra cột bắt buộc và cấu trúc CSV trước khi thay database. Database đang mở có thể khiến thao tác thay file thất bại trên Windows; đóng các kết nối trước khi import lại.

## Triển khai Railway và Supabase

Tạo Supabase project, áp dụng các migration trong `supabase/migrations/` qua Supabase CLI sau khi review. Tạo tài khoản bằng Supabase Auth; app đăng nhập bằng email/mật khẩu. RLS chỉ cho phép người dùng truy cập dữ liệu thuộc tài khoản của mình; role do hệ thống quản lý. Màn hình có thể lưu báo cáo số liệu thành bản nháp trong `analysis_runs`.

Tạo Railway service dùng Dockerfile, workflow đồng bộ `SUPABASE_URL` và `SUPABASE_PUBLISHABLE_KEY` từ GitHub environment secrets sang service variables; chỉ dùng publishable key, không đưa secret/service-role key vào frontend. Bật domain và health check `/api/health`. Trong GitHub environment `production`, tạo secrets `RAILWAY_TOKEN`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `LIQUID_API_KEY`, `TYPESAFE_API_KEY` và variable `RAILWAY_SERVICE` là tên service. Tắt auto-deploy GitHub trong Railway để tránh deploy trùng. Workflow kiểm thử, build image và deploy khi push main; `railway up --ci` chỉ xác nhận build, kiểm tra trạng thái deployment/health trên Railway sau đó.

Frontend local dùng `pnpm dev`, backend dùng `uv run uvicorn codebase.backend.main:app --reload`; đặt hai biến Supabase trong môi trường backend trước khi chạy. Supabase lưu tài khoản và kết quả; DuckDB giữ dữ liệu pre-class local. Không có bước tự đồng bộ dataset lên cloud.

### Quyền truy cập

Migration `20261128000000_allow_auth_users.sql` cho phép mọi tài khoản còn tồn tại trong Supabase Auth truy cập, không cần thêm email vào allowlist. RLS vẫn giới hạn dữ liệu theo chủ sở hữu. Quản trị viên cần kiểm soát việc tạo tài khoản và cấu hình đăng ký trong Supabase Auth. Không nhập mật khẩu hoặc service-role key vào repo.

Backend có `/api/me` để xác thực token với Supabase Auth và kiểm tra tài khoản qua RPC; cả hai đều phải thành công. Cần áp dụng migration cho Supabase và deploy frontend để cập nhật thông tin hiển thị trên Railway.

`lesson_metrics` hiện tổng hợp theo `lesson_id` và `kc_code`: tỷ lệ sai bằng số lượt sai chia số lượt đã được chấm ở lần đầu; lượt chưa chấm được tính riêng. Dashboard đọc snapshot đã lọc trên Railway; API báo lỗi khi snapshot chưa có.

### Chuẩn bị báo cáo tổng hợp

Chạy `uv run python -m codebase.backend.analytics.ingest`, sau đó `uv run python -m codebase.backend.analytics.export_snapshot`. Snapshot `data/aggregate.json` được ignore, không chứa mã học viên; số tổng hợp của nhóm nhỏ được hiển thị theo lựa chọn của nhóm, nên cần thận trọng với nguy cơ suy đoán cá nhân. Ngoài ra KC dưới 10 lượt được chấm ở lần đầu không được xếp ưu tiên; các KC có cùng tỷ lệ sai được hiển thị đồng hạng, theo quyết định CP2. Lệnh export tạo cả `data/aggregate.json` và `data/aggregate.v2.json` (snapshot v2 cho dashboard/báo cáo, bài sắp theo natural sort, vd L2 trước L10). Backend đọc `AGGREGATE_SNAPSHOT_PATH` và `AGGREGATE_SNAPSHOT_V2_PATH`; nếu không đặt biến v2, backend dùng `aggregate.v2.json` cùng thư mục với `AGGREGATE_SNAPSHOT_PATH`. Trên Railway đặt `AGGREGATE_SNAPSHOT_PATH=/data/aggregate.json` và `AGGREGATE_SNAPSHOT_V2_PATH=/data/aggregate.v2.json` (trỏ vào volume). CLI nhận câu hỏi tiếng Việt, tìm mọi bài được nhắc (mã đầy đủ hoặc bí danh như `Day 05`), hoặc câu hỏi về toàn bộ dữ liệu, rồi dùng cùng báo cáo với dashboard làm căn cứ; yêu cầu rõ ràng về dữ liệu cá nhân, bí mật hoặc tự gửi/duyệt bị từ chối trước khi đọc dữ liệu. Câu hỏi không chỉ ra bài và không có số liệu thì CLI hỏi lại. Số đếm phụ trợ (dòng chat theo bài, lượt lần hai) nằm ở `data/extra_counts.json`, cũng do lệnh export tạo. JEV và AI recommendation trên web chưa hoạt động.

`LIQUID_API_KEY` và `TYPESAFE_API_KEY` được đồng bộ từ GitHub Actions secrets sang Railway trong bước deploy. Điền `MODEL_PROVIDER=liquid`, `MODEL_NAME=lfm3-1.7b` để CLI gọi model thật; mặc định là fake. Khi `MODEL_PROVIDER=liquid`, `answer()` gửi số liệu tổng hợp cho model và kiểm từng con số trong câu trả lời bằng code; sai thì thử lại một lần rồi quay về báo cáo số liệu. Luồng web chưa gọi model.

Các module BM25 theo `lesson_id`/`kc_code` và JEV đánh giá hai tiêu chí đã có kiểm thử với dữ liệu giả, nhưng chưa nối vào workflow: nhóm cần bổ sung nguồn Lesson KB được phép và chốt cách chấm/hiệu chuẩn trước khi bật đề xuất AI.

Để cập nhật snapshot Railway sau khi kiểm tra dữ liệu nguồn và ngưỡng, dùng Railway CLI đã liên kết đúng project/environment/service và SSH key đã đăng ký: `railway volume files --volume <VOLUME_ID> upload data/aggregate.json /aggregate.json --overwrite --json` và `railway volume files --volume <VOLUME_ID> upload data/aggregate.v2.json /aggregate.v2.json --overwrite --json` (tải cả hai file cùng lúc để dashboard v2 và báo cáo v1 khớp nhau). Kiểm tra nội dung tổng hợp trước khi tải; không tải `data/pre_class/` hoặc database gốc lên volume.

Module thử nghiệm `backend/agents/recommend.py` yêu cầu mỗi KC có nguồn được duyệt, kiểm tra định dạng, mã trích dẫn, dấu hiệu dữ liệu cá nhân và số trong output, sau đó nhận hai điểm JEV; thất bại thì thử lại một lần rồi chỉ trả số liệu. Ngưỡng 0,9 trong module là giá trị thử nghiệm chưa hiệu chuẩn, chưa phải chuẩn đạt CP2. Module này chưa nối vào ứng dụng; các bộ lọc không bảo đảm phát hiện mọi dữ liệu cá nhân, số sai hay prompt injection.

### Bảo mật và vận hành

- **Header bảo mật:** backend gắn CSP, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` cho mọi response (kể cả lỗi 500). CSP đọc `SUPABASE_URL` ở **mỗi request** để cho phép kết nối đăng nhập tới Supabase; thiếu hoặc sai biến này thì `connect-src` chỉ còn `'self'` và đăng nhập sẽ hỏng. `script-src 'self'` không cho script nội tuyến: nếu thêm script nội tuyến hoặc nguồn ngoài phải sửa `codebase/backend/security/headers.py`. CSP chưa được kiểm trên trình duyệt thật: sau mỗi lần deploy mở Console xem có báo vi phạm khi vẽ biểu đồ hoặc mở hộp thoại.
- **HSTS:** backend không đặt; bật ở proxy/Railway.
- **Hạn mức tạo báo cáo:** 20 lần/phút/coach (`RUN_CREATE_LIMIT_PER_MIN`), vượt thì trả 429 kèm `Retry-After`; retry cùng `request_id` không bị tính. Bộ đếm nằm trong bộ nhớ của một tiến trình: chạy nhiều bản sao thì hạn mức nhân lên và restart sẽ đặt lại, khi đó cần hạn mức ở proxy.
- **Service role:** `SUPABASE_SERVICE_ROLE_KEY` chỉ backend dùng (ghi báo cáo, duyệt, audit, luôn lọc theo chủ sở hữu từ phiên đăng nhập); không đưa vào frontend hay `/api/config`. Thiếu biến này các API ghi trả 503.
- **Áp migration:** `…000003` và `…000004` thu hồi quyền ghi trực tiếp của browser trên bảng báo cáo, nên áp cùng lúc với deploy code mới (code cũ còn ghi trực tiếp từ browser sẽ lỗi). Thử trên Supabase test (`supabase db reset`) trước; hai migration chưa từng chạy trên Postgres thật. Workflow deploy không tự chạy migration.
- **Ẩn số liệu nhóm nhỏ:** trong snapshot v2 (dashboard, báo cáo đã lưu, CSV, Copilot), KC có dưới 5 học viên bị ẩn toàn bộ số (`MIN_LEARNERS` trong `codebase/backend/analytics/metrics.py`). Luồng CLI/`answer()` v1 dùng cho benchmark chưa áp quy tắc này.

### Nạp và duyệt Lesson KB

Coach đăng nhập mở **KB bài giảng**, chọn bài, khai nguồn được phép và tải PDF có lớp chữ hoặc Markdown UTF-8 (tối đa 10 MB, 100 trang PDF). PDF scan cần được chuyển thành văn bản trước; ứng dụng không OCR. Kiểm tra nội dung và KC đề xuất, lưu sửa rồi duyệt từng đoạn. Các đoạn đã duyệt dùng chung; sửa nội dung hoặc ánh xạ sẽ tạo phiên bản mới và yêu cầu duyệt lại. Tải bản khác với cùng bài, nguồn và tên tệp sẽ thay phiên bản hiện tại; đoạn cũ ngừng được truy xuất. Có thể tìm thử căn cứ đã duyệt theo bài/KC ngay trên trang.

Nạp hàng loạt dùng `uv run python scripts/ingest_kb.py --files <thu_muc> --propose data/kb_mapping.csv`, sau đó người có chuyên môn kiểm tra và ghi `confirmed=yes` cho từng dòng đúng. Chạy lại với `--files <thu_muc> --mapping data/kb_mapping.csv` để dry-run, thêm `--apply --confirm-rights` mới ghi Supabase. Các file notes/quiz có cấu trúc cũ vẫn dùng `--notes` và `--quiz`. Script cần snapshot v2; chỉ nạp tài liệu có quyền sử dụng.

Migration `20261128000005` và `20261128000006` cần kiểm trên Supabase test cùng các migration còn thiếu trước production; kiểm `supabase/tests/knowledge_review_check.sql`. Việc nạp KB không bật tính năng tạo nội dung AI. Không gửi dữ liệu học viên hoặc raw chat vào KB.
