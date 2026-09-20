"""Module kết nối và trích xuất dữ liệu bài báo từ NCBI PubMed E-Utilities API."""

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
import pandas as pd
import requests

NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedClient:
    """Client giao tiếp với NCBI PubMed E-utilities để tìm kiếm và tải bài báo khoa học."""

    def __init__(self, email: str = "researcher@example.com", tool_name: str = "ProteinResearchBot"):
        self.email = email
        self.tool_name = tool_name
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"{tool_name}/1.0 ({email})"
        })

    def search_articles(self, query: str, max_results: int = 25, sort: str = "pub_date") -> List[str]:
        """Tìm danh sách PMID (PubMed ID) dựa trên truy vấn từ khóa."""
        url = f"{NCBI_BASE_URL}/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "sort": sort,
            "retmode": "json",
            "tool": self.tool_name,
            "email": self.email,
        }
        resp = self.session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        id_list = data.get("esearchresult", {}).get("idlist", [])
        return id_list

    def fetch_details(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """Lấy thông tin chi tiết bài báo (Title, Abstract, Journal, Year, Authors, DOI) từ danh sách PMID."""
        if not pmids:
            return []

        url = f"{NCBI_BASE_URL}/efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "tool": self.tool_name,
            "email": self.email,
        }
        resp = self.session.get(url, params=params, timeout=25)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        articles: List[Dict[str, Any]] = []

        for article in root.findall(".//PubmedArticle"):
            pmid_elem = article.find(".//MedlineCitation/PMID")
            pmid = pmid_elem.text if pmid_elem is not None else ""

            # Title
            title_elem = article.find(".//MedlineCitation/Article/ArticleTitle")
            title = "".join(title_elem.itertext()).strip() if title_elem is not None else "No title"

            # Abstract
            abstract_elems = article.findall(".//MedlineCitation/Article/Abstract/AbstractText")
            if abstract_elems:
                abstract_parts = []
                for ab in abstract_elems:
                    label = ab.attrib.get("Label")
                    text = "".join(ab.itertext()).strip()
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)
                abstract = " ".join(abstract_parts)
            else:
                abstract = "No abstract available."

            # Journal
            journal_elem = article.find(".//MedlineCitation/Article/Journal/Title")
            journal = journal_elem.text if journal_elem is not None else "Unknown Journal"

            # Year
            year_elem = article.find(".//MedlineCitation/Article/Journal/JournalIssue/PubDate/Year")
            if year_elem is None:
                year_elem = article.find(".//MedlineCitation/Article/Journal/JournalIssue/PubDate/MedlineDate")
            year = year_elem.text[:4] if year_elem is not None and year_elem.text else "Unknown"

            # Authors
            author_elems = article.findall(".//MedlineCitation/Article/AuthorList/Author")
            authors = []
            for auth in author_elems:
                last_name = auth.find("LastName")
                fore_name = auth.find("ForeName")
                if last_name is not None and last_name.text:
                    if fore_name is not None and fore_name.text:
                        authors.append(f"{last_name.text} {fore_name.text}")
                    else:
                        authors.append(last_name.text)

            # DOI
            doi = ""
            for id_elem in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
                if id_elem.attrib.get("IdType") == "doi":
                    doi = id_elem.text
                    break

            articles.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "journal": journal,
                "year": year,
                "authors": ", ".join(authors[:5]) + (" et al." if len(authors) > 5 else ""),
                "doi": doi,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
            })

        return articles

    def search_protein(
        self,
        protein_name: str,
        topic: Optional[str] = None,
        max_results: int = 25
    ) -> pd.DataFrame:
        """Tìm kiếm bài báo liên quan đến protein và trả về dưới dạng DataFrame.
        
        Args:
            protein_name: Tên protein hoặc gene (ví dụ: 'EGFR', 'TP53', 'ACE2')
            topic: Chủ đề phụ ('mechanism', 'side effects', 'structure',...)
            max_results: Số lượng bài báo tối đa cần lấy.
        """
        query = f'"{protein_name}"[Title/Abstract]'
        if topic:
            query += f' AND ({topic})'

        pmids = self.search_articles(query, max_results=max_results)
        articles = self.fetch_details(pmids)
        return pd.DataFrame(articles)
