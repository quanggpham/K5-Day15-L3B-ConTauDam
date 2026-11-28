"""Tách markdown notes/quiz thành đoạn nhỏ cho Lesson KB. Hàm thuần, không I/O."""
import re
from typing import TypedDict

MAX_CHUNK_CHARS = 8000  # khớp check length(text) trong migration

NOTE_ITEM = re.compile(r'^(\d+)\.\s+(.*\S)\s*$')
QUIZ_HEADER = re.compile(r'^##\s+Câu\s+\d+\s*·\s*(\S+)\s*$')
QUIZ_OPTION = re.compile(r'^-\s+([A-D])\.\s+(.*\S)\s*$')
QUIZ_ANSWER = re.compile(r'^\*\*Đáp án:\s*([A-D])\*\*\s*$')
QUIZ_CORRECT_EXPLANATION = re.compile(r'^-\s+Lựa chọn\s+([A-D])\s+\(ĐÚNG\):\s*(.*\S)\s*$')


class Chunk(TypedDict):
    id: str
    text: str
    source: str


def chunk_notes(markdown: str, source: str) -> list[Chunk]:
    """Mỗi mục đánh số (`1. **Tiêu đề** — ...`) là một đoạn; dòng nối tiếp được gộp vào mục trước."""
    chunks: list[Chunk] = []
    number, lines = None, []

    def flush():
        if number is not None:
            text = '\n'.join(lines).strip()[:MAX_CHUNK_CHARS]
            if text:
                chunks.append({'id': f'{source}:{number}', 'text': text, 'source': source})

    for line in markdown.splitlines():
        match = NOTE_ITEM.match(line)
        if match:
            flush()
            number, lines = match.group(1), [match.group(2)]
        elif number is not None and line.strip() and not line.startswith('#'):
            lines.append(line.strip())
    flush()
    return chunks


def chunk_quiz(markdown: str, source: str) -> list[Chunk]:
    """Mỗi câu là một đoạn gồm câu hỏi, đáp án đúng và lời giải của đáp án đúng.

    Lựa chọn sai và lời giải "SAI" bị bỏ có chủ đích: chúng mô tả khái niệm khác và LLM có thể trích nhầm làm căn cứ.
    Câu thiếu đáp án hoặc lời giải đúng bị bỏ.
    """
    blocks: list[tuple[str, list[str]]] = []
    for line in markdown.splitlines():
        header = QUIZ_HEADER.match(line)
        if header:
            blocks.append((header.group(1), []))
        elif blocks:
            blocks[-1][1].append(line)
    chunks: list[Chunk] = []
    for quiz_id, body in blocks:
        chunk = _quiz_chunk(quiz_id, body, source)
        if chunk:
            chunks.append(chunk)
    return chunks


def _quiz_chunk(quiz_id: str, body: list[str], source: str) -> Chunk | None:
    question_lines: list[str] = []
    options: dict[str, str] = {}
    answer, explanation = None, None
    for line in body:
        if (match := QUIZ_OPTION.match(line)):
            options[match.group(1)] = match.group(2)
        elif (match := QUIZ_ANSWER.match(line)):
            answer = match.group(1)
        elif (match := QUIZ_CORRECT_EXPLANATION.match(line)):
            explanation = match.group(2)
        elif not options and answer is None and line.strip() and not line.startswith('*'):
            question_lines.append(line.strip())
    if not (answer and answer in options and explanation and question_lines):
        return None
    text = (f"Câu hỏi: {' '.join(question_lines)}\nĐáp án đúng: {options[answer]}\nGiải thích: {explanation}")
    return {'id': f'{source}:{quiz_id}', 'text': text[:MAX_CHUNK_CHARS], 'source': source}
