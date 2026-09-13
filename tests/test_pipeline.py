"""
Bộ kiểm thử tự động (Unit & Integration Tests) cho Hệ thống Nghiên cứu Kháng Ung thư.
"""

import unittest
from pathlib import Path
import os
import shutil

from src.fetchers.pubmed_fetcher import PubMedFetcher, AcademicArticle
from src.chemistry.pubchem_client import PubChemClient, CompoundData
from src.chemistry.druglikeness import evaluate_druglikeness
from src.rag.vector_store import VectorStore
from src.rag.bm25_index import BM25Index
from src.rag.hybrid_retriever import HybridRetriever
from src.ingestion.text_splitter import ScientificTextSplitter, DocumentChunk
from src.writer.paper_generator import ScientificPaperGenerator, PaperMetadata
from src.config import BASE_DIR


class TestScientificPipeline(unittest.TestCase):

    def setUp(self):
        self.test_db_dir = BASE_DIR / "data" / "test_vector_db"
        self.splitter = ScientificTextSplitter(chunk_size=300, chunk_overlap=50)

    def tearDown(self):
        # Dọn dẹp thư mục test vector db nếu có
        if self.test_db_dir.exists():
            shutil.rmtree(self.test_db_dir, ignore_errors=True)

    def test_pubchem_and_lipinski(self):
        """Kiểm tra tra cứu PubChem và tính toán quy tắc Lipinski."""
        client = PubChemClient()
        comp = client.get_compound_by_name("Staurosporine")
        self.assertIsNotNone(comp)
        self.assertGreater(comp.molecular_weight, 400)
        self.assertIn("N", comp.canonical_smiles)

        report = evaluate_druglikeness(comp)
        self.assertEqual(report.compound_name, "Staurosporine")
        self.assertTrue(report.is_lipinski_compliant)
        self.assertIn("Lipinski's Rule of Five", report.scientific_narrative)

    def test_hybrid_rag_indexing_and_retrieval(self):
        """Kiểm tra lập chỉ mục kép Vector + BM25 và truy xuất bằng RRF."""
        vstore = VectorStore(collection_name="test_collection", db_path=self.test_db_dir)

        chunks = [
            DocumentChunk(
                chunk_id="chunk_1",
                content="Streptomyces sp. VN-08 produces secondary metabolites that activate caspase-3 and induce apoptosis in MCF-7 cells.",
                metadata={"title": "Anticancer Streptomyces Paper", "source": "PubMed", "section": "Results"}
            ),
            DocumentChunk(
                chunk_id="chunk_2",
                content="Bacillus velezensis demonstrates antimicrobial peptides and promotes plant growth.",
                metadata={"title": "Bacillus Ecology", "source": "Journal", "section": "Abstract"}
            ),
            DocumentChunk(
                chunk_id="chunk_3",
                content="Mitochondrial depolarization with loss of membrane potential triggers the release of cytochrome c.",
                metadata={"title": "Apoptosis Review", "source": "PMC", "section": "Discussion"}
            )
        ]

        vstore.add_chunks(chunks)
        self.assertEqual(vstore.count(), 3)

        retriever = HybridRetriever(vector_store=vstore)
        results = retriever.search(query="caspase-3 apoptosis MCF-7", top_k=2)

        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "chunk_1")
        self.assertIn("caspase-3", results[0]["content"])

    def test_paper_generator_and_docx_export(self):
        """Kiểm tra module viết bài báo và xuất file Word .docx."""
        vstore = VectorStore(collection_name="test_collection_paper", db_path=self.test_db_dir)
        retriever = HybridRetriever(vector_store=vstore)
        generator = ScientificPaperGenerator(hybrid_retriever=retriever)

        meta = PaperMetadata(
            title="",
            authors=["Dr. Linh Nguyen", "Prof. Research"],
            affiliations=["Biotechnology Department"],
            target_journal="Journal of Natural Products",
            bacterial_strain="Streptomyces sp. K-12",
            isolation_source="Mangrove sediment",
            compound_name="Streptomycinol",
            target_cancer_cells=["MCF-7", "A549"],
            measured_ic50="2.8 ± 0.2 μM",
            observed_mechanisms=["Apoptosis induction", "Caspase-3 cleavage"]
        )

        manuscript = generator.generate_manuscript(meta=meta)

        self.assertIsNotNone(manuscript)
        self.assertIn("Streptomyces sp. K-12", manuscript.title)
        self.assertIn("1. Introduction", manuscript.sections)
        self.assertIn("2. Results and Discussion", manuscript.sections)
        self.assertTrue(Path(manuscript.docx_file_path).exists())
        self.assertGreater(os.path.getsize(manuscript.docx_file_path), 1000)

    def test_pubmed_fetcher_live(self):
        """Kiểm tra gọi PubMed API thực tế."""
        fetcher = PubMedFetcher()
        articles = fetcher.search_articles(query="Streptomyces apoptosis", max_results=2)
        self.assertIsInstance(articles, list)
        if articles:  # Nếu có kết nối mạng
            self.assertIsNotNone(articles[0].pmid)
            self.assertIsNotNone(articles[0].title)


if __name__ == "__main__":
    unittest.main()
