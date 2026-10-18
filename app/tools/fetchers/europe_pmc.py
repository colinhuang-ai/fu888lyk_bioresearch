"""
Europe PMC API Client.
Tìm kiếm tài liệu, lấy tóm tắt và hỗ trợ tải PDF Open Access miễn phí.
"""

from typing import List, Optional
from pathlib import Path
import requests
from app.tools.fetchers.model.article import AcademicArticle
from app.tools.fetchers.jats_markdown import jats_to_markdown
from app.config import RAW_PAPERS_DIR


class EuropePMCFetcher:
    """Europe PMC REST API Client."""

    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    FULLTEXT_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ScientificResearchAgent/1.0"

    def __init__(self, download_dir: Path = RAW_PAPERS_DIR):
        self.download_dir = download_dir

    @staticmethod
    def _looks_like_pdf(head: bytes) -> bool:
        """File PDF thật chứa chữ ký '%PDF-' ở đầu (trong 1 KB đầu theo đặc tả)."""
        return b"%PDF-" in head[:1024]

    @classmethod
    def _is_pdf_file(cls, path: Path) -> bool:
        try:
            with open(path, "rb") as f:
                return cls._looks_like_pdf(f.read(1024))
        except OSError:
            return False

    @staticmethod
    def _default_stem(article: AcademicArticle) -> str:
        """Tên file mặc định (không đuôi): pmid_<PMID>_<40 ký tự đầu của tiêu đề>."""
        clean_title = "".join(c for c in article.title if c.isalnum() or c in (" ", "_", "-")).rstrip()
        return f"pmid_{article.pmid}_{clean_title[:40].replace(' ', '_')}"

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
                    pmcid=pmcid or None,
                    open_access_pdf=pdf_url
                ))

        except Exception as e:
            print(f"[EuropePMCFetcher] Lỗi tìm kiếm: {e}")

        return articles

    def download_pdf(self, article: AcademicArticle, filename: Optional[str] = None) -> Optional[Path]:
        """
        Tải file PDF của bài báo về thư mục data/raw_papers.
        Chỉ giữ lại file khi nội dung thật sự là PDF. Nếu server trả về HTML (ví dụ trang
        CAPTCHA chống bot của PMC) thì trả None và không để lại file nào.
        """
        if not article.open_access_pdf:
            print(f"[EuropePMCFetcher] Bài báo '{article.title[:40]}' không có PDF Open Access công khai.")
            return None

        if not filename:
            filename = f"{self._default_stem(article)}.pdf"

        file_path = self.download_dir / filename
        if file_path.exists():
            if self._is_pdf_file(file_path):
                print(f"[EuropePMCFetcher] File đã tồn tại: {file_path.name}")
                return file_path
            # Bản tải lỗi từ trước (thường là trang HTML đặt tên .pdf) -> xóa để tải lại
            print(f"[EuropePMCFetcher] {file_path.name} không phải PDF thật, xóa và tải lại.")
            file_path.unlink()

        # Ghi vào file tạm, chỉ đổi tên thành .pdf sau khi xác nhận đúng định dạng
        tmp_path = file_path.with_name(file_path.name + ".part")
        try:
            headers = {"User-Agent": self.USER_AGENT}
            with requests.get(article.open_access_pdf, headers=headers, stream=True, timeout=25) as resp:
                resp.raise_for_status()

                chunks = resp.iter_content(chunk_size=8192)
                head = b""
                for chunk in chunks:
                    head += chunk
                    if len(head) >= 1024:
                        break

                if not self._looks_like_pdf(head):
                    content_type = resp.headers.get("Content-Type", "không rõ")
                    print(
                        f"[EuropePMCFetcher] Server không trả về PDF (Content-Type: {content_type}), "
                        f"có thể bị chặn bởi CAPTCHA/chống bot: {article.open_access_pdf}"
                    )
                    return None

                with open(tmp_path, "wb") as f:
                    f.write(head)
                    for chunk in chunks:
                        if chunk:
                            f.write(chunk)

            tmp_path.replace(file_path)
            print(f"[EuropePMCFetcher] Đã tải thành công: {file_path.name}")
            return file_path
        except Exception as e:
            print(f"[EuropePMCFetcher] Tải PDF thất bại từ {article.open_access_pdf}: {e}")
            return None
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def _resolve_pmcid(self, article: AcademicArticle) -> Optional[str]:
        """Tra PMCID của bài báo (vd. từ PubMed) qua Europe PMC bằng PMID."""
        if not article.pmid:
            return None
        hits = self.search_articles(f"EXT_ID:{article.pmid} AND SRC:MED", max_results=1)
        return hits[0].pmcid if hits else None

    def save_markdown(self, article: AcademicArticle, filename: Optional[str] = None) -> Optional[Path]:
        """
        Lấy full text (JATS XML) từ Europe PMC rồi lưu thành file Markdown trong data/raw_papers.
        Chỉ hoạt động với bài thuộc Open Access subset của PMC; trả None nếu không có full text.
        """
        pmcid = article.pmcid or self._resolve_pmcid(article)
        if not pmcid:
            print(f"[EuropePMCFetcher] Bài báo '{article.title[:40]}' không có PMCID (không có full text trên PMC).")
            return None

        if not filename:
            filename = f"{self._default_stem(article)}.md"

        file_path = self.download_dir / filename
        if file_path.exists():
            print(f"[EuropePMCFetcher] File đã tồn tại: {file_path.name}")
            return file_path

        try:
            resp = requests.get(
                self.FULLTEXT_URL.format(pmcid=pmcid),
                headers={"User-Agent": self.USER_AGENT},
                timeout=25,
            )
            if resp.status_code == 404:
                print(f"[EuropePMCFetcher] {pmcid} không có full text XML (không thuộc Open Access subset).")
                return None
            resp.raise_for_status()

            markdown = jats_to_markdown(resp.content, article.model_copy(update={"pmcid": pmcid}))
            file_path.write_text(markdown, encoding="utf-8")

            print(f"[EuropePMCFetcher] Đã lưu Markdown: {file_path.name}")
            return file_path
        except Exception as e:
            print(f"[EuropePMCFetcher] Lưu Markdown thất bại cho {pmcid}: {e}")
            if file_path.exists():
                file_path.unlink()
            return None
