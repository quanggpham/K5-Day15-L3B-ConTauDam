import csv
import duckdb
import pytest
from codebase.backend.analytics.ingest import ingest, REQUIRED_COLUMNS


def make_files(path):
    path.mkdir()
    for name, columns in REQUIRED_COLUMNS.items():
        with (path / f"{name}.csv").open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerow(["1"] * len(columns))


def test_ingest_and_failure_preserve_existing_database(tmp_path):
    source = tmp_path / "source"
    database = tmp_path / "data.duckdb"
    make_files(source)
    ingest(source, database)
    ingest(source, database)
    with duckdb.connect(str(database), read_only=True) as conn:
        assert conn.execute("select count(*) from answers").fetchone()[0] == 1
    (source / "answers.csv").write_text("bad\nvalue\n", encoding="utf-8")
    with pytest.raises(ValueError, match="answers.csv"):
        ingest(source, database)
    with duckdb.connect(str(database), read_only=True) as conn:
        assert conn.execute("select count(*) from answers").fetchone()[0] == 1
    (source / "chat.csv").unlink()
    with pytest.raises(FileNotFoundError):
        ingest(source, database)


def test_bad_csv_preserves_database(tmp_path):
    source = tmp_path / "source"
    database = tmp_path / "data.duckdb"
    make_files(source)
    ingest(source, database)
    with (source / "answers.csv").open("a", encoding="utf-8") as f:
        f.write('"unterminated\n')
    with pytest.raises(Exception):
        ingest(source, database)
    with duckdb.connect(str(database), read_only=True) as conn:
        assert conn.execute("select count(*) from answers").fetchone()[0] == 1
