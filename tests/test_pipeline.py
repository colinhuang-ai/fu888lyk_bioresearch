"""
Bộ kiểm thử tự động (Unit & Integration Tests) cho Hệ thống Nghiên cứu Kháng Ung thư.
"""

import unittest
from pathlib import Path
from unittest.mock import patch
import os
import shutil
import tempfile

import requests

from app.tools.fetchers.pubmed_fetcher import PubMedFetcher
from app.tools.fetchers.europe_pmc import EuropePMCFetcher
from app.tools.fetchers.jats_markdown import jats_to_markdown
from app.tools.fetchers.model.article import AcademicArticle
from app.tools.chemistry.pubchem_client import PubChemClient, CompoundData
from app.tools.chemistry.druglikeness import evaluate_druglikeness
from app.tools.rag.vector_store import VectorStore
from app.tools.rag.bm25_index import BM25Index
from app.tools.rag.hybrid_retriever import HybridRetriever
from app.tools.rag.document_indexer import DocumentIndexer
from app.tools.ingestion.text_splitter import ScientificTextSplitter, DocumentChunk
from app.tools.writer.paper_generator import ScientificPaperGenerator, PaperMetadata
from app.config import BASE_DIR


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


PDF_BYTES = b"%PDF-1.7\n" + b"x" * 20000
HTML_BYTES = b"<!doctype html><html><body>recaptcha challenge</body></html>"

SAMPLE_JATS = """<article xmlns:xlink="http://www.w3.org/1999/xlink">
  <front><article-meta>
    <title-group><article-title>EGFR <italic>L858R</italic> peptide</article-title></title-group>
    <abstract>
      <sec><title>Background</title><p>EGFR is a <bold>key</bold> target.</p></sec>
      <sec><title>Results</title><p>IC<sub>50</sub> was 3.4 uM.</p></sec>
    </abstract>
    <permissions><license xlink:href="https://creativecommons.org/licenses/by/4.0/"/></permissions>
  </article-meta></front>
  <body>
    <sec><title>Introduction</title>
      <p>See <xref ref-type="bibr" rid="B1">1</xref> and <ext-link xlink:href="https://example.org">a site</ext-link>.</p>
      <p>Common<xref ref-type="bibr" rid="B1"><sup>1</sup></xref><sup>,</sup><xref ref-type="bibr" rid="B2"><sup>2</sup></xref>
         and<sup><xref ref-type="bibr" rid="B3">3</xref></sup> at 5 x 10<sup>3</sup> cells; <bold>JRC-2</bold><bold>JRC-6</bold> and <ext-link xlink:href="10.1000/abc">data</ext-link>.</p>
      <sec><title>Subsection</title><p>Nested text.</p></sec>
    </sec>
    <sec><title>References</title><ref-list><ref id="B9"><mixed-citation>Ignored in body.</mixed-citation></ref></ref-list></sec>
    <sec><title>Results</title>
      <table-wrap><label>Table 1</label><caption><title>IC50 values</title></caption>
        <table>
          <thead><tr><th>Compound</th><th>IC50 (uM)</th></tr></thead>
          <tbody><tr><td>A</td><td>3.45</td></tr><tr><td>B | C</td><td>1.2</td></tr></tbody>
        </table>
      </table-wrap>
      <fig id="F1"><label>Figure 1</label><caption><title>Binding mode.</title><p>Docking pose.</p></caption></fig>
      <list list-type="order"><list-item><p>first</p></list-item><list-item><p>second</p></list-item></list>
    </sec>
  </body>
  <back><ref-list><ref id="B1"><mixed-citation>Smith J, Doe A. A paper. Nature. 2020;1:2.<pub-id pub-id-type="pmid">555</pub-id><pub-id pub-id-type="doi">10.1/x</pub-id></mixed-citation></ref></ref-list></back>
</article>"""


class _FakeResponse:
    """Response giả cho requests.get, dùng được cả với `with`."""

    def __init__(self, content: bytes, content_type: str, status_code: int = 200):
        self.content = content
        self.headers = {"Content-Type": content_type}
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error")

    def iter_content(self, chunk_size=8192):
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i:i + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class TestEuropePMCFileHandling(unittest.TestCase):
    """Kiểm tra tải PDF / lưu Markdown của EuropePMCFetcher — không cần mạng."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.fetcher = EuropePMCFetcher(download_dir=self.dir)
        self.article = AcademicArticle(
            pmid="123",
            title="EGFR peptide study",
            authors=["Nguyen A", "Tran B"],
            journal="Test Journal",
            pub_year="2026",
            doi="10.1000/test",
            pmcid="PMC999",
            open_access_pdf="https://example.org/paper.pdf",
        )
        self.pdf_path = self.dir / "pmid_123_EGFR_peptide_study.pdf"

    @patch("app.tools.fetchers.europe_pmc.requests.get")
    def test_download_pdf_keeps_real_pdf(self, mock_get):
        mock_get.return_value = _FakeResponse(PDF_BYTES, "application/pdf")
        path = self.fetcher.download_pdf(self.article)
        self.assertEqual(path, self.pdf_path)
        self.assertEqual(path.read_bytes(), PDF_BYTES)
        self.assertEqual(list(self.dir.glob("*.part")), [])

    @patch("app.tools.fetchers.europe_pmc.requests.get")
    def test_download_pdf_rejects_html_captcha_page(self, mock_get):
        mock_get.return_value = _FakeResponse(HTML_BYTES, "text/html; charset=utf-8")
        self.assertIsNone(self.fetcher.download_pdf(self.article))
        self.assertEqual(list(self.dir.iterdir()), [])

    @patch("app.tools.fetchers.europe_pmc.requests.get")
    def test_download_pdf_replaces_stale_fake_pdf(self, mock_get):
        self.pdf_path.write_bytes(HTML_BYTES)  # bản tải lỗi từ phiên bản cũ
        mock_get.return_value = _FakeResponse(PDF_BYTES, "application/pdf")
        path = self.fetcher.download_pdf(self.article)
        self.assertEqual(path.read_bytes(), PDF_BYTES)

    @patch("app.tools.fetchers.europe_pmc.requests.get")
    def test_download_pdf_removes_stale_fake_pdf_when_still_blocked(self, mock_get):
        self.pdf_path.write_bytes(HTML_BYTES)
        mock_get.return_value = _FakeResponse(HTML_BYTES, "text/html")
        self.assertIsNone(self.fetcher.download_pdf(self.article))
        self.assertFalse(self.pdf_path.exists())

    @patch("app.tools.fetchers.europe_pmc.requests.get")
    def test_download_pdf_skips_valid_existing_file(self, mock_get):
        self.pdf_path.write_bytes(PDF_BYTES)
        self.assertEqual(self.fetcher.download_pdf(self.article), self.pdf_path)
        mock_get.assert_not_called()

    def test_jats_to_markdown_structure(self):
        md = jats_to_markdown(SAMPLE_JATS, self.article)
        self.assertIn("# EGFR *L858R* peptide", md)
        self.assertIn("[PMC999](https://pmc.ncbi.nlm.nih.gov/articles/PMC999/)", md)
        self.assertIn("https://creativecommons.org/licenses/by/4.0/", md)
        self.assertIn("## Abstract", md)
        self.assertIn("### Background", md)
        self.assertIn("EGFR is a **key** target.", md)
        self.assertIn("IC<sub>50</sub> was 3.4 uM.", md)
        self.assertIn("## Introduction", md)
        self.assertIn("### Subsection", md)
        self.assertIn("[a site](https://example.org)", md)
        self.assertIn("Common[1,2] and[3] at 5 x 10<sup>3</sup> cells;", md)  # trích dẫn gộp, chỉ số mũ thật được giữ
        self.assertIn("**JRC-2JRC-6**", md)                           # in đậm kề nhau được gộp
        self.assertNotIn("****", md)
        self.assertIn("[data](https://doi.org/10.1000/abc)", md)
        self.assertEqual(md.count("## References"), 1)                # mục rỗng trong thân bài bị bỏ
        self.assertNotIn("Ignored in body", md)
        self.assertIn("**Table 1.** IC50 values", md)
        self.assertIn("| Compound | IC50 (uM) |", md)
        self.assertIn("| --- | --- |", md)
        self.assertIn("| A | 3.45 |", md)
        self.assertIn("| B \\| C | 1.2 |", md)
        self.assertIn("> **Figure 1** Binding mode. Docking pose.", md)
        self.assertIn("1. first\n2. second", md)
        self.assertIn("## References", md)
        self.assertIn("1. Smith J, Doe A. A paper. Nature. 2020;1:2. PMID:555 https://doi.org/10.1/x", md)

    @patch("app.tools.fetchers.europe_pmc.requests.get")
    def test_save_markdown_writes_file(self, mock_get):
        mock_get.return_value = _FakeResponse(SAMPLE_JATS.encode("utf-8"), "application/xml")
        path = self.fetcher.save_markdown(self.article)
        self.assertEqual(path, self.dir / "pmid_123_EGFR_peptide_study.md")
        self.assertIn("## Introduction", path.read_text(encoding="utf-8"))
        self.assertIn("PMC999/fullTextXML", mock_get.call_args.args[0])

    @patch("app.tools.fetchers.europe_pmc.requests.get")
    def test_save_markdown_returns_none_when_no_fulltext(self, mock_get):
        mock_get.return_value = _FakeResponse(b"", "text/html", status_code=404)
        self.assertIsNone(self.fetcher.save_markdown(self.article))
        self.assertEqual(list(self.dir.iterdir()), [])

    @patch("app.tools.fetchers.europe_pmc.requests.get")
    def test_save_markdown_returns_none_without_pmcid(self, mock_get):
        article = self.article.model_copy(update={"pmcid": None})
        with patch.object(EuropePMCFetcher, "_resolve_pmcid", return_value=None):
            self.assertIsNone(self.fetcher.save_markdown(article))
        mock_get.assert_not_called()


class TestDocumentIndexer(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = VectorStore(collection_name="test_indexer", db_path=self.tmp / "db")
        self.indexer = DocumentIndexer(self.store)
        self.md = self.tmp / "pmid_123_Test_paper.md"
        self.md.write_text(
            "# Test paper\n\n- **DOI:** [10.1000/abc](https://doi.org/10.1000/abc)\n\n"
            "## Abstract\n\nMCF-7 cells showed caspase-3 activation.\n\n"
            "## Results\n\nIC50 was 5.2 μM in HeLa.\n\n"
            "## References\n\n1. Should not be indexed.\n",
            encoding="utf-8",
        )

    def tearDown(self):
        del self.store, self.indexer
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_markdown_indexed_with_metadata_and_skips_references(self):
        res = self.indexer.index_file(self.md)
        self.assertEqual(res.sections, 3)  # Header + Abstract + Results
        self.assertGreater(res.chunks_indexed, 0)
        docs = self.store.get_all_documents()
        self.assertFalse(any("Should not be indexed" in d["content"] for d in docs))
        self.assertEqual(docs[0]["metadata"]["pmid"], "123")
        self.assertEqual(docs[0]["metadata"]["doi"], "10.1000/abc")

    def test_reindex_does_not_duplicate(self):
        self.indexer.index_file(self.md)
        first = self.store.count()
        self.indexer.index_file(self.md)
        self.assertEqual(self.store.count(), first)

    def test_unsupported_and_missing_file(self):
        txt = self.tmp / "a.txt"
        txt.write_text("x")
        with self.assertRaises(ValueError):
            self.indexer.index_file(txt)
        with self.assertRaises(FileNotFoundError):
            self.indexer.index_file(self.tmp / "none.pdf")


if __name__ == "__main__":
    unittest.main()
