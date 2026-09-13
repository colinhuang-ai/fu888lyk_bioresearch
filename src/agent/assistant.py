"""
Scientific Research & Paper Assistant Coordinator.
Điều phối toàn bộ quy trình: Thu thập -> Lập chỉ mục RAG -> Tra cứu Hóa dược -> Viết bài báo.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path

from src.fetchers.pubmed_fetcher import PubMedFetcher, AcademicArticle
from src.fetchers.europe_pmc import EuropePMCFetcher
from src.ingestion.pdf_parser import PDFPaperParser
from src.ingestion.text_splitter import ScientificTextSplitter, DocumentChunk
from src.chemistry.pubchem_client import PubChemClient, CompoundData
from src.chemistry.druglikeness import evaluate_druglikeness, DruglikenessReport
from src.rag.vector_store import VectorStore
from src.rag.hybrid_retriever import HybridRetriever
from src.writer.paper_generator import ScientificPaperGenerator, PaperMetadata, GeneratedManuscript
from src.config import RAW_PAPERS_DIR, OUTPUT_DIR


class ScientificResearchAssistant:
    """Trợ lý nghiên cứu toàn diện cho nhà khoa học."""

    def __init__(self):
        self.pubmed = PubMedFetcher()
        self.europe_pmc = EuropePMCFetcher()
        self.pdf_parser = PDFPaperParser()
        self.splitter = ScientificTextSplitter()
        self.pubchem = PubChemClient()
        self.vector_store = VectorStore()
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

    def ingest_pdf_file(self, pdf_path: str | Path) -> Dict[str, Any]:
        """Đọc và nạp một file PDF vào kho RAG."""
        parsed = self.pdf_parser.parse_pdf(pdf_path)
        all_chunks: List[DocumentChunk] = []

        base_meta = {
            "doc_id": Path(pdf_path).stem,
            "title": parsed.title,
            "source": Path(pdf_path).name,
            "strains": parsed.identified_strains,
            "cell_lines": parsed.identified_cell_lines,
            "pathways": parsed.identified_pathways
        }

        for sec in parsed.sections:
            sec_meta = dict(base_meta)
            sec_meta["section"] = sec.title
            chunks = self.splitter.split_text(sec.content, sec_meta)
            all_chunks.extend(chunks)

        if all_chunks:
            self.vector_store.add_chunks(all_chunks)
            self.retriever.reload()

        return {
            "file_name": parsed.file_name,
            "title": parsed.title,
            "pages": parsed.total_pages,
            "chunks_indexed": len(all_chunks),
            "strains": parsed.identified_strains,
            "cell_lines": parsed.identified_cell_lines,
            "ic50_snippets": parsed.extracted_ic50_snippets
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
