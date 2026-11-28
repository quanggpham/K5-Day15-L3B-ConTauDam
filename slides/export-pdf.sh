#!/bin/sh
# Xuất slides/demo-slides.html -> demo-slides.pdf (gốc repo) bằng Chrome đã cài sẵn, không cài thêm gì.
# Chạy từ bất kỳ đâu: sh slides/export-pdf.sh
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$ROOT/demo-slides.pdf" "file://$ROOT/slides/demo-slides.html"
echo "Xong: $ROOT/demo-slides.pdf (phải đủ 8 trang, không còn ô vàng [chờ ...])"
