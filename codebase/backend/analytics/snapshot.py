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
