"""BM25 search restricted to approved lesson and knowledge-code documents."""
import re
from rank_bm25 import BM25Okapi


def _tokens(text: str) -> list[str]:
    return re.findall(r'\w+', text.casefold())


def retrieve(documents: list[dict], lesson_id: str, kc_code: str, query: str, limit: int = 3) -> list[dict]:
    matches = [doc for doc in documents if doc.get('approved') is True and doc.get('lesson_id') == lesson_id
               and doc.get('kc_code') == kc_code and isinstance(doc.get('text'), str)
               and isinstance(doc.get('id'), str) and _tokens(doc['text'])]
    if not matches or not _tokens(query) or limit <= 0:
        return []
    scores = BM25Okapi([_tokens(doc['text']) for doc in matches]).get_scores(_tokens(query))
    ordered = sorted(zip(matches, scores), key=lambda item: (-item[1], item[0]['id']))
    return [doc for doc, score in ordered[:limit]]
