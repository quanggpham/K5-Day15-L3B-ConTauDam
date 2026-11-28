"""Verify Supabase sessions and fail closed on access checks."""
import os
import httpx
from fastapi import Header, HTTPException


def require_coach(authorization: str = Header(default="")) -> dict:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(401, "Cần đăng nhập")
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    if not url or not key:
        raise HTTPException(503, "Chưa cấu hình xác thực")
    headers = {"apikey": key, "Authorization": f"Bearer {token.strip()}"}
    try:
        with httpx.Client(timeout=10) as client:
            user = client.get(f"{url}/auth/v1/user", headers=headers)
            if user.status_code in (401, 403):
                raise HTTPException(401, "Phiên đăng nhập không hợp lệ")
            user.raise_for_status()
            permission = client.post(f"{url}/rest/v1/rpc/is_allowed_coach", headers=headers, json={})
            permission.raise_for_status()
            if permission.json() is not True:
                raise HTTPException(403, "Tài khoản chưa được cấp quyền")
            data = user.json()
            if not data.get("id"):
                raise HTTPException(401, "Phiên đăng nhập không hợp lệ")
            return {"id": data["id"], "email": data.get("email")}
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, "Không kiểm tra được quyền truy cập") from None
