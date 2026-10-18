"""
Scientific Research & Paper Assistant Coordinator.
Điều phối toàn bộ quy trình: Thu thập -> Lập chỉ mục RAG -> Tra cứu Hóa dược -> Viết bài báo.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path

from app.tools.fetchers.pubmed_fetcher import PubMedFetcher
from app.tools.fetchers.model.article import AcademicArticle
from app.tools.fetchers.europe_pmc import EuropePMCFetcher
from app.tools.ingestion.pdf_parser import PDFPaperParser
from app.tools.ingestion.text_splitter import ScientificTextSplitter, DocumentChunk
from app.tools.chemistry.pubchem_client import PubChemClient, CompoundData
from app.tools.chemistry.druglikeness import evaluate_druglikeness, DruglikenessReport
from app.tools.rag.vector_store import VectorStore
from app.tools.rag.hybrid_retriever import HybridRetriever
from app.tools.rag.document_indexer import DocumentIndexer, IndexResult
from app.tools.writer.paper_generator import ScientificPaperGenerator, PaperMetadata, GeneratedManuscript
from app.config import RAW_PAPERS_DIR, OUTPUT_DIR


class ScientificResearchAssistant:
    """Trợ lý nghiên cứu toàn diện cho nhà khoa học."""

    def __init__(self):
        self.pubmed = PubMedFetcher()
        self.europe_pmc = EuropePMCFetcher()
        self.pdf_parser = PDFPaperParser()
        self.splitter = ScientificTextSplitter()
        self.pubchem = PubChemClient()
        self.vector_store = VectorStore()
        self.indexer = DocumentIndexer(self.vector_store, self.splitter, self.pdf_parser)
        self.retriever = HybridRetriever(vector_store=self.vector_store)
        self.paper_writer = ScientificPaperGenerator(hybrid_retriever=self.retriever)

    def search_and_index_pubmed(self, query: str, max_results: int = 5) -> List[AcademicArticle]:
        """Tìm kiếm trên PubMed và tự động nạp Abstract vào hệ thống RAG Hybrid."""
        articles = self.pubmed.search_articles(query=query, max_results=max_results)
        if not articles:
            return []

        all_chunks: List[DocumentChunk] = []
        for art in articles:
            text_to_split = f"Title: {art.title}\n\nAbstract:\n{art.abstract}"
            meta = {
                "doc_id": f"pmid_{art.pmid}",
                "pmid": art.pmid,
                "title": art.title,
                "journal": art.journal,
                "pub_year": art.pub_year,
                "doi": art.doi,
                "source": "PubMed",
                "section": "Abstract"
            }
            chunks = self.splitter.split_text(text_to_split, meta)
            all_chunks.extend(chunks)

        if all_chunks:
            self.vector_store.add_chunks(all_chunks)
            self.retriever.reload()

        return articles

    def ingest_document(self, file_path: str | Path) -> IndexResult:
        """Nạp một file PDF hoặc Markdown vào ChromaDB và dựng lại chỉ mục BM25."""
        result = self.indexer.index_file(file_path)
        if result.chunks_indexed:
            self.retriever.reload()
        return result

    def ingest_directory(self, directory: str | Path = RAW_PAPERS_DIR) -> List[IndexResult]:
        """Nạp toàn bộ PDF / Markdown trong một thư mục (mặc định data/raw_papers)."""
        results = self.indexer.index_directory(directory)
        if any(r.chunks_indexed for r in results):
            self.retriever.reload()
        return results

    def ingest_pdf_file(self, pdf_path: str | Path) -> Dict[str, Any]:
        """Đọc và nạp một file PDF vào kho RAG."""
        r = self.ingest_document(pdf_path)
        return {
            "file_name": r.file_name,
            "title": r.title,
            "pages": r.pages,
            "chunks_indexed": r.chunks_indexed,
            "strains": r.strains,
            "cell_lines": r.cell_lines,
            "ic50_snippets": r.ic50_snippets
        }

    def analyze_chemical_compound(self, compound_name: str) -> Optional[DruglikenessReport]:
        """Tra cứu PubChem và tính toán Lipinski Rule of 5."""
        comp = self.pubchem.get_compound_by_name(compound_name)
        if not comp:
            return None
        return evaluate_druglikeness(comp)

    def query_rag(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Truy vấn tìm kiếm kiến thức từ các bài báo đã nạp."""
        return self.retriever.search(query=query, top_k=top_k)

    def write_full_paper(
        self,
        meta: PaperMetadata,
        compound_name: Optional[str] = None,
        bioassay_data: Optional[List[Dict[str, Any]]] = None
    ) -> GeneratedManuscript:
        """Tạo bản thảo bài báo hoàn chỉnh, xuất ra Word (.docx) và Markdown."""
        drug_report = None
        target_compound = compound_name or meta.compound_name
        if target_compound and target_compound.lower() not in ("bioactive fraction", "unknown"):
            drug_report = self.analyze_chemical_compound(target_compound)

        return self.paper_writer.generate_manuscript(
            meta=meta,
            druglikeness=drug_report,
            bioassay_data=bioassay_data
        )
