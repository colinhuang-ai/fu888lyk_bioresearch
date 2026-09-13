"""
NCBI PubMed E-Utilities Fetcher.
Tìm kiếm và trích xuất dữ liệu bài báo y sinh từ cơ sở dữ liệu NCBI PubMed.
"""

from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET
import requests
from pydantic import BaseModel, Field
from src.config import NCBI_EMAIL, NCBI_API_KEY


class AcademicArticle(BaseModel):
    pmid: str
    title: str
    authors: List[str] = Field(default_factory=list)
    journal: str = "Unknown Journal"
    pub_year: str = "N/A"
    doi: str = ""
    abstract: str = ""
    url: str = ""
    source: str = "PubMed"
    keywords: List[str] = Field(default_factory=list)
    open_access_pdf: Optional[str] = None


class PubMedFetcher:
    """NCBI Entrez E-Utilities API Client."""

    BASE_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    BASE_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    BASE_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(self, email: str = NCBI_EMAIL, api_key: str = NCBI_API_KEY):
        self.email = email
        self.api_key = api_key

    def _get_base_params(self) -> Dict[str, str]:
        params = {"retmode": "json"}
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    def search_pmids(self, query: str, max_results: int = 10) -> List[str]:
        """Tìm kiếm danh sách PMID theo từ khóa."""
        params = self._get_base_params()
        params.update({
            "db": "pubmed",
            "term": query,
            "retmax": str(max_results),
            "sort": "pub_date"
        })

        try:
            resp = requests.get(self.BASE_ESEARCH, params=params, timeout=12)
            resp.raise_for_status()
            data = resp.json()
            return data.get("esearchresult", {}).get("idlist", [])
        except Exception as e:
            print(f"[PubMedFetcher] Lỗi khi tìm kiếm: {e}")
            return []

    def fetch_details_by_pmids(self, pmids: List[str]) -> List[AcademicArticle]:
        """Lấy chi tiết và tóm tắt (Abstract) của danh sách PMID bằng efetch XML."""
        if not pmids:
            return []

        # Gọi efetch XML để lấy Abstract và Author đầy đủ nhất
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml"
        }
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key

        articles: List[AcademicArticle] = []

        try:
            resp = requests.get(self.BASE_EFETCH, params=params, timeout=18)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)

            for article_elem in root.findall(".//PubmedArticle"):
                pmid_elem = article_elem.find(".//MedlineCitation/PMID")
                pmid = pmid_elem.text if pmid_elem is not None else ""

                # Tiêu đề
                title_elem = article_elem.find(".//ArticleTitle")
                title = "".join(title_elem.itertext()).strip() if title_elem is not None else "No Title Available"

                # Journal
                journal_elem = article_elem.find(".//Journal/Title")
                journal = journal_elem.text.strip() if journal_elem is not None and journal_elem.text else "N/A"

                # Năm xuất bản
                year_elem = article_elem.find(".//JournalIssue/PubDate/Year")
                if year_elem is None:
                    year_elem = article_elem.find(".//JournalIssue/PubDate/MedlineDate")
                pub_year = year_elem.text[:4] if year_elem is not None and year_elem.text else "N/A"

                # Tác giả
                authors = []
                for author in article_elem.findall(".//AuthorList/Author"):
                    last_name = author.find("LastName")
                    fore_name = author.find("ForeName")
                    if last_name is not None and last_name.text:
                        name = last_name.text
                        if fore_name is not None and fore_name.text:
                            name = f"{fore_name.text} {last_name.text}"
                        authors.append(name)

                # Abstract
                abstract_parts = []
                for abstract_text in article_elem.findall(".//Abstract/AbstractText"):
                    label = abstract_text.get("Label", "")
                    text = "".join(abstract_text.itertext()).strip()
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    elif text:
                        abstract_parts.append(text)
                abstract = "\n\n".join(abstract_parts)

                # DOI
                doi = ""
                for article_id in article_elem.findall(".//ArticleIdList/ArticleId"):
                    if article_id.get("IdType") == "doi":
                        doi = article_id.text or ""
                        break

                # Keywords
                keywords = []
                for kw in article_elem.findall(".//KeywordList/Keyword"):
                    if kw.text:
                        keywords.append(kw.text.strip())

                article = AcademicArticle(
                    pmid=pmid,
                    title=title,
                    authors=authors,
                    journal=journal,
                    pub_year=pub_year,
                    doi=doi,
                    abstract=abstract,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                    source="PubMed",
                    keywords=keywords
                )
                articles.append(article)

        except Exception as e:
            print(f"[PubMedFetcher] Lỗi khi trích xuất efetch: {e}")
            # Fallback dùng esummary nếu XML thất bại
            return self._fallback_esummary(pmids)

        return articles

    def _fallback_esummary(self, pmids: List[str]) -> List[AcademicArticle]:
        params = self._get_base_params()
        params.update({"db": "pubmed", "id": ",".join(pmids)})
        articles = []
        try:
            resp = requests.get(self.BASE_ESUMMARY, params=params, timeout=12)
            data = resp.json().get("result", {})
            for pmid in pmids:
                info = data.get(pmid, {})
                title = info.get("title", "No Title")
                journal = info.get("source", "N/A")
                pubdate = info.get("pubdate", "N/A")
                authors = [a.get("name", "") for a in info.get("authors", [])]
                articles.append(AcademicArticle(
                    pmid=pmid,
                    title=title,
                    authors=authors,
                    journal=journal,
                    pub_year=pubdate[:4] if pubdate else "N/A",
                    abstract="Abstract preview not available via summary fallback.",
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    source="PubMed"
                ))
        except Exception:
            pass
        return articles

    def search_articles(self, query: str, max_results: int = 5) -> List[AcademicArticle]:
        """Hàm tích hợp: Tìm kiếm và trả về danh sách bài báo đầy đủ thông tin."""
        pmids = self.search_pmids(query=query, max_results=max_results)
        if not pmids:
            return []
        return self.fetch_details_by_pmids(pmids)
