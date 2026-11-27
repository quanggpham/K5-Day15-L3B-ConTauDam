"""Import the supplied CSV files into a local DuckDB database."""
import os
import csv
from pathlib import Path
import tempfile

import duckdb

ROOT = Path(__file__).resolve().parents[3]
FILES = ("answers", "events", "completed_items", "chat", "column_dictionary")
REQUIRED_COLUMNS = {
    "answers": ("id", "hv", "lesson_id", "kc_code", "lan_thu", "was_correct"),
    "events": ("hv", "type", "lesson_id", "occurred_at"),
    "completed_items": ("hv", "lesson_id", "item_code", "completed_at"),
    "chat": ("id", "hv", "lesson_id", "transcript", "created_at"),
    "column_dictionary": ("file", "cot", "nghia", "gia_tri"),
}


def ingest(source: Path, destination: Path) -> None:
    paths = {name: source / f"{name}.csv" for name in FILES}
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    for name, path in paths.items():
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.reader(file, strict=True)
            header = next(reader, [])
            for line, row in enumerate(reader, start=2):
                valid_width = len(row) == len(header) or (name == "column_dictionary" and len(row) == len(header) - 1)
                if row and not valid_width:
                    raise ValueError(f"{path.name}:{line}: sai số cột")
        missing = set(REQUIRED_COLUMNS[name]) - set(header)
        if missing:
            raise ValueError(f"{path.name}: thiếu cột {', '.join(sorted(missing))}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, filename = tempfile.mkstemp(suffix=".duckdb", dir=destination.parent)
    os.close(fd)
    os.unlink(filename)
    try:
        with duckdb.connect(filename) as db:
            for name, path in paths.items():
                db.execute(f'CREATE TABLE "{name}" AS SELECT * FROM read_csv(?, header=true, sample_size=-1)', [str(path)])
                print(f"{name}: {db.execute(f'SELECT count(*) FROM {name}').fetchone()[0]} dòng")
        os.replace(filename, destination)
    finally:
        Path(filename).unlink(missing_ok=True)


if __name__ == "__main__":
    ingest(ROOT / "data/pre_class", ROOT / "data/learning_pulse.duckdb")
