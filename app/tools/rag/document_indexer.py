"""
Document Indexer: nạp file PDF hoặc Markdown vào ChromaDB (VectorStore).
Tự chọn bộ đọc theo đuôi file, chia chunk theo section và gắn metadata khoa học.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.tools.ingestion.pdf_parser import (
    PDFPaperParser,
    STRAIN_PATTERNS,
    CELL_LINE_PATTERNS,
    PATHWAY_PATTERNS,
)
from app.tools.ingestion.text_splitter import ScientificTextSplitter, DocumentChunk
from app.tools.rag.vector_store import VectorStore

SUPPORTED_SUFFIXES = (".pdf", ".md", ".markdown")

# Các section không mang tri thức, bỏ qua khi lập chỉ mục
_SKIP_SECTIONS = re.compile(r"^(?:references?|tài liệu tham khảo|bibliography)\b", re.IGNORECASE)
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_PMID_IN_NAME = re.compile(r"^pmid_(\d+)", re.IGNORECASE)
_PMID_IN_TEXT = re.compile(r"\*\*PMID:\*\*\s*\[?(\d+)")
_DOI_IN_TEXT = re.compile(r"\*\*DOI:\*\*\s*\[?(10\.\d{4,}/[^\]\s)]+)")
_JOURNAL_IN_TEXT = re.compile(r"\*\*Tạp chí:\*\*\s*(.+?)\s*\((\d{4})\)")


class IndexResult(BaseModel):
    """Kết quả nạp một tài liệu vào ChromaDB."""
    file_name: str
    doc_id: str
    file_type: str
    title: str = ""
    sections: int = 0
    chunks_indexed: int = 0
    pages: Optional[int] = None
    strains: List[str] = Field(default_factory=list)
    cell_lines: List[str] = Field(default_factory=list)
    pathways: List[str] = Field(default_factory=list)
    ic50_snippets: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class DocumentIndexer:
    """Đọc PDF / Markdown → chia chunk → lưu vào ChromaDB. Nạp lại cùng file sẽ ghi đè, không nhân đôi."""

    def __init__(
        self,
        vector_store: VectorStore,
        splitter: Optional[ScientificTextSplitter] = None,
        pdf_parser: Optional[PDFPaperParser] = None,
    ):
        self.vector_store = vector_store
        self.splitter = splitter or ScientificTextSplitter()
        self.pdf_parser = pdf_parser or PDFPaperParser()

    def index_file(self, path: str | Path) -> IndexResult:
        """Nạp một file .pdf / .md. Raise FileNotFoundError / ValueError nếu file sai."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Tệp không tồn tại: {p}")
        suffix = p.suffix.lower()
        if suffix == ".pdf":
            return self._index_pdf(p)
        if suffix in (".md", ".markdown"):
            return self._index_markdown(p)
        raise ValueError(f"Định dạng không được hỗ trợ: {suffix} (chỉ nhận {', '.join(SUPPORTED_SUFFIXES)})")

    def index_directory(self, directory: str | Path, recursive: bool = True) -> List[IndexResult]:
        """Nạp mọi file PDF / Markdown trong thư mục. File lỗi được ghi vào `error`, không dừng cả lô."""
        root = Path(directory)
        if not root.is_dir():
            raise NotADirectoryError(f"Không phải thư mục: {root}")
        pattern = root.rglob("*") if recursive else root.glob("*")
        files = sorted(f for f in pattern if f.is_file() and f.suffix.lower() in SUPPORTED_SUFFIXES)

        results: List[IndexResult] = []
        for f in files:
            try:
                results.append(self.index_file(f))
            except Exception as e:
                results.append(IndexResult(
                    file_name=f.name, doc_id=f.stem, file_type=f.suffix.lower().lstrip("."), error=str(e)
                ))
        return results

    # ------------------------------------------------------------------ PDF
    def _index_pdf(self, path: Path) -> IndexResult:
        parsed = self.pdf_parser.parse_pdf(path)
        doc_id = path.stem
        base_meta = self._base_meta(
            doc_id=doc_id,
            title=parsed.title,
            source=path.name,
            file_type="pdf",
            strains=parsed.identified_strains,
            cell_lines=parsed.identified_cell_lines,
            pathways=parsed.identified_pathways,
        )
        pmid = _PMID_IN_NAME.match(doc_id)
        if pmid:
            base_meta["pmid"] = pmid.group(1)

        sections = [(s.title, s.content) for s in parsed.sections if not _SKIP_SECTIONS.match(s.title)]
        count = self._store(doc_id, base_meta, sections)

        return IndexResult(
            file_name=path.name, doc_id=doc_id, file_type="pdf", title=parsed.title,
            sections=len(sections), chunks_indexed=count, pages=parsed.total_pages,
            strains=parsed.identified_strains, cell_lines=parsed.identified_cell_lines,
            pathways=parsed.identified_pathways, ic50_snippets=parsed.extracted_ic50_snippets,
        )

    # ------------------------------------------------------------- Markdown
    def _index_markdown(self, path: Path) -> IndexResult:
        text = path.read_text(encoding="utf-8")
        title, sections = self._split_markdown(text, fallback_title=path.stem)
        doc_id = path.stem

        full_text = "\n".join(content for _, content in sections)
        strains = self.pdf_parser._extract_entities(full_text, STRAIN_PATTERNS)
        cell_lines = self.pdf_parser._extract_entities(full_text, CELL_LINE_PATTERNS)
        pathways = self.pdf_parser._extract_entities(full_text, PATHWAY_PATTERNS)

        base_meta = self._base_meta(
            doc_id=doc_id, title=title, source=path.name, file_type="markdown",
            strains=strains, cell_lines=cell_lines, pathways=pathways,
        )
        base_meta.update(self._markdown_info(path.stem, text))

        indexable = [(t, c) for t, c in sections if not _SKIP_SECTIONS.match(t)]
        count = self._store(doc_id, base_meta, indexable)

        return IndexResult(
            file_name=path.name, doc_id=doc_id, file_type="markdown", title=title,
            sections=len(indexable), chunks_indexed=count,
            strains=strains, cell_lines=cell_lines, pathways=pathways,
            ic50_snippets=self.pdf_parser._extract_ic50_snippets(full_text),
        )

    @staticmethod
    def _split_markdown(text: str, fallback_title: str) -> Tuple[str, List[Tuple[str, str]]]:
        """Tách Markdown theo heading cấp 1-2 (cấp 3+ giữ nguyên trong nội dung section cha)."""
        title = ""
        sections: List[Tuple[str, str]] = []
        current_title = "Header"
        buffer: List[str] = []
        in_code = False

        def flush():
            body = "\n".join(buffer).strip()
            if body:
                sections.append((current_title, body))
            buffer.clear()

        for line in text.splitlines():
            if line.lstrip().startswith("```"):
                in_code = not in_code
            m = None if in_code else _HEADING.match(line)
            if m and len(m.group(1)) == 1 and not title:
                title = m.group(2)
                continue
            if m and len(m.group(1)) <= 2:
                flush()
                current_title = m.group(2)
            else:
                buffer.append(line)
        flush()

        return title or fallback_title, sections

    @staticmethod
    def _markdown_info(stem: str, text: str) -> Dict[str, Any]:
        """Lấy PMID / DOI / tạp chí từ tên file hoặc khối thông tin do `jats_to_markdown` sinh ra."""
        info: Dict[str, Any] = {}
        m = _PMID_IN_NAME.match(stem) or _PMID_IN_TEXT.search(text)
        if m:
            info["pmid"] = m.group(1)
        m = _DOI_IN_TEXT.search(text)
        if m:
            info["doi"] = m.group(1)
        m = _JOURNAL_IN_TEXT.search(text)
        if m:
            info["journal"], info["pub_year"] = m.group(1), int(m.group(2))
        return info

    # --------------------------------------------------------------- chung
    @staticmethod
    def _base_meta(**kwargs) -> Dict[str, Any]:
        return dict(kwargs)

    def _store(self, doc_id: str, base_meta: Dict[str, Any], sections: List[Tuple[str, str]]) -> int:
        """Chia chunk theo section rồi upsert vào ChromaDB. Xóa chunk cũ của doc_id trước để không sót chunk thừa."""
        all_chunks: List[DocumentChunk] = []
        chunk_no = 0
        for sec_title, content in sections:
            meta = dict(base_meta)
            meta["section"] = sec_title
            for chunk in self.splitter.split_text(content, meta):
                # Đánh số lại liên tục toàn tài liệu: split_text chỉ đánh số trong từng section
                chunk_no += 1
                chunk.chunk_id = f"{doc_id}_chunk_{chunk_no}"
                chunk.metadata["chunk_index"] = chunk_no
                all_chunks.append(chunk)

        self.vector_store.delete_document(doc_id)
        self.vector_store.add_chunks(all_chunks)
        return len(all_chunks)
