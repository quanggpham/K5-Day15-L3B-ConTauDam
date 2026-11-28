# Kiểm tra guardrail AI

Pytest chạy trong CI với model giả. Promptfoo chạy thủ công với Liquid và snapshot tổng hợp giả. Chuẩn bị MODEL_PROVIDER=liquid, MODEL_NAME và LIQUID_API_KEY từ môi trường hoặc .env local. Không đưa dữ liệu lớp học vào cấu hình này.

Từ thư mục gốc, chạy bằng PowerShell:

```powershell
uv sync
pnpm --dir codebase/frontend install --frozen-lockfile
$env:PROMPTFOO_DISABLE_TELEMETRY = '1'
$env:PROMPTFOO_PYTHON = (Resolve-Path .venv/Scripts/python.exe).Path
node codebase/frontend/node_modules/promptfoo/dist/src/entrypoint.js eval -c eval/ai-safety/promptfooconfig.yaml --no-cache --max-concurrency 1
```

Ca hợp lệ yêu cầu phản hồi thật có token usage và đúng căn cứ. Các ca từ chối yêu cầu không gọi model. Coach vẫn cần đọc bản nháp web và đối chiếu với nguồn đã duyệt trước demo.
