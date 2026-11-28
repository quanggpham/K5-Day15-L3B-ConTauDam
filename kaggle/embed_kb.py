"""Chạy trên Kaggle (GPU nếu có): embed đoạn Lesson KB, ghi /kaggle/working/kb_embeddings.jsonl.

Đầu vào: dataset private chứa kb_chunks.jsonl (từ scripts/export_kb_chunks.py), gắn vào kernel.
Đầu ra mỗi dòng: {"id", "model", "embedding"} — scripts/load_kb_embeddings.py kiểm tra model/số chiều/đủ id.
Model và tiền tố phải khớp codebase/backend/rag/embedding.py (file này chạy độc lập nên chép hằng số).
Kernel cần bật Internet để tải model từ Hugging Face.
"""
import glob
import json
from pathlib import Path

from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL = 'intfloat/multilingual-e5-small'
PASSAGE_PREFIX = 'passage: '
BATCH_SIZE = 64
OUTPUT = Path('/kaggle/working/kb_embeddings.jsonl')


def main() -> None:
    inputs = glob.glob('/kaggle/input/**/kb_chunks.jsonl', recursive=True)
    if len(inputs) != 1:
        raise SystemExit(f'cần đúng 1 kb_chunks.jsonl trong /kaggle/input, thấy {len(inputs)}')
    with open(inputs[0], encoding='utf-8') as file:
        chunks = [json.loads(line) for line in file if line.strip()]
    model = SentenceTransformer(EMBEDDING_MODEL)
    vectors = model.encode([PASSAGE_PREFIX + chunk['text'] for chunk in chunks], batch_size=BATCH_SIZE,
                           normalize_embeddings=True, show_progress_bar=True)
    with OUTPUT.open('w', encoding='utf-8') as file:
        for chunk, vector in zip(chunks, vectors, strict=True):
            file.write(json.dumps({'id': chunk['id'], 'model': EMBEDDING_MODEL, 'embedding': vector.tolist()}) + '\n')
    print(f'{len(chunks)} embeddings, {vectors.shape[1]} chiều, device={model.device} -> {OUTPUT}')


if __name__ == '__main__':
    main()
