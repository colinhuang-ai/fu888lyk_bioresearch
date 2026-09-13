"""
BM25 Keyword Indexing cho tài liệu y sinh học.
Đảm bảo bắt chính xác tên chủng vi sinh, mã hợp chất, gen và dòng tế bào.
"""

from typing import List, Dict, Any, Tuple
import re
from rank_bm25 import BM25Okapi


def scientific_tokenize(text: str) -> List[str]:
    """Tách từ giữ nguyên các ký tự gạch nối chuyên ngành (e.g. MCF-7, Caspase-3, IC50)."""
    clean_text = text.lower()
    tokens = re.findall(r"[a-z0-9]+(?:[\-_/][a-z0-9]+)*", clean_text)
    return tokens


class BM25Index:
    """Lập chỉ mục BM25 phục vụ Sparse Keyword Search."""

    def __init__(self):
        self.corpus_chunks: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []
        self.bm25: BM25Okapi | None = None

    def build_index(self, documents: List[Dict[str, Any]]):
        """Build lại BM25 index từ danh sách documents có {id, content, metadata}."""
        self.corpus_chunks = documents
        self.tokenized_corpus = [scientific_tokenize(d["content"]) for d in documents]
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        else:
            self.bm25 = None

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.bm25 or not self.corpus_chunks:
            return []

        query_tokens = scientific_tokenize(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)
        scored_pairs: List[Tuple[int, float]] = [(idx, float(score)) for idx, score in enumerate(scores) if score > 0]
        scored_pairs.sort(key=lambda x: x[1], reverse=True)

        results: List[Dict[str, Any]] = []
        for rank, (idx, score) in enumerate(scored_pairs[:top_k], start=1):
            doc = self.corpus_chunks[idx]
            results.append({
                "id": doc["id"],
                "content": doc["content"],
                "metadata": doc.get("metadata", {}),
                "score": round(score, 4),
                "rank": rank,
                "type": "bm25_sparse"
            })
        return results
