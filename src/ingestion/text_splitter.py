"""
Semantic Text Splitter chuyên dụng cho văn bản khoa học.
Bảo toàn tính toàn vẹn câu và gắn nhãn metadata ngữ cảnh.
"""

from typing import List, Dict, Any
from pydantic import BaseModel
import re


class DocumentChunk(BaseModel):
    chunk_id: str
    content: str
    metadata: Dict[str, Any]


class ScientificTextSplitter:
    """Chia nhỏ văn bản tài liệu theo đoạn và kích thước phù hợp cho Vector Embedding & BM25."""

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str, base_metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """Tách văn bản dựa trên đoạn văn và ranh giới câu."""
        text = text.strip()
        if not text:
            return []

        # Tách theo đoạn văn trước
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: List[DocumentChunk] = []
        current_chunk = ""
        chunk_idx = 1

        for para in paragraphs:
            if len(current_chunk) + len(para) < self.chunk_size:
                current_chunk += ("\n\n" + para if current_chunk else para)
            else:
                if current_chunk:
                    meta = dict(base_metadata)
                    meta["chunk_index"] = chunk_idx
                    doc_id = f"{base_metadata.get('doc_id', 'doc')}_chunk_{chunk_idx}"
                    chunks.append(DocumentChunk(chunk_id=doc_id, content=current_chunk, metadata=meta))
                    chunk_idx += 1

                # Nếu bản thân paragraph quá dài, cắt theo câu
                if len(para) > self.chunk_size:
                    sentences = re.split(r"(?<=[.!?])\s+", para)
                    sub_chunk = ""
                    for s in sentences:
                        if len(sub_chunk) + len(s) < self.chunk_size:
                            sub_chunk += (" " + s if sub_chunk else s)
                        else:
                            if sub_chunk:
                                meta = dict(base_metadata)
                                meta["chunk_index"] = chunk_idx
                                doc_id = f"{base_metadata.get('doc_id', 'doc')}_chunk_{chunk_idx}"
                                chunks.append(DocumentChunk(chunk_id=doc_id, content=sub_chunk, metadata=meta))
                                chunk_idx += 1
                            sub_chunk = s
                    current_chunk = sub_chunk
                else:
                    current_chunk = para

        if current_chunk:
            meta = dict(base_metadata)
            meta["chunk_index"] = chunk_idx
            doc_id = f"{base_metadata.get('doc_id', 'doc')}_chunk_{chunk_idx}"
            chunks.append(DocumentChunk(chunk_id=doc_id, content=current_chunk, metadata=meta))

        return chunks
