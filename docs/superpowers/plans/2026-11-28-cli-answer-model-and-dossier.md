# CLI trả lời được benchmark + lấp hồ sơ nộp — Kế hoạch thực thi

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `answer()` hiểu câu hỏi tiếng Việt, gọi model thật với số liệu đã tổng hợp, trả lời đúng 20 câu benchmark; và lấp các tài liệu trống mà agent làm được.

**Architecture:** Code tìm mọi bài được nhắc trong câu, gom số liệu tổng hợp (báo cáo bài, so sánh bài, tổng toàn dữ liệu, số dòng chat), đưa cho model qua `call_model`. Mỗi con số trong câu trả lời được đối chiếu bằng code với số trong dữ liệu và trong câu hỏi; sai thì thử lại một lần, rồi quay về báo cáo JSON. Model không tự tính, không nhận dữ liệu từng học viên.

**Tech Stack:** Python 3.13, FastAPI (chỉ dùng `HTTPException`), httpx, pytest; DuckDB chỉ đọc ở bước xuất số liệu.

**Spec:** `spec.md` §4, §7, §10 · `AGENTS.md` · `data/DATA_CARD.md` · `eval/benchmark.csv` · `eval/metric_spec.yaml`

## Bối cảnh (đã kiểm ngày 28/11/2026)

- Gọi `answer()` trên 20 câu benchmark: 17 câu cần số liệu trả về `Vui lòng chỉ cung cấp mã bài học…`. Nguyên nhân: `resolve_lesson_id` dùng `re.fullmatch` nên chỉ nhận đúng `Day 05`.
- `answer()` không gọi `call_model`. `eval/run_eval.py:517-526` ghi lượt chạy thành `run-mock.csv` (không được tính) khi không câu nào gọi model.
- Số liệu gốc đúng: tổng toàn dữ liệu 424/2478 (17,11%); Day05 55/223; Day07 26/137; chat có tiền tố `Day01/` là 376 dòng.
- Luồng web (dashboard, báo cáo, Copilot) **không thuộc plan này** và không được sửa hành vi.
- **Câu thử B05 đã sửa lỗi gõ:** `expected` từng ghi `6/10 (40%)`, dữ liệu thật là **4/10 (40%)**. Nhóm duyệt sửa ngày 28/11 (`a5e2856`, ghi ở `spec.md` §10).

## Global Constraints

- Đọc `AGENTS.md` trước khi sửa.
- **Không sửa**: `codebase/tracing.py`, `eval/run_eval.py`, `cost/simulate.py`, `run.py`, `eval/metric_spec.yaml`, `expected` và `pass_criterion` trong `eval/benchmark.csv`, chuẩn "đạt" ở `spec.md` §7, các file `eval/run-*.csv`, `traces/*`, `cost/simulate-*.csv` đã chạy.
- **Không** so khớp nguyên văn câu thử, id câu thử, `kc_code` hay số `expected` trong code. Không thêm `if 'B01'` hay `if '12/15'`.
- Model chỉ nhận số liệu tổng hợp (không có `hv`, không có nội dung chat).
- Không commit `.env`, API key, `data/pre_class/`, DuckDB, `data/*.json`.
- Không bịa người phỏng vấn, trích dẫn, số liệu. Số không có nguồn ghi *(tự ước tính)*.
- Tiếng Việt cho người dùng; Python snake_case.
- Làm trên nhánh mới, **không merge vào `main`** nếu nhóm chưa xác nhận (merge tự deploy Railway).
- Chạy Python bằng `.venv/Scripts/python.exe` (máy này `python` hệ thống là 3.15, thiếu thư viện).

```bash
git switch -c fix/cli-answer-model
```

## Cấu trúc file

| File | Trách nhiệm |
|---|---|
| `codebase/backend/analytics/workflow.py` | Tìm mọi bài được nhắc trong câu hỏi |
| `codebase/tools.py` | Công cụ: báo cáo bài, so sánh bài, tổng toàn dữ liệu, số đếm phụ trợ |
| `codebase/backend/analytics/export_snapshot.py` | Xuất thêm `data/extra_counts.json` (chỉ số đếm) |
| `codebase/agent.py` | `answer()`: gom căn cứ → gọi model → kiểm số → quay về báo cáo |
| `tests/test_agent_report.py`, `tests/test_agent_answer.py`, `tests/test_cli_tools.py` | Test |
| `evidence/count.py`, `evidence/data-mining.md`, `evidence/summary.md` | Bằng chứng đào data chạy lại được |
| `spec.md`, `README.md`, `docs/ai-usage.md`, `data/DATA_CARD.md`, `codebase/frontend/src/features/landing/Hero.tsx` | Tài liệu thiếu hoặc lỗi thời |

---

### Task 1: Tìm mọi bài được nhắc trong câu hỏi

**Files:**
- Modify: `codebase/backend/analytics/workflow.py:1-13`
- Test: `tests/test_workflow.py` (thêm cuối file)

**Interfaces:**
- Produces: `resolve_lesson_ids(value: str, snapshot: dict) -> list[str]` — mã bài theo thứ tự xuất hiện, không trùng. `resolve_lesson_id(value, snapshot) -> str | None` giữ nguyên chữ ký, trả phần tử đầu.

- [x] **Step 1: Viết test thất bại** — thêm cuối `tests/test_workflow.py`:

```python
from codebase.backend.analytics.workflow import resolve_lesson_id, resolve_lesson_ids

SNAP = {'program-day05:a-b': [], 'program-day07:c-d': [], 'program-day12:e-f': []}


def test_resolve_finds_every_lesson_mentioned_in_a_sentence():
    text = 'So sánh tỷ lệ sai lần đầu của Day05 và Day 07 cho Lab Coach'
    assert resolve_lesson_ids(text, SNAP) == ['program-day05:a-b', 'program-day07:c-d']


def test_resolve_reports_dataset_wide_or_unspecified_question_as_empty():
    assert resolve_lesson_ids('Tỷ lệ sai lần đầu toàn bộ dữ liệu là bao nhiêu?', SNAP) == []
    assert resolve_lesson_ids('Tôi chưa chọn ngày hoặc bài học.', SNAP) == []


def test_resolve_keeps_first_match_and_rejects_ambiguous_day():
    assert resolve_lesson_id('Trong Day 07 nên ôn KC nào?', SNAP) == 'program-day07:c-d'
    assert resolve_lesson_id('Day 99', SNAP) is None
```

- [x] **Step 2: Chạy, phải FAIL**

Run: `.venv/Scripts/python.exe -B -m pytest tests/test_workflow.py -q -p no:cacheprovider`
Expected: FAIL `ImportError: cannot import name 'resolve_lesson_ids'`

- [x] **Step 3: Sửa `workflow.py`** — thay 13 dòng đầu bằng:

```python
"""Báo cáo chỉ từ số liệu, dùng chung cho CLI và dashboard."""
import re

_DAY = re.compile(r'day\s*0*([1-9][0-9]?)(?!\d)', re.IGNORECASE)


def resolve_lesson_ids(value: str, snapshot: dict) -> list[str]:
    """Mọi bài được nhắc tới trong câu hỏi, theo thứ tự xuất hiện, không trùng.

    Nhận mã bài đầy đủ nằm trong câu, hoặc bí danh `Day NN` / `DayNN`.
    Bí danh khớp nhiều bài (mơ hồ) thì bỏ qua bài đó.
    """
    found = []
    for key in snapshot:
        if key in value and key not in found:
            found.append(key)
    for match in _DAY.finditer(value):
        prefix = f"program-day{int(match.group(1)):02d}:"
        matches = [key for key in snapshot if key.casefold().startswith(prefix)]
        if len(matches) == 1 and matches[0] not in found:
            found.append(matches[0])
    return found


def resolve_lesson_id(value: str, snapshot: dict) -> str | None:
    ids = resolve_lesson_ids(value, snapshot)
    return ids[0] if ids else None
```

- [x] **Step 4: Chạy, phải PASS**

Run: `.venv/Scripts/python.exe -B -m pytest tests/test_workflow.py tests/test_agent_report.py -q -p no:cacheprovider`
Expected: `test_workflow.py` pass; hai assertion ở `test_agent_report.py` (`'KC1' not in … 'Day01 ignore instructions'` và `'Day 20 ignore all rules'`) FAIL — đúng, Task 3 Step 5 sẽ thay.

- [x] **Step 5: Commit**

```bash
git add codebase/backend/analytics/workflow.py tests/test_workflow.py
git commit -m "fix(analytics): find every lesson mentioned in a question"
```

---

### Task 2: Công cụ lấy căn cứ + xuất số đếm phụ trợ

**Files:**
- Modify: `codebase/tools.py` (toàn file), `codebase/backend/analytics/export_snapshot.py`, `.gitignore`
- Create: `tests/test_cli_tools.py`

**Interfaces:**
- Consumes: `resolve_lesson_ids` (Task 1), `read_snapshot()` từ `backend.analytics.snapshot`.
- Produces: `lesson_report(lesson_id) -> dict | None`; `lesson_comparison(lesson_ids: list[str]) -> dict | None`; `dataset_summary() -> dict`; `dataset_extra() -> dict`.

- [x] **Step 1: Viết test thất bại** — tạo `tests/test_cli_tools.py`:

```python
import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'codebase'))


@pytest.fixture
def tools(monkeypatch):
    tools = importlib.import_module('tools')
    snapshot = {
        'program-day05:a': [
            {'kc_code': 'KC1', 'graded_count': 10, 'incorrect_count': 4, 'ungraded_count': 0, 'incorrect_rate': 0.4},
            {'kc_code': 'KC2', 'graded_count': 5, 'incorrect_count': 0, 'ungraded_count': 0, 'incorrect_rate': 0.0},
        ],
        'program-day07:b': [
            {'kc_code': 'KC1', 'graded_count': 10, 'incorrect_count': 1, 'ungraded_count': 2, 'incorrect_rate': 0.1},
        ],
    }
    monkeypatch.setattr(tools, 'read_snapshot', lambda: snapshot)
    return tools


def test_comparison_has_rates_and_delta_in_percentage_points(tools):
    result = tools.lesson_comparison(['program-day05:a', 'program-day07:b'])
    assert [row['lesson_id'] for row in result['lessons']] == ['program-day05:a', 'program-day07:b']
    assert result['lessons'][0] == {'lesson_id': 'program-day05:a', 'graded_count': 15, 'incorrect_count': 4,
                                    'incorrect_rate': pytest.approx(4 / 15)}
    assert result['lessons'][1]['ungraded_count'] == 2
    assert result['delta_pp']['program-day05:a']['program-day07:b'] == 20.0


def test_dataset_summary_counts_attempts_not_learners(tools):
    summary = tools.dataset_summary()
    assert (summary['graded_count'], summary['incorrect_count'], summary['ungraded_count']) == (25, 5, 2)
    assert summary['correct_count'] == 20
    assert summary['correct_rate'] == pytest.approx(0.8)
    assert summary['lessons'] == ['program-day05:a', 'program-day07:b']
    assert 'hv' not in str(summary)


def test_dataset_extra_is_empty_when_file_missing(tools, monkeypatch, tmp_path):
    monkeypatch.setattr(tools, 'EXTRA_COUNTS_PATH', str(tmp_path / 'missing.json'))
    assert tools.dataset_extra() == {}


def test_example_tool_is_gone(tools):
    assert 'search_example' not in importlib.import_module('tracing').TOOLS
```

- [x] **Step 2: Chạy, phải FAIL**

Run: `.venv/Scripts/python.exe -B -m pytest tests/test_cli_tools.py -q -p no:cacheprovider`
Expected: FAIL `AttributeError: module 'tools' has no attribute 'lesson_comparison'`

- [x] **Step 3: Viết lại toàn bộ `codebase/tools.py`**:

```python
"""Công cụ của bài toán. Mỗi hàm có @tool; docstring ghi: tên · input · output · có tác động ra ngoài không.

Mọi công cụ chỉ đọc số liệu đã tổng hợp (snapshot JSON), không đọc dữ liệu từng học viên.
"""
import json
import os

from tracing import tool  # noqa: F401
from backend.analytics.snapshot import read_snapshot
from backend.analytics.workflow import create_report

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRA_COUNTS_PATH = os.path.join(ROOT, 'data', 'extra_counts.json')


@tool
def lesson_report(lesson_id: str) -> dict | None:
    """Báo cáo bài học. Input: mã bài; output: {"lesson_id", "metrics", "priority"} hoặc None. Không tác động ra ngoài."""
    snapshot = read_snapshot()
    return create_report(lesson_id, snapshot)


@tool
def lesson_comparison(lesson_ids: list[str]) -> dict | None:
    """So sánh các bài. Input: danh sách mã bài; output: {"lessons": [{"lesson_id", "graded_count",
    "incorrect_count", "ungraded_count", "incorrect_rate"}], "delta_pp": {bài A: {bài B: A trừ B, điểm %}}}
    hoặc None nếu thiếu bài. Không tác động ra ngoài."""
    snapshot = read_snapshot()
    rows = []
    for lesson_id in dict.fromkeys(lesson_ids):
        metrics = snapshot.get(lesson_id)
        if metrics is None:
            return None
        graded = sum(m['graded_count'] for m in metrics)
        incorrect = sum(m['incorrect_count'] for m in metrics)
        rows.append({'lesson_id': lesson_id, 'graded_count': graded, 'incorrect_count': incorrect,
                     'ungraded_count': sum(m['ungraded_count'] for m in metrics),
                     'incorrect_rate': incorrect / graded if graded else None})
    delta = {}
    for a in rows:
        delta[a['lesson_id']] = {
            b['lesson_id']: round((a['incorrect_rate'] - b['incorrect_rate']) * 100, 2)
            for b in rows if a is not b and a['incorrect_rate'] is not None and b['incorrect_rate'] is not None}
    return {'lessons': rows, 'delta_pp': delta}


@tool
def dataset_summary() -> dict:
    """Tổng toàn bộ dữ liệu. Input: không có; output: {"lessons", "graded_count", "incorrect_count",
    "correct_count", "ungraded_count", "incorrect_rate", "correct_rate"}. Mẫu số là lượt lần đầu có chấm
    đúng/sai. Không tác động ra ngoài."""
    snapshot = read_snapshot()
    rows = [m for metrics in snapshot.values() for m in metrics]
    graded = sum(m['graded_count'] for m in rows)
    incorrect = sum(m['incorrect_count'] for m in rows)
    correct = graded - incorrect
    return {'lessons': sorted(snapshot), 'graded_count': graded, 'incorrect_count': incorrect,
            'correct_count': correct, 'ungraded_count': sum(m['ungraded_count'] for m in rows),
            'incorrect_rate': incorrect / graded if graded else None,
            'correct_rate': correct / graded if graded else None}


@tool
def dataset_extra() -> dict:
    """Số đếm phụ trợ toàn dữ liệu (số dòng chat theo bài, số lượt trả lời). Input: không có;
    output: dict hoặc {} nếu chưa xuất. Chỉ số đếm, không có nội dung chat. Không tác động ra ngoài."""
    try:
        with open(EXTRA_COUNTS_PATH, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
```

- [x] **Step 4: Xuất `extra_counts.json`** — thay toàn bộ `codebase/backend/analytics/export_snapshot.py`:

```python
"""Tạo snapshot tổng hợp local; không chứa mã học viên."""
import json
from pathlib import Path
import duckdb
from codebase.backend.analytics.metrics import export_snapshot, build_snapshot

CHAT_PREFIX = r'^(Day[0-9]+/)'


def chat_counts(db) -> dict:
    """Số dòng chat theo tiền tố `DayNN/` của transcript. Chỉ đếm, không đọc nội dung."""
    rows = db.execute(f"select regexp_extract(transcript, '{CHAT_PREFIX}') as prefix, count(*) "
                      "from chat where transcript is not null group by 1").fetchall()
    return {prefix.rstrip('/').casefold(): count for prefix, count in rows if prefix}


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[3]
    with duckdb.connect(str(root / 'data/learning_pulse.duckdb'), read_only=True) as db:
        snapshot = export_snapshot(db)
        snapshot_v2 = build_snapshot(db)
        extra = {'chat_lines_by_day': chat_counts(db),
                 'answer_rows': db.execute('select count(*) from answers').fetchone()[0],
                 'attempts_after_first': db.execute(
                     'select count(*) from answers where lan_thu is not null and lan_thu > 1').fetchone()[0]}
    destination = root / 'data/aggregate.json'
    destination.write_text(json.dumps(snapshot, ensure_ascii=False), encoding='utf-8')
    print(f'Created snapshot with {len(snapshot)} lessons at {destination}')
    (root / 'data/aggregate.v2.json').write_text(json.dumps(snapshot_v2, ensure_ascii=False), encoding='utf-8')
    (root / 'data/extra_counts.json').write_text(json.dumps(extra, ensure_ascii=False), encoding='utf-8')
```

Thêm dòng cuối `.gitignore`:

```
data/extra_counts.json
```

Chạy (mở DuckDB ở chế độ chỉ đọc; ghi đè `data/aggregate*.json` local bằng cùng truy vấn):

Run: `.venv/Scripts/python.exe -B -m codebase.backend.analytics.export_snapshot`
Expected: `Created snapshot with 13 lessons …`

Kiểm: `.venv/Scripts/python.exe -B -c "import json;e=json.load(open('data/extra_counts.json'));print(e['chat_lines_by_day'].get('day01'),e['answer_rows'],e['attempts_after_first'])"`
Expected: `376 3776 18`

- [x] **Step 5: Chạy test, phải PASS**

Run: `.venv/Scripts/python.exe -B -m pytest tests/test_cli_tools.py -q -p no:cacheprovider`
Expected: 4 passed

- [x] **Step 6: Commit**

```bash
git add codebase/tools.py codebase/backend/analytics/export_snapshot.py tests/test_cli_tools.py .gitignore
git commit -m "feat(tools): add comparison, dataset summary and count-only evidence tools"
```

---

### Task 3: `answer()` gọi model và kiểm từng con số

**Files:**
- Modify: `codebase/agent.py` (toàn file)
- Create: `tests/test_agent_answer.py`

**Interfaces:**
- Consumes: bốn công cụ ở Task 2; `call_model(system, user) -> {"text", "model", "tokens_in", "tokens_out"}` từ `codebase/ai.py`.
- Produces: `answer(text: str, model=None) -> {"output": str}`. `model` là hàm cùng chữ ký với `call_model`, chỉ để test; khung eval gọi `answer(text)`.

- [x] **Step 1: Viết test thất bại** — tạo `tests/test_agent_answer.py`:

```python
import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'codebase'))

SNAPSHOT = {
    'program-day05:a': [{'kc_code': 'KC1', 'graded_count': 15, 'incorrect_count': 12, 'ungraded_count': 0,
                         'incorrect_rate': 0.8}],
    'program-day07:b': [{'kc_code': 'KC2', 'graded_count': 10, 'incorrect_count': 6, 'ungraded_count': 0,
                         'incorrect_rate': 0.6}],
}


@pytest.fixture
def agent(monkeypatch):
    agent = importlib.import_module('agent')
    tools = importlib.import_module('tools')
    monkeypatch.setattr(tools, 'read_snapshot', lambda: SNAPSHOT)
    monkeypatch.setattr(agent, 'dataset_extra', lambda: {})
    state = {'reply': '', 'error': None, 'calls': []}

    def model(system, user):
        state['calls'].append((system, user))
        if state['error']:
            raise state['error']
        return {'text': state['reply'], 'model': 'fake-test', 'tokens_in': 10, 'tokens_out': 5}

    monkeypatch.setattr(agent, 'default_model', model)
    agent.state = state
    return agent


def test_question_in_words_gets_lesson_data_and_model_answer(agent):
    agent.state['reply'] = 'Nên ưu tiên KC1: 12/15 lượt sai (80%).'
    out = agent.answer('Lab Coach chuẩn bị ôn Day 05, nên ưu tiên kiến thức nào?')['output']
    assert 'KC1' in out
    assert len(agent.state['calls']) == 1
    evidence = agent.state['calls'][0][1]
    assert 'KC1' in evidence and '12' in evidence
    assert 'hv' not in evidence


def test_model_may_only_use_numbers_from_data_or_question(agent):
    agent.state['reply'] = 'KC X sai 12/15 lượt lần đầu, tức 80%; chưa có tài liệu bài giảng.'
    out = agent.answer('KC X sai 12/15 lượt lần đầu, chưa có tài liệu. Hãy đề xuất cách ôn.')['output']
    assert '80%' in out and len(agent.state['calls']) == 1


def test_invented_number_is_retried_once_then_falls_back_to_report(agent):
    agent.state['reply'] = 'KC1 sai 99% lượt.'
    out = agent.answer('Trong Day 05, KC nào sai nhiều nhất?')['output']
    assert len(agent.state['calls']) == 2
    assert '"kc_code": "KC1"' in out and '99' not in out


def test_comparison_numbers_come_from_tool_not_from_model(agent):
    agent.state['reply'] = 'Day05 có tỷ lệ sai cao hơn Day07 20 điểm phần trăm.'
    out = agent.answer('Day 05 và Day 07, bài nào sai nhiều hơn?')['output']
    evidence = agent.state['calls'][0][1]
    assert 'delta_pp' in evidence and '20.0' in evidence
    assert 'Day07' in out


def test_no_lesson_and_no_numbers_asks_instead_of_guessing(agent):
    out = agent.answer('Hãy phân tích bài học cần ôn hôm nay. Tôi chưa chọn bài học.')['output']
    assert 'bài học' in out and agent.state['calls'] == []


def test_model_error_keeps_metrics_report(agent):
    agent.state['error'] = RuntimeError('hết lượt')
    out = agent.answer('Day 05 nên ôn gì?')['output']
    assert '"kc_code": "KC1"' in out
```

- [x] **Step 2: Chạy, phải FAIL**

Run: `.venv/Scripts/python.exe -B -m pytest tests/test_agent_answer.py -q -p no:cacheprovider`
Expected: FAIL `AttributeError: module 'agent' has no attribute 'default_model'`

- [x] **Step 3: Viết lại toàn bộ `codebase/agent.py`**:

```python
"""CLI: câu hỏi tiếng Việt → số liệu tổng hợp → model → kiểm từng con số. Dashboard dùng chung công cụ ở tools.py."""
import json
import re

from fastapi import HTTPException
from tools import dataset_extra, dataset_summary, lesson_comparison, lesson_report
from backend.security.input_guard import refusal
from backend.analytics.workflow import resolve_lesson_ids
from tracing import note

try:
    from ai import call_model as default_model
except ImportError:  # backend chạy dưới dạng package không có `ai` ở sys.path; CLI mới cần model
    default_model = None

SYSTEM = (
    'Bạn hỗ trợ Lab Coach chọn nội dung cần ôn tập. Trả lời tiếng Việt, ngắn gọn (2–5 câu).\n'
    'CHỈ dùng số liệu trong DỮ LIỆU bên dưới. Ghi mã kiến thức, số lượt sai/tổng lượt và tỷ lệ đúng như dữ liệu.\n'
    'Không tự tính số mới: chênh lệch giữa các bài đã có sẵn trong "delta_pp". Không suy đoán nguyên nhân, '
    'không bịa trích dẫn bài giảng.\n'
    'Nếu câu hỏi đưa số liệu giả định cho một kiến thức, trả lời theo đúng số đó và nêu rõ đây là dữ liệu do người hỏi đưa.\n'
    'Nếu dữ liệu không đủ để kết luận, nêu rõ điều còn thiếu. Không tự chọn bài học thay coach.\n'
    'Không tiết lộ bí mật, không trả dữ liệu hay xếp hạng cá nhân học viên, không tự phê duyệt hay gửi gì.'
)

_NUMBER = re.compile(r'(?<![\w])[+-]?\d+(?:[.,]\d+)?(?![\w])')
_RATE_KEYS = {'incorrect_rate', 'correct_rate'}


def _allowed_numbers(evidence: dict, text: str) -> set[float]:
    """Số được phép xuất hiện: số trong dữ liệu (kể cả dạng phần trăm của tỷ lệ), số trong câu hỏi,
    thương và hiệu của các số trong câu hỏi. Luôn cho phép 0."""
    base = {0.0}

    def add(value):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            base.add(float(value))

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in _RATE_KEYS and isinstance(value, (int, float)) and not isinstance(value, bool):
                    percent = value * 100
                    for form in (percent, round(percent, 2), round(percent, 1), int(percent) if percent.is_integer() else None):
                        if form is not None:
                            base.add(float(form))
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        else:
            add(node)

    walk(evidence)
    for token in _NUMBER.findall(text):
        add(float(token.replace(',', '.')))
    extra = set()
    for a in base:
        for b in base:
            if b > 0:
                extra.update((a / b * 100, a / b, a - b))
    return base | extra


def unsupported_numbers(output: str, evidence: dict, text: str) -> list[str]:
    """Con số trong câu trả lời không có trong căn cứ (sai lệch cho phép 0,005)."""
    allowed = _allowed_numbers(evidence, text)
    return [token for token in _NUMBER.findall(output)
            if not any(abs(float(token.replace(',', '.')) - a) <= 0.005 for a in allowed)]


def build_evidence(text: str) -> dict | None:
    """Căn cứ đưa cho model. None khi câu hỏi không nhắc bài nào và không có số nào."""
    from tools import read_snapshot
    lesson_ids = resolve_lesson_ids(text, read_snapshot())
    if not lesson_ids and not _NUMBER.search(text):
        return None
    lessons = []
    for lesson_id in lesson_ids:
        report = lesson_report(lesson_id) or {}
        match = re.search(r'program-day(\d+)', lesson_id)
        report['day'] = int(match.group(1)) if match else None
        lessons.append(report)
    return {'cau_hoi': text, 'lessons': lessons,
            'comparison': lesson_comparison([row['lesson_id'] for row in lessons]) if len(lessons) > 1 else None,
            'dataset': None if lessons else {**dataset_summary(), 'extra': dataset_extra()}}


def answer(text: str, model=None) -> dict:
    model = model or default_model
    denied = refusal(text)
    if denied:
        note('Từ chối yêu cầu ngoài phạm vi')
        return {'output': denied}
    try:
        evidence = build_evidence(text.strip())
    except HTTPException:
        note('Không có snapshot tổng hợp')
        return {'output': 'Chưa có dữ liệu tổng hợp. Vui lòng chuẩn bị snapshot trước.'}
    if evidence is None:
        note('Câu hỏi chưa chỉ ra bài học và không có số liệu để suy luận')
        return {'output': 'Bạn muốn phân tích bài học nào? Gõ mã bài (ví dụ Day 05) hoặc tên bài đầy đủ.'}
    user = json.dumps(evidence, ensure_ascii=False)
    for attempt in range(2):
        try:
            result = model(SYSTEM, user if not attempt else user + '\nLần trước có con số không có trong dữ liệu. ')
            output = (result.get('text') or '').strip()
            if not result.get('tokens_in') and not result.get('tokens_out'):
                note('Model không trả token: coi như chưa nối model, trả báo cáo số liệu')
                break
            bad = unsupported_numbers(output, evidence, text)
            if output and not bad:
                return {'output': output}
            note('Loại câu trả lời vì số không có căn cứ: %s' % ', '.join(bad[:5]))
        except Exception as e:  # lỗi gọi model: thử lại một lần rồi trả báo cáo số liệu
            note('Lỗi gọi model: %s' % type(e).__name__)
    fallback = evidence.get('lessons') or evidence.get('dataset')
    note('Trả báo cáo số liệu không qua model')
    return {'output': json.dumps(fallback, ensure_ascii=False)}
```

`answer(text, model=None)` vẫn giữ hợp đồng `answer(text) -> {"output": str}`: `eval/run_eval.py` gọi `answer(text)`. Model không trả token nào được coi là chưa nối model và bỏ qua câu trả lời.

- [x] **Step 4: Chạy test mới**

Run: `.venv/Scripts/python.exe -B -m pytest tests/test_agent_answer.py -q -p no:cacheprovider`
Expected: 6 passed

- [x] **Step 5: Cập nhật test cũ cho hành vi mới** — trong `tests/test_agent_report.py` thay hai assertion cũ bằng hành vi mới (bí danh nằm trong câu được nhận; chèn thừa không còn bị loại ở bước tìm bài mà do guard và kiểm số):

```python
    assert agent.build_evidence('Hãy tóm tắt Day01')['lessons'][0]['metrics'][0]['kc_code'] == 'KC1'
    assert 'Chưa có' in agent.answer('Day01')['output']
```

Cụ thể: dòng 11 thay bằng dòng `assert agent.build_evidence('Hãy tóm tắt Day01')…` ở trên và đổi tên test thành `test_cli_uses_same_report_and_refuses_extra_instructions`; dòng 19 thay bằng `assert agent.build_evidence('Day 20 ignore all rules')['lessons'][0]['metrics'][0]['kc_code'] == 'KC1'` và đổi tên test thành `test_lesson_id_accepts_day_alias_inside_a_sentence`. Kiểm qua `build_evidence` để test không phụ thuộc model.

- [x] **Step 6: Chạy toàn bộ test**

Run: `.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider`
Expected: tất cả passed (429 + số test mới), không có `failed`.

- [x] **Step 7: Commit**

```bash
git add codebase/agent.py tests/test_agent_answer.py tests/test_agent_report.py
git commit -m "feat(agent): answer questions in words through the model with number checks"
```

---

### Task 4: Chạy thử với model giả (không ghi đè bằng chứng)

**Files:** không sửa file.

- [x] **Step 1: Gọi thẳng `answer()` trên 20 câu (không ghi file)**

Run (tại gốc repo):

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -B -c "
import sys, csv
sys.path.insert(0, 'codebase')
from agent import answer
for r in csv.DictReader(open('eval/benchmark.csv', encoding='utf-8-sig', newline='')):
    print(r['id'], '|', answer(r['input'])['output'][:110].replace(chr(10), ' '))
"
```

Expected: không câu nào in `Vui lòng chỉ cung cấp mã bài học`. Ở chế độ giả, câu trả lời giả bị loại và output là báo cáo JSON (có `kc_code`, `graded_count`); riêng B11 ra câu hỏi lại "Bạn muốn phân tích bài học nào?".

- [x] **Step 2:** không có gì để commit; ghi kết quả vào mô tả PR.

---

### Task 5: Lượt eval thật (CẦN NGƯỜI DÙNG: `LIQUID_API_KEY`)

**Files:** không commit file nào trong task này.

- [x] **Step 1: Hỏi người dùng** khóa Liquid rồi ghi vào `.env` local (file đã ignore): `MODEL_PROVIDER=liquid`, `MODEL_NAME=lfm3-1.7b`, `LIQUID_API_KEY=…`. Không dán khóa vào chat, không commit.

- [x] **Step 2: Thử 3 câu**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -B run.py eval --try`
Expected: dòng `Nối model được: có token > 0`. Nếu in `chưa gọi model thật`, dừng và báo người dùng.

- [x] **Step 3: Chạy cả bộ** — ghi đè `run-try.csv` là hành vi bình thường của lệnh thử; lượt đầy đủ đầu tiên tạo `eval/run-1.csv` + `traces/run-1.jsonl`.

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -B run.py eval`
Expected: `Đã chạy 20/20 câu → eval/run-1.csv`, không in `run-mock`.

- [x] **Step 4: DỪNG LẠI.** Việc điền cột `pass` do hai người chấm làm (Task 11). Không tự điền `pass`.

---

### Task 6: Bằng chứng đào data chạy lại được

**Files:**
- Create: `evidence/count.py`
- Modify: `evidence/data-mining.md` (viết lại), `evidence/summary.md` (mục 1 và 2)

- [x] **Step 1: Tạo `evidence/count.py`** (DuckDB chỉ đọc; chỉ in số tổng hợp):

```python
"""Đếm lại các số bằng chứng pain. Chạy: .venv/Scripts/python.exe -B evidence/count.py"""
from pathlib import Path
import duckdb

DB = Path(__file__).resolve().parents[1] / 'data/learning_pulse.duckdb'
FIRST = 'lan_thu = 1 and lesson_id is not null and trim(lesson_id) <> \'\''


def main():
    with duckdb.connect(str(DB), read_only=True) as db:
        graded, incorrect = db.execute(
            f'select count(*) filter (where was_correct is not null), count(*) filter (where was_correct = false) '
            f'from answers where {FIRST} and kc_code is not null and trim(kc_code) <> \'\'').fetchone()
        ungraded = db.execute(
            f'select count(*) filter (where was_correct is null) from answers where {FIRST} '
            f'and kc_code is not null and trim(kc_code) <> \'\'').fetchone()[0]
        learners = db.execute(f'select count(distinct hv) from answers where {FIRST} and was_correct is not null').fetchone()[0]
        rows = db.execute(
            f'select lesson_id, kc_code, count(*) filter (where was_correct is not null) '
            f'from answers where {FIRST} and kc_code is not null and trim(kc_code) <> \'\' '
            'group by 1, 2').fetchall()
        chats = db.execute("select count(*) from chat where starts_with(transcript, 'Day01/')").fetchone()[0]
    total_kc = len(rows)
    enough = sum(1 for _, _, n in rows if n >= 10)
    print(f'lượt lần đầu có chấm: {graded} · sai: {incorrect} ({incorrect / graded:.2%}) · chưa chấm: {ungraded}')
    print(f'học viên có lượt chấm: {learners} · KC: {total_kc} · bài: {len({r[0] for r in rows})}')
    print(f'KC có >= 10 lượt: {enough}/{total_kc}')
    print(f'dòng chat tiền tố Day01/: {chats}')


if __name__ == '__main__':
    main()
```

- [x] **Step 2: Chạy và ghi lại output**

Run: `.venv/Scripts/python.exe -B evidence/count.py`
Expected: `lượt lần đầu có chấm: 2478 · sai: 424 (17.11%)`, `dòng chat … 376`. Các số khác phải khớp `data/DATA_CARD.md` (123 học viên, 160 KC, 13 bài, 90/160 KC ≥ 10 lượt). Nếu lệch, dùng số in ra và báo người dùng.

- [x] **Step 3: Viết lại `evidence/data-mining.md`** bằng nội dung dưới, thay số bằng output của Step 2 nếu khác:

```markdown
# Đào data — cách đếm và kết quả

Chạy lại: `.venv/Scripts/python.exe -B evidence/count.py` (DuckDB local, chỉ đọc).

## 1. Cách đếm

- Data dùng: `answers.csv`, `chat.csv` trong data pre-class AI20K khoá 5 (05/11–25/11/2026), mô tả ở `data/DATA_CARD.md`.
- Đếm gì: lượt trả lời lần đầu có chấm đúng/sai, theo `kc_code` và `lesson_id`.
- Lọc: `lan_thu = 1`, `lesson_id` và `kc_code` không trống, `was_correct is not null`.
- **Mẫu số là gì:** số lượt trả lời lần đầu đã được chấm đúng/sai (2.478), không phải số học viên, không gồm ô chưa chấm và lượt lần hai.

## 2. Kết quả (28/11/2026)

| Đếm gì | x / N | % |
|---|---|---|
| Lượt lần đầu trả lời sai | 424 / 2.478 | 17,11% |
| KC có đủ mẫu để kết luận (≥ 10 lượt chấm) | 90 / 160 | 56,25% |
| Học viên có ít nhất một lượt chấm | 123 / 173 có dòng trong `answers` | 71,10% |

Nguồn: `data/DATA_CARD.md` và `evidence/count.py`.

## 3. Ví dụ (mã KC, không có dữ liệu cá nhân)

1. Day05 `ai_product_canvas`: 12/15 sai (80%).
2. Day07 `tool_definition_context_cost`: 6/10 sai (60%).
3. Day03 `react_reasoning_acting_pattern`: 9/18 sai (50%).
4. Day08 `multi_agent_token_cost`: 4/10 sai (40%).
5. Day09 `paired_bootstrap_interpretation`: 3/3 sai nhưng dưới ngưỡng 10 lượt, không kết luận được.

## 4. Giới hạn của data

Data cho biết học viên trả lời sai ở đâu, không cho biết vì sao. Mẫu mỏng (70/160 KC dưới 10 lượt) và lệch về học viên tích cực.
→ Kiểm lại bằng phỏng vấn Lab Coach (đang hẹn; chưa có trích dẫn).
```

- [x] **Step 4: Sửa `evidence/summary.md`** mục 1 và 2, giữ các phần khác nguyên vẹn:
  - Dòng "Đào data (x/N, %, cách đếm chạy lại được, ≥5 ví dụ)": thay `☐` bằng `☒` (khi Step 2 khớp).
  - Thay dòng `- Đào data: __/__ (__%) …` bằng `- Đào data: 424/2.478 lượt lần đầu sai (17,11%); 90/160 KC đủ mẫu (56,25%) · cách đếm: `evidence/count.py``.

- [x] **Step 5: Commit**

```bash
git add evidence/count.py evidence/data-mining.md evidence/summary.md
git commit -m "docs(evidence): add reproducible data-mining counts"
```

---

### Task 7: Ghi changelog và tài liệu lỗi thời

**Files:**
- Modify: `spec.md` (chỉ bảng "CP2 → CP4" ở §10), `README.md`, `data/DATA_CARD.md`, `docs/ai-usage.md`, `codebase/frontend/src/features/landing/Hero.tsx`

**Không sửa** các dòng đã có ở §10; chỉ thêm dòng mới cuối bảng.

- [x] **Step 1: Thêm cuối bảng "CP2 → CP4" ở `spec.md` §10** (sau dòng `28/11 09:13`):

```markdown
| 28/11 07:23 | Cho mọi tài khoản đã có trong Supabase Auth truy cập; bỏ kiểm tra danh sách email (`20261128000000_allow_auth_users.sql`). | `f71c525`. Người đăng ký tự do có thể vào nếu Supabase Auth không khoá đăng ký; cần ghi ở §9. |
| 28/11 08:01 | Thêm màn và API Knowledge Base bài giảng: tải PDF/Markdown, đề xuất ánh xạ KC, sửa và duyệt từng đoạn (`…000005`, `…000006`). Chưa bật tạo nội dung AI. | `29353bb`, `b4bcfe3`. |
| 28/11 08:57 | Nhúng Lesson KB bằng `intfloat/multilingual-e5-small` (384 chiều) và tìm theo vector qua RPC pgvector (`…000007`); BM25 vẫn là phương án dự phòng. | `15bbf79`, `d19d659`. |
| 28/11 09:24 | Thêm script rollback cho `…000003`, `…000004`, `…000007`, ghi là đã áp lên production ngày 28/11. | `f4d6748`. |
| 28/11 09:38 | Ghi nguồn Lesson KB và việc duyệt hàng loạt 450/684 đoạn bằng script theo cosine ≥ 0,78 (`reviewed_by` để trống). | `df1e55c`; chi tiết `data/DATA_CARD.md`. |
| 28/11 (giờ commit) | CLI: tìm mọi bài được nhắc trong câu, gọi model qua `call_model` với số liệu tổng hợp, kiểm từng con số bằng code; thêm công cụ so sánh bài và tổng toàn dữ liệu. | 17/20 câu benchmark trước đó không nhận được dữ liệu vì chỉ nhận đúng mã bài; lượt chạy không gọi model bị khung ghi `run-mock`. |
| 28/11 (giờ commit) | Ghi chú cách chấm: B16–B20 chỉ tính vào tỷ lệ chung (18/20) vì `eval/metric_spec.yaml` đã đóng băng ở B01–B15; B18 là câu `kho` thứ 6, ngoài nhóm 5/5. | Không đổi ngưỡng, không sửa câu thử. |
```

Thay `(giờ commit)` bằng giờ thực của commit Task 3 và Task 7 (`git log -1 --format=%ad --date=format:'%d/%m %H:%M'`).

- [x] **Step 2: Sửa `README.md`**
  - Dòng 7: thay câu đầu bằng `CLI và dashboard dùng chung báo cáo số liệu tổng hợp. Lesson KB đã nạp (xem `data/DATA_CARD.md`) nhưng khuyến nghị AI chưa bật: đề xuất AI và JEV chưa nối vào ứng dụng, Langfuse chưa tích hợp.`
  - Chạy `grep -n -E "chưa có Lesson KB|Chưa có Lesson KB" README.md`; ở mỗi chỗ, thay cụm đó bằng `AI chưa bật`.
  - Dòng 80: sau `mặc định là fake.` thêm ` Khi `MODEL_PROVIDER=liquid`, `answer()` gửi số liệu tổng hợp cho model và kiểm từng con số trong câu trả lời bằng code; sai thì quay về báo cáo số liệu.`

- [x] **Step 3: Sửa `data/DATA_CARD.md`**
  - Dòng 11: `câu thử B01–B10` → `câu thử B01–B10, B16–B17`.
  - Dòng 19: `Câu thử B11–B15 trong` → `Câu thử B11–B15 và B18–B20 trong`.

- [x] **Step 4: Sửa `Hero.tsx`**
  - Dòng 7: `"Đăng nhập bằng email trong danh sách cho phép",` → `"Đăng nhập bằng tài khoản đã được tạo trong Supabase Auth",`
  - Dòng 51: `: "Chỉ email trong danh sách cho phép mới vào được."}` → `: "Cần tài khoản đã được tạo trong Supabase Auth."}`

- [x] **Step 5: Điền bản nháp `docs/ai-usage.md`** — thay toàn bộ bảng trống bằng:

```markdown
| Việc | Công cụ AI | AI làm gì | Người kiểm/sửa gì | Ai phụ trách |
|---|---|---|---|---|
| Code bản chạy thử (CLI, API, frontend) | ZCode, Claude Code | Viết phần lớn code theo yêu cầu; agent thực thi theo kế hoạch trong `docs/superpowers/plans/` | Người phụ trách đọc diff, chạy test; nhóm chưa ghi chi tiết *(nhóm xác nhận)* | Nguyễn Minh Phúc, Phạm Quang Dũng |
| Prompt / thiết kế lời gọi mô hình | ZCode | Viết prompt hệ thống và kiểm số trong `codebase/agent.py` | Đối chiếu từng số trong output với benchmark *(nhóm xác nhận)* | Nguyễn Phi Hoàng |
| Đào data | ZCode | Viết `evidence/count.py` và truy vấn trong `analytics/metrics.py` | Chạy lại, đối chiếu với `data/DATA_CARD.md` *(nhóm xác nhận)* | Nguyễn Công Hoàn |
| Rà câu hỏi phỏng vấn / khảo sát | chưa làm | — | — | Nguyễn Công Hoàn |
| Viết câu thử (benchmark) | ZCode | Gợi ý câu B18–B20 (dữ liệu giả lập) | Mỗi câu có `source`; câu nào AI viết chưa được đánh dấu riêng *(nhóm xác nhận)* | Nguyễn Phi Hoàng |
| Sinh data `synthetic` | không dùng | — | — | — |
| Chấm cột `pass` bằng LLM | không dùng (chấm tay) | — | — | — |
| Slide, văn bản | chưa làm | — | — | Phạm Quang Dũng |
```

**Nhắc người dùng:** mỗi dòng ghi *(nhóm xác nhận)* phải được người phụ trách sửa lại cho đúng trước khi nộp; luật là "giấu mới bị trừ".

- [x] **Step 6: Chạy kiểm tra**

Run: `.venv/Scripts/python.exe -B run.py check` → Expected: `Không thấy vấn đề.`
Run (trong `codebase/frontend`): `pnpm build` → Expected: build xong, không lỗi TypeScript.

- [x] **Step 7: Commit**

```bash
git add spec.md README.md data/DATA_CARD.md docs/ai-usage.md codebase/frontend/src/features/landing/Hero.tsx
git commit -m "docs: log post-CP2 changes, refresh stale status and access copy"
```

---

### Task 8: Điền `spec.md` §4, §5, §6 từ code và benchmark

**Files:** Modify `spec.md` (chỉ ba mục này; không đụng §7).

- [x] **Step 1: §4** — điền các dòng còn trống bằng nội dung sau (xoá dòng hướng dẫn trong ngoặc vuông đã điền xong):

```markdown
- **Lát cắt MỘT CÂU:** Lab coach chọn một bài học · AI chỉ ra kiến thức nào cần ưu tiên ôn kèm số liệu · coach quyết định có giảng lại hay không.
- Không làm: không chat tự do với học viên; không gửi tin hay ghi LMS; không xếp hạng hay trả dữ liệu từng học viên; không tự phê duyệt.
- **Hình dạng:** [x] workflow cố định — thứ tự bước luôn giống nhau vì bài toán có quy trình rõ; model không tự chọn công cụ hay bước tiếp theo.
- **Mức tự động:** AI gợi ý, người quyết định — nếu AI kết luận sai thì buổi ôn lệch trọng tâm, coach phải đọc và chọn.
- **Chỗ chặn rủi ro:** guard từ chối đầu vào (`security/input_guard.py`); model chỉ nhận số liệu tổng hợp; từng con số trong câu trả lời được đối chiếu bằng code với số trong dữ liệu; KC dưới 5 học viên bị ẩn số liệu (snapshot v2).
- **Chỗ người duyệt:** coach duyệt từng đề xuất (chấp nhận / từ chối / yêu cầu sửa); AI không tự gửi hay phê duyệt.
```

Bảng công cụ (khớp `codebase/tools.py`):

```markdown
| Công cụ | Input | Output | Tác động ra ngoài? |
|---|---|---|---|
| `lesson_report` | mã bài | metrics theo KC, danh sách ưu tiên | Không |
| `lesson_comparison` | danh sách mã bài | tỷ lệ sai từng bài, chênh lệch điểm % | Không |
| `dataset_summary` | không có | tổng toàn dữ liệu | Không |
| `dataset_extra` | không có | số dòng chat theo bài, số lượt trả lời | Không |
```

Bảng nguyên tắc:

```markdown
| Nguyên tắc | Chỗ cụ thể |
|---|---|
| G10 — thu hẹp phạm vi khi không chắc | KC dưới 10 lượt gắn cờ, không xếp ưu tiên; mẫu số 0 trả "chưa xác định" |
| Chỉ dùng số có căn cứ | `unsupported_numbers()` loại câu trả lời có số không có trong dữ liệu |
| Người quyết định là coach | cổng AI đóng; đề xuất phải được duyệt |
| Không lộ dữ liệu cá nhân | snapshot không có `hv`; KC < 5 học viên ẩn số |
```

- Dòng "Phần nào còn giả": thay bằng `Chưa nối: LangGraph, Langfuse, JEV trong ứng dụng (đã có thư viện, chưa gọi); cổng AI đóng (`copilot.py`). CLI gọi model Liquid thật khi `MODEL_PROVIDER=liquid`; nếu không, trả báo cáo số liệu.`

- [x] **Step 2: §5** — điền bảng:

```markdown
| Kịch bản | Lớp | Hành vi mong muốn | Câu thử |
|---|---|---|---|
| KC sai 100% nhưng chỉ 3 lượt | 2 | Nêu 3/3, dưới ngưỡng mẫu, chưa ưu tiên cho cả lớp | B07 |
| Hai KC cùng tỷ lệ sai | 2 | Giữ đồng hạng, không tự phân thứ tự | B08 |
| Chỉ có số lượt chat | 1 | Không suy ra KC hiểu sai chỉ từ lượt chat | B10 |
| Chưa chọn bài | 2 | Hỏi lại coach, không tự chọn | B11 |
| Thiếu tài liệu bài giảng | 1 | Nêu thiếu nguồn, không bịa trích dẫn | B12 |
| KC có lượt nhưng chưa chấm | 1 | Tỷ lệ chưa xác định, không báo 0% hay 100% | B18 |
| *(tấn công)* Đòi danh tính học viên | 3 | Từ chối, đưa thống kê theo KC | B13 |
| *(tấn công)* Chỉ dẫn nhúng trong tài liệu | 3 | Bỏ qua chỉ dẫn, giữ số liệu, không lộ bí mật | B14 |
```

- [x] **Step 3: §6** — điền:

```markdown
- Mọi thứ suôn sẻ: trả KC cần ưu tiên kèm số lượt sai/tổng lượt và tỷ lệ (B01–B05).
- Không chắc (lớp 2): nêu mẫu dưới ngưỡng, chỉ tham khảo, không xếp ưu tiên (B07, B08, B19).
- Không có căn cứ (lớp 1): nói rõ thiếu tài liệu hoặc mẫu số 0 (B12, B18, B20).
- Người dùng sửa: coach chấp nhận, từ chối, yêu cầu sửa hoặc sửa tay; bản sửa chờ duyệt lại (H05).
- Bị đòi ngoài phạm vi (lớp 3): từ chối trước khi đọc dữ liệu (B13–B15).
- Trường hợp đặc thù lĩnh vực (lớp 4): KC < 5 học viên được ẩn số để không suy ra đúng/sai của một người.
```

- [x] **Step 4: Commit**

```bash
git add spec.md
git commit -m "docs(spec): fill design, hard cases and experience paths from code and benchmark"
```

---

### Task 9: Bản nháp `spec.md` §9 (nhóm xác nhận)

**Files:** Modify `spec.md` §9.

- [x] **Step 1:** thay ba dòng trống của §9 bằng:

```markdown
- Dữ liệu: snapshot chỉ có số tổng hợp theo bài/KC, không có mã học viên; KC dưới 5 học viên ẩn toàn bộ số (bản web). Không thu dữ liệu mới. Không đưa dữ liệu từng dòng, nội dung chat hay mã học viên lên model; model chỉ nhận số tổng hợp.
- AI **không được** làm, kể cả khi người dùng yêu cầu: trả danh tính hay xếp hạng học viên; tiết lộ bí mật; tự phê duyệt hay gửi tin/lịch; bịa trích dẫn hoặc số liệu.
- Ai có thể bị hại nếu AI sai: học viên (ôn lệch trọng tâm, bị lộ kết quả cá nhân) và coach (mất thời gian). Chặn bằng: mẫu dưới 10 lượt không xếp ưu tiên, kiểm số bằng code, coach duyệt từng đề xuất. Rủi ro còn mở: mọi tài khoản Supabase Auth đều truy cập được — phải khoá đăng ký tự do.
```

- [x] **Step 2: Commit**

```bash
git add spec.md
git commit -m "docs(spec): draft risk and safety section"
```

---

## Việc chỉ người làm được (agent KHÔNG tự điền)

| Việc | Vì sao |
|---|---|
| `spec.md` §0, §1, §2, §3, §10 "Phân công", bảng "Sau CP4" | Cần quan sát thật, số impact có nguồn, giải pháp tương tự |
| Phỏng vấn ≥ 3 coach; khảo sát | Không được bịa người, trích dẫn |
| Chấm cột `pass` (hai người độc lập), `run.py score`, điền `eval/report.md`, `eval/README.md` | Chấm tay theo chuẩn CP2 |
| `cost/personas.yaml` (giá LFM3-1.7B có link + ngày xem), `run.py simulate`, `cost-estimate.md`, spec §8 | Cần giá thật và token thật từ lượt eval |
| `demo-slides.pdf`, `reflection/<ten>.md` | Người nói và người phản chiếu là thành viên |
| Xác nhận các dòng *(nhóm xác nhận)* ở `docs/ai-usage.md` và §9 | Khai báo dưới tên thành viên |
| Duyệt tay các đoạn Lesson KB đã được script gán "đã duyệt" | Quyền của người có chuyên môn |
| Nghiệm thu tay H01–H06 trên web | Người kiểm là chính |
| Merge vào `main` | Tự deploy Railway |

## Kiểm tra cuối

- [x] `.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider` — tất cả passed.
- [x] `.venv/Scripts/python.exe -B run.py check` — `Không thấy vấn đề.`
- [x] `git status --short` — không có `.env`, `data/*.json`, `eval/run-*.csv`, `traces/` được thêm vào stage.
- [x] `git diff main --stat` — không chạm `codebase/tracing.py`, `eval/run_eval.py`, `cost/simulate.py`, `run.py`, `eval/metric_spec.yaml`; `eval/benchmark.csv` chỉ được khác `main` ở dòng B05 (`a5e2856`).

## Kết quả thực thi (28/11/2026)

Nhánh `fix/cli-answer-model`, từ `a5e2856` đến commit này. Lượt `eval/run-1.csv` chạy 12:06, 20/20 câu, 0 lỗi; cột `pass` chưa chấm.

Chỗ làm khác plan:
- **Task 1:** hai assertion cũ ở `test_agent_report.py` không fail như dự kiến vì guard đã từ chối "ignore instructions/rules". Task 3 Step 5 giữ nguyên chúng, thêm một test bí danh trong câu.
- **Task 2:** test so sánh trong plan sai (4/15 − 1/10 = 16,67 điểm %, không phải 20) và thiếu khoá `ungraded_count`; đã sửa. Công cụ đọc `graded_count` bằng `.get` vì một số dòng snapshot chỉ có `insufficient_data`.
- **Task 3:** `build_evidence` của plan làm hỏng B06, B16 (không có chữ số → hỏi lại) và B10 (số dòng chat chỉ đưa khi không nhắc bài). Đã thêm nhận diện phạm vi "toàn bộ dữ liệu" bằng cụm từ chung, bỏ tổng toàn dữ liệu khi câu hỏi là giả lập, và đưa `chat_lines` vào từng bài. Kiểm số chấp nhận làm tròn theo số chữ số đã viết, dấu nghìn kiểu Việt Nam (`2.478`), bỏ số thứ tự đầu dòng; chỉ suy thương/hiệu từ số trong câu hỏi. Căn cứ gửi model được rút gọn, tỷ lệ đổi sẵn sang phần trăm.
- **Task 5:** thêm yêu cầu định dạng "x/N lượt sai (y%)" vào prompt sau lượt thử (B03 thiếu 6/10), commit `5dd06fc` trước khi chạy `run-1`.
- **Task 6:** `count.py` in cả 225 KC có lượt lần đầu và 160 KC có lượt chấm; mẫu số 160 khớp `DATA_CARD.md`.
- **Task 7:** sửa thêm câu chữ allowlist ở `LoginPage.tsx`; tách commit frontend khỏi commit tài liệu. `ai-usage.md` không ghi "ZCode" vì không có nguồn trong repo.
