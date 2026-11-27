"""Tạo snapshot tổng hợp local; không chứa mã học viên."""
import json
from pathlib import Path
import duckdb
from codebase.backend.analytics.metrics import export_snapshot

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[3]
    with duckdb.connect(str(root / 'data/learning_pulse.duckdb'), read_only=True) as db:
        snapshot = export_snapshot(db)
    destination = root / 'data/aggregate.json'
    destination.write_text(json.dumps(snapshot, ensure_ascii=False), encoding='utf-8')
    print(f'Created snapshot with {len(snapshot)} lessons at {destination}')
