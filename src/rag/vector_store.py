"""
Vector Store quản lý lưu trữ và truy xuất vector bằng ChromaDB.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings
from src.config import VECTOR_DB_DIR, DEFAULT_COLLECTION_NAME
from src.ingestion.text_splitter import DocumentChunk


class VectorStore:
    """Giao diện quản lý Vector Store bền vững (Persistent) của ChromaDB."""

    def __init__(self, collection_name: str = DEFAULT_COLLECTION_NAME, db_path: Path = VECTOR_DB_DIR):
        self.db_path = str(db_path)
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    def add_chunks(self, chunks: List[DocumentChunk]):
        """Thêm danh sách document chunks vào ChromaDB."""
        if not chunks:
            return

        ids = [c.chunk_id for c in chunks]
        docs = [c.content for c in chunks]
        metadatas = []
        for c in chunks:
            meta = {}
            for k, v in c.metadata.items():
                if isinstance(v, list):
                    meta[k] = ", ".join(str(x) for x in v)
                elif isinstance(v, (str, int, float, bool)):
                    meta[k] = v
                else:
                    meta[k] = str(v)
            metadatas.append(meta)

        self.collection.upsert(
            ids=ids,
            documents=docs,
            metadatas=metadatas
        )

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Truy vấn tìm kiếm ngữ nghĩa theo khoảng cách vector."""
        count = self.collection.count()
        if count == 0:
            return []

        actual_k = min(top_k, count)
        results = self.collection.query(
            query_texts=[query],
            n_results=actual_k
        )

        hits: List[Dict[str, Any]] = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0] if "distances" in results else [0.0] * len(docs)
        ids = results.get("ids", [[]])[0]

        for i, (chunk_id, doc, meta, dist) in enumerate(zip(ids, docs, metas, distances)):
            # Chuyển đổi distance sang similarity score ước lượng (1 / (1 + dist))
            score = round(1.0 / (1.0 + float(dist)), 4) if dist is not None else 1.0
            hits.append({
                "id": chunk_id,
                "content": doc,
                "metadata": meta or {},
                "score": score,
                "rank": i + 1,
                "type": "dense_vector"
            })

        return hits

    def count(self) -> int:
        return self.collection.count()

    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Lấy toàn bộ dữ liệu văn bản hiện có trong collection."""
        res = self.collection.get()
        docs = res.get("documents", [])
        metas = res.get("metadatas", [])
        ids = res.get("ids", [])
        items = []
        for doc_id, doc, meta in zip(ids, docs, metas):
            items.append({
                "id": doc_id,
                "content": doc,
                "metadata": meta
            })
        return items
