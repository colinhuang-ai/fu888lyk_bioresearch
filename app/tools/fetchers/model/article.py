"""
Data models dùng chung cho toàn bộ pipeline.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# khai báo class, OOP
# object là đối tượng có state, còn param là tham số truyền vào hàm
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
    pmcid: Optional[str] = None
    open_access_pdf: Optional[str] = None
