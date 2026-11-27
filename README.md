# ConTauDam — LearningPulse

LearningPulse hỗ trợ lab coach tìm nội dung cần ôn tập từ dữ liệu pre-class. Pain point cần xác minh bằng phỏng vấn và dữ liệu. MVP dự kiến tổng hợp số liệu, truy xuất kiến thức và đề xuất có căn cứ để coach quyết định.

## Trạng thái

CLI BTC đang dùng model giả. Backend có health endpoint, frontend là trang nền. Analytics, RAG, đề xuất, JEV, Liquid API và Langfuse chưa được tích hợp. LFM3-1.7B qua Liquid API là model dự kiến; cấu hình trong `.env.example` chỉ chuẩn bị cho bước sau.

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

Tạo Supabase project, chạy migration `supabase/migrations/20261127000000_initial.sql` qua Supabase CLI hoặc SQL Editor sau khi review. Tạo tài khoản bằng Supabase Auth; app đăng nhập bằng email/mật khẩu. RLS chỉ cho phép người dùng truy cập dữ liệu thuộc tài khoản của mình; role do hệ thống quản lý. Chưa nối màn hình với dữ liệu analysis.

Tạo Railway service dùng Dockerfile, workflow đồng bộ `SUPABASE_URL` và `SUPABASE_PUBLISHABLE_KEY` từ GitHub environment secrets sang service variables; chỉ dùng publishable key, không đưa secret/service-role key vào frontend. Bật domain và health check `/api/health`. Trong GitHub environment `production`, tạo secrets `RAILWAY_TOKEN`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` và variable `RAILWAY_SERVICE` là tên service. Tắt auto-deploy GitHub trong Railway để tránh deploy trùng. Workflow kiểm thử, build image và deploy khi push main; `railway up --ci` chỉ xác nhận build, kiểm tra trạng thái deployment/health trên Railway sau đó.

Frontend local dùng `pnpm dev`, backend dùng `uv run uvicorn codebase.backend.main:app --reload`; đặt hai biến Supabase trong môi trường backend trước khi chạy. Supabase lưu tài khoản và kết quả; DuckDB giữ dữ liệu pre-class local. Không có bước tự đồng bộ dataset lên cloud.
