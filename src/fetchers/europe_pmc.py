"""
Europe PMC API Client.
Tìm kiếm tài liệu, lấy tóm tắt và hỗ trợ tải PDF Open Access miễn phí.
"""

from typing import List, Optional
from pathlib import Path
import requests
from src.fetchers.pubmed_fetcher import AcademicArticle
from src.config import RAW_PAPERS_DIR


class EuropePMCFetcher:
    """Europe PMC REST API Client."""

    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    def __init__(self, download_dir: Path = RAW_PAPERS_DIR):
        self.download_dir = download_dir

    def search_articles(
        self,
        query: str,
        max_results: int = 5,
        open_access_only: bool = False
    ) -> List[AcademicArticle]:
        """Tìm kiếm bài báo trên Europe PMC."""
        full_query = query
        if open_access_only:
            full_query += " OPEN_ACCESS:y"

        params = {
            "query": full_query,
            "format": "json",
            "resultType": "core",
            "pageSize": str(max_results)
        }

        articles: List[AcademicArticle] = []

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("resultList", {}).get("result", [])

            for item in results:
                pmid = item.get("pmid", item.get("id", ""))
                title = item.get("title", "No Title").strip().rstrip(".")
                journal = item.get("journalTitle", item.get("journalInfo", {}).get("journal", {}).get("title", "N/A"))
                pub_year = str(item.get("pubYear", "N/A"))
                doi = item.get("doi", "")
                abstract = item.get("abstractText", "No abstract available.")
                
                # Tác giả
                author_string = item.get("authorString", "")
                authors = [a.strip() for a in author_string.split(",") if a.strip()]

                # Open Access PDF Link
                pdf_url = None
                pmcid = item.get("pmcid", "")
                is_oa = item.get("isOpenAccess", "N") == "Y"
                if is_oa and pmcid:
                    pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
                elif is_oa and item.get("fullTextUrlList", {}).get("fullTextUrl"):
                    for ft in item.get("fullTextUrlList", {}).get("fullTextUrl", []):
                        if ft.get("documentStyle") == "pdf":
                            pdf_url = ft.get("url")
                            break

                # Keywords / MeSH
                keywords = []
                mesh_headings = item.get("meshHeadingList", {}).get("meshHeading", [])
                for mesh in mesh_headings:
                    descriptor = mesh.get("descriptorName")
                    if descriptor:
                        keywords.append(descriptor)

                articles.append(AcademicArticle(
                    pmid=pmid,
                    title=title,
                    authors=authors,
                    journal=journal,
                    pub_year=pub_year,
                    doi=doi,
                    abstract=abstract,
                    url=f"https://europepmc.org/article/MED/{pmid}" if pmid else "",
                    source="EuropePMC",
                    keywords=keywords,
                    open_access_pdf=pdf_url
                ))

        except Exception as e:
            print(f"[EuropePMCFetcher] Lỗi tìm kiếm: {e}")

        return articles

    def download_pdf(self, article: AcademicArticle, filename: Optional[str] = None) -> Optional[Path]:
        """Tải file PDF của bài báo về thư mục data/raw_papers."""
        if not article.open_access_pdf:
            print(f"[EuropePMCFetcher] Bài báo '{article.title[:40]}' không có PDF Open Access công khai.")
            return None

        if not filename:
            clean_title = "".join(c for c in article.title if c.isalnum() or c in (" ", "_", "-")).rstrip()
            filename = f"pmid_{article.pmid}_{clean_title[:40].replace(' ', '_')}.pdf"

        file_path = self.download_dir / filename
        if file_path.exists():
            print(f"[EuropePMCFetcher] File đã tồn tại: {file_path.name}")
            return file_path

        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ScientificResearchAgent/1.0"}
            resp = requests.get(article.open_access_pdf, headers=headers, stream=True, timeout=25)
            resp.raise_for_status()

            with open(file_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            print(f"[EuropePMCFetcher] Đã tải thành công: {file_path.name}")
            return file_path
        except Exception as e:
            print(f"[EuropePMCFetcher] Tải PDF thất bại từ {article.open_access_pdf}: {e}")
            if file_path.exists():
                file_path.unlink()
            return None
