"""Read a privacy-filtered snapshot generated offline."""
import json
import os
from pathlib import Path
from fastapi import HTTPException


def read_snapshot() -> dict:
    path = Path(os.getenv('AGGREGATE_SNAPSHOT_PATH', 'data/aggregate.json'))
    try:
        with path.open(encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError('Invalid snapshot')
        return data
    except (OSError, ValueError):
        raise HTTPException(503, 'Chưa có dữ liệu tổng hợp hợp lệ') from None


def read_snapshot_v2() -> dict | None:
    """Đọc snapshot v2 (catalog + lessons). Trả None nếu chưa có file; 503 nếu file hỏng/sai phiên bản."""
    path = Path(os.getenv('AGGREGATE_SNAPSHOT_V2_PATH', 'data/aggregate.v2.json'))
    try:
        with path.open(encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        raise HTTPException(503, 'Chưa có dữ liệu tổng hợp hợp lệ') from None
    if (not isinstance(data, dict) or data.get('version') != 2
            or not isinstance(data.get('catalog'), list) or not isinstance(data.get('lessons'), dict)):
        raise HTTPException(503, 'Chưa có dữ liệu tổng hợp hợp lệ')
    return data
