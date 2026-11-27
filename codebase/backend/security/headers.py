"""Header bảo mật cho API và SPA (CSP, nosniff, chống nhúng khung, referrer)."""
import os
from urllib.parse import urlparse


def _origin(url: str) -> str | None:
    parsed = urlparse(url.strip())
    return f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme in ("http", "https") and parsed.netloc else None


def content_security_policy() -> str:
    """Chỉ cho phép script/kết nối từ chính origin và origin Supabase (đăng nhập chạy ở browser).

    `style-src 'unsafe-inline'`: recharts và Radix đặt style nội tuyến; script KHÔNG cho phép inline.
    """
    connect = ["'self'"]
    supabase = _origin(os.getenv("SUPABASE_URL", ""))
    if supabase:
        connect.append(supabase)
        connect.append(supabase.replace("https://", "wss://", 1) if supabase.startswith("https://") else supabase)
    return "; ".join([
        "default-src 'self'", "script-src 'self'", "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:", "font-src 'self' data:", f"connect-src {' '.join(connect)}",
        "object-src 'none'", "base-uri 'self'", "form-action 'self'", "frame-ancestors 'none'"])


def security_headers() -> dict[str, str]:
    return {
        "Content-Security-Policy": content_security_policy(),
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
    }
