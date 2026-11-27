# ConTauDam — LearningPulse

LearningPulse hỗ trợ lab coach tìm nội dung cần ôn tập từ dữ liệu pre-class. Pain point cần xác minh bằng phỏng vấn và dữ liệu. MVP dự kiến tổng hợp số liệu, truy xuất kiến thức và đề xuất có căn cứ để coach quyết định.

## Trạng thái

CLI và dashboard dùng chung báo cáo số liệu tổng hợp; không có khuyến nghị AI khi chưa có Lesson KB. Dashboard có đăng nhập, allowlist, chọn bài và lưu bản nháp. Adapter Liquid đã có nhưng chưa nối vào workflow; RAG, JEV, khuyến nghị AI và Langfuse chưa tích hợp.

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

### Allowlist giảng viên và coach

Migration `20261127000001_coach_allowlist.sql` tạo bảng allowlist và yêu cầu email trong JWT nằm trong bảng cho mọi truy cập các bảng ứng dụng. Người quản trị quản lý email viết thường qua Supabase SQL Editor; client không có quyền đọc hoặc sửa bảng allowlist. Cần tạo người dùng trong Supabase Auth riêng. Không nhập mật khẩu hoặc service-role key vào repo.

Backend có `/api/me` để xác thực token với Supabase Auth và kiểm tra allowlist qua RLS; cả hai đều phải thành công. Thay đổi backend/frontend này phải được deploy mới có tác dụng trên Railway.

`lesson_metrics` hiện tổng hợp theo `lesson_id` và `kc_code`: tỷ lệ sai bằng số lượt sai chia số lượt đã được chấm ở lần đầu; lượt chưa chấm được tính riêng. Dashboard đọc snapshot đã lọc trên Railway; API báo lỗi khi snapshot chưa có.

### Chuẩn bị báo cáo tổng hợp

Chạy `uv run python -m codebase.backend.analytics.ingest`, sau đó `uv run python -m codebase.backend.analytics.export_snapshot`. Snapshot `data/aggregate.json` được ignore, không chứa mã học viên; nhóm dưới 5 học viên có lượt chấm đúng/sai ở lần đầu bị che số đếm và tỷ lệ. Ngoài ra KC dưới 10 lượt được chấm ở lần đầu không được xếp ưu tiên, theo quyết định CP2 trong canvas. Backend đọc `AGGREGATE_SNAPSHOT_PATH`; Railway dùng `/data/aggregate.json` trên volume. CLI nhận chính xác mã bài học và trả báo cáo cùng luồng với dashboard; câu hỏi tự do hiện chưa hỗ trợ. Chưa có Lesson KB, JEV và AI recommendation hoạt động; báo cáo không phải kết quả đánh giá model.

`LIQUID_API_KEY` và `TYPESAFE_API_KEY` được đồng bộ từ GitHub Actions secrets sang Railway trong bước deploy. Adapter Liquid đã chuẩn bị nhưng chưa nối vào luồng báo cáo. Điền `MODEL_PROVIDER=liquid`, `MODEL_NAME=lfm3-1.7b` chỉ khi kiểm thử adapter; mặc định là fake.

Các module BM25 theo `lesson_id`/`kc_code` và JEV đánh giá hai tiêu chí đã có kiểm thử với dữ liệu giả, nhưng chưa nối vào workflow: nhóm cần bổ sung nguồn Lesson KB được phép và chốt cách chấm/hiệu chuẩn trước khi bật đề xuất AI.

Để cập nhật snapshot Railway sau khi kiểm tra dữ liệu nguồn và ngưỡng, dùng Railway CLI đã liên kết đúng project/environment/service và SSH key đã đăng ký: `railway volume files --volume <VOLUME_ID> upload data/aggregate.json /aggregate.json --overwrite --json`. Kiểm tra nội dung tổng hợp trước khi tải; không tải `data/pre_class/` hoặc database gốc lên volume.
