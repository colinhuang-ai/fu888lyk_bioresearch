"""
Hybrid Retriever kết hợp Dense Vector (ChromaDB) và Sparse Keyword (BM25)
bằng giải thuật Reciprocal Rank Fusion (RRF).
"""

from typing import List, Dict, Any, Optional
from src.rag.vector_store import VectorStore
from src.rag.bm25_index import BM25Index


class HybridRetriever:
    """Truy xuất tài liệu lai tối ưu hóa cho nghiên cứu khoa học."""

    def __init__(self, vector_store: VectorStore, rrf_k: int = 60):
        self.vector_store = vector_store
        self.rrf_k = rrf_k
        self.bm25_index = BM25Index()
        self._refresh_bm25()

    def _refresh_bm25(self):
        """Đồng bộ dữ liệu từ ChromaDB sang BM25 Index."""
        docs = self.vector_store.get_all_documents()
        self.bm25_index.build_index(docs)

    def reload(self):
        """Hàm gọi làm mới index khi có tài liệu mới nạp vào."""
        self._refresh_bm25()

    def search(
        self,
        query: str,
        top_k: int = 5,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Thực hiện tìm kiếm lai (Hybrid Search):
        1. Lấy top kết quả từ Dense Vector Search.
        2. Lấy top kết quả từ BM25 Sparse Search.
        3. Kết hợp bằng Reciprocal Rank Fusion (RRF).
        """
        # Đảm bảo BM25 đồng bộ
        if not self.bm25_index.corpus_chunks and self.vector_store.count() > 0:
            self._refresh_bm25()

        fetch_limit = max(top_k * 2, 10)
        dense_results = self.vector_store.search(query=query, top_k=fetch_limit)
        sparse_results = self.bm25_index.search(query=query, top_k=fetch_limit)

        # Tính RRF Score
        doc_pool: Dict[str, Dict[str, Any]] = {}
        rrf_scores: Dict[str, float] = {}

        # Xử lý Dense
        for item in dense_results:
            doc_id = item["id"]
            rank = item["rank"]
            doc_pool[doc_id] = item
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (dense_weight / (self.rrf_k + rank))

        # Xử lý Sparse
        for item in sparse_results:
            doc_id = item["id"]
            rank = item["rank"]
            if doc_id not in doc_pool:
                doc_pool[doc_id] = item
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (sparse_weight / (self.rrf_k + rank))

        # Sắp xếp theo điểm RRF giảm dần
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        final_results: List[Dict[str, Any]] = []
        for rank, doc_id in enumerate(sorted_ids[:top_k], start=1):
            base_item = doc_pool[doc_id]
            final_results.append({
                "id": doc_id,
                "content": base_item["content"],
                "metadata": base_item["metadata"],
                "rrf_score": round(rrf_scores[doc_id], 6),
                "rank": rank,
                "type": "hybrid_rrf"
            })

        return final_results

    def format_context_for_prompt(self, results: List[Dict[str, Any]]) -> str:
        """Định dạng context thành văn bản rõ ràng để đưa vào prompt cho LLM/Writer."""
        if not results:
            return "Không có ngữ cảnh tài liệu tham khảo nào được tìm thấy."

        snippets = []
        for i, res in enumerate(results, start=1):
            meta = res.get("metadata", {})
            title = meta.get("title", "Unknown Title")
            source = meta.get("source", "Paper")
            sec = meta.get("section", "Abstract")
            pmid = meta.get("pmid", "")
            pmid_str = f"PMID:{pmid} | " if pmid else ""
            snippets.append(
                f"--- [TÀI LIỆU {i}] ---\n"
                f"Nguồn: {source} ({pmid_str}Mục: {sec})\n"
                f"Tiêu đề: {title}\n"
                f"Nội dung trích đoạn:\n{res['content']}"
            )
        return "\n\n".join(snippets)
