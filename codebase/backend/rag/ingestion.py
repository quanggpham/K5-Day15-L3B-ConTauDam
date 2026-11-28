"""Trích xuất KB từ Markdown/PDF, không ghi tệp gốc."""
import hashlib
import io
import re
from pathlib import Path
from pypdf import PdfReader

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 100
MAX_CHUNKS = 500


def extract_chunks(filename: str, data: bytes) -> list[dict]:
    if not data or len(data) > MAX_BYTES:
        raise ValueError('Tệp rỗng hoặc lớn hơn 10 MB.')
    suffix = Path(filename).suffix.lower()
    if suffix == '.md':
        try:
            text = data.decode('utf-8-sig')
        except UnicodeDecodeError:
            raise ValueError('Markdown phải dùng UTF-8.') from None
    elif suffix == '.pdf':
        try:
            reader = PdfReader(io.BytesIO(data), strict=True)
            if reader.is_encrypted:
                raise ValueError('PDF có mật khẩu chưa được hỗ trợ.')
            if len(reader.pages) > MAX_PAGES:
                raise ValueError('PDF vượt quá 100 trang.')
            pages = [page.extract_text() or '' for page in reader.pages]
            if any(not page.strip() for page in pages):
                raise ValueError('PDF có trang không trích xuất được chữ; PDF scan cần chuyển thành văn bản trước.')
            text = '\n\n'.join(pages)
        except ValueError:
            raise
        except Exception:
            raise ValueError('PDF không hợp lệ hoặc không đọc được.') from None
    else:
        raise ValueError('Chỉ nhận tệp Markdown hoặc PDF.')
    if not text.strip():
        raise ValueError('Không trích xuất được chữ; PDF scan cần được chuyển thành văn bản trước.')
    parts = [part.strip() for part in re.split(r'\n\s*\n', text) if part.strip()]
    pieces = [part[i:i + 4000] for part in parts for i in range(0, len(part), 4000)]
    if len(pieces) > MAX_CHUNKS:
        raise ValueError('Tài liệu có quá nhiều đoạn; hãy chia thành các tệp nhỏ hơn.')
    digest = hashlib.sha256(data).hexdigest()
    return [{'id': f'{digest}:{i}', 'text': part} for i, part in enumerate(pieces, 1)]
