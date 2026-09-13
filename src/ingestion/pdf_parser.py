"""
Trích xuất và phân tích cấu trúc bài báo khoa học từ tệp PDF bằng pypdfium2.
Tự động tách các phần (Abstract, Methods, Results, Discussion, Mechanism) và nhận diện thực thể sinh học.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import re
from pydantic import BaseModel, Field
import pypdfium2 as pdfium


class ParsedSection(BaseModel):
    title: str
    content: str
    page_start: int
    page_end: int


class ParsedPaper(BaseModel):
    file_name: str
    file_path: str
    total_pages: int
    title: str = ""
    abstract: str = ""
    sections: List[ParsedSection] = Field(default_factory=list)
    identified_strains: List[str] = Field(default_factory=list)
    identified_cell_lines: List[str] = Field(default_factory=list)
    identified_pathways: List[str] = Field(default_factory=list)
    extracted_ic50_snippets: List[str] = Field(default_factory=list)


# Từ điển nhận diện thực thể sinh học và hóa dược
STRAIN_PATTERNS = [
    r"\bStreptomyces\s+[a-z0-9_\-]+",
    r"\bBacillus\s+[a-z0-9_\-]+",
    r"\bActinobacteria\b",
    r"\bMicromonospora\s+[a-z0-9_\-]+",
    r"\bPseudomonas\s+[a-z0-9_\-]+",
    r"\bPenicillium\s+[a-z0-9_\-]+",
    r"\bAspergillus\s+[a-z0-9_\-]+"
]

CELL_LINE_PATTERNS = [
    r"\b(HeLa|MCF-7|HepG2|A549|PC-3|HCT-?116|MDA-MB-231|U87|K562|SW480|HT-29|SKOV3|Vero|HEK-?293)\b"
]

PATHWAY_PATTERNS = [
    r"\b(Caspase-3|Caspase-8|Caspase-9|PARP|Bax|Bcl-2|p53|Cytochrome\s+c|PI3K|Akt|mTOR|MAPK|ERK|JNK|NF-[kκ]B|ROS|MMP|\u0394\u03a8m|Apoptosis|Autophagy)\b"
]

IC50_PATTERNS = [
    r"(?:IC\s*50|IC50)\s*(?:=|is|was|of|value)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:μM|uM|µM|μg\/mL|ug\/mL|ng\/mL)",
    r"([0-9]+(?:\.[0-9]+)?)\s*(?:μM|uM|µM)\s*(?:\([^\)]*IC50\))?"
]


class PDFPaperParser:
    """Bộ phân tích bài báo PDF chuyên dụng cho sinh dược học và ung thư."""

    SECTION_HEADERS = {
        "abstract": re.compile(r"^(?:abstract|tóm tắt)\b", re.IGNORECASE),
        "introduction": re.compile(r"^(?:1\.?\s*)?(?:introduction|background|đặt vấn đề)\b", re.IGNORECASE),
        "materials_and_methods": re.compile(r"^(?:2\.?\s*)?(?:materials?\s+and\s+methods?|experimental(?:\s+section)?|phương pháp)\b", re.IGNORECASE),
        "results": re.compile(r"^(?:3\.?\s*)?(?:results?(?:\s+and\s+discussion)?|kết quả)\b", re.IGNORECASE),
        "discussion": re.compile(r"^(?:4\.?\s*)?(?:discussion|thảo luận)\b", re.IGNORECASE),
        "conclusion": re.compile(r"^(?:5\.?\s*)?(?:conclusions?|kết luận)\b", re.IGNORECASE),
        "references": re.compile(r"^(?:references|tài liệu tham khảo)\b", re.IGNORECASE)
    }

    def parse_pdf(self, pdf_path: str | Path) -> ParsedPaper:
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"Tệp không tồn tại: {path}")

        pdf = pdfium.PdfDocument(str(path))
        total_pages = len(pdf)

        page_texts: List[str] = []
        for i in range(total_pages):
            page = pdf[i]
            textpage = page.get_textpage()
            page_texts.append(textpage.get_text_range())

        full_text = "\n\n".join(page_texts)

        # 1. Trích xuất tiêu đề (thường ở trang 1, các dòng đầu)
        title = self._extract_title(page_texts[0] if page_texts else path.stem)

        # 2. Phân chia sections
        sections = self._split_into_sections(page_texts)

        # 3. Trích xuất Abstract
        abstract = ""
        for sec in sections:
            if "abstract" in sec.title.lower():
                abstract = sec.content
                break
        if not abstract and sections:
            # Fallback nếu header không khớp rõ
            abstract = sections[0].content[:1500]

        # 4. Trích xuất thực thể khoa học
        strains = self._extract_entities(full_text, STRAIN_PATTERNS)
        cell_lines = self._extract_entities(full_text, CELL_LINE_PATTERNS)
        pathways = self._extract_entities(full_text, PATHWAY_PATTERNS)
        ic50_snippets = self._extract_ic50_snippets(full_text)

        return ParsedPaper(
            file_name=path.name,
            file_path=str(path.resolve()),
            total_pages=total_pages,
            title=title,
            abstract=abstract,
            sections=sections,
            identified_strains=strains,
            identified_cell_lines=cell_lines,
            identified_pathways=pathways,
            extracted_ic50_snippets=ic50_snippets
        )

    def _extract_title(self, first_page_text: str) -> str:
        lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]
        # Bỏ qua tên tạp chí, DOI nếu nằm đầu trang
        candidates = []
        for line in lines[:10]:
            if len(line) > 20 and not line.lower().startswith(("http", "doi:", "volume", "journal", "issn")):
                candidates.append(line)
        return candidates[0] if candidates else "Untitled Paper"

    def _split_into_sections(self, page_texts: List[str]) -> List[ParsedSection]:
        sections: List[ParsedSection] = []
        current_section_title = "Header / Title"
        current_content: List[str] = []
        start_page = 1

        for page_idx, page_text in enumerate(page_texts, start=1):
            lines = page_text.splitlines()
            for line in lines:
                clean_line = line.strip()
                matched_header = None
                for sec_key, pattern in self.SECTION_HEADERS.items():
                    if pattern.match(clean_line) and len(clean_line) < 60:
                        matched_header = clean_line
                        break

                if matched_header:
                    if current_content:
                        sections.append(ParsedSection(
                            title=current_section_title,
                            content="\n".join(current_content).strip(),
                            page_start=start_page,
                            page_end=page_idx
                        ))
                        current_content = []
                    current_section_title = matched_header
                    start_page = page_idx
                else:
                    current_content.append(line)

        if current_content:
            sections.append(ParsedSection(
                title=current_section_title,
                content="\n".join(current_content).strip(),
                page_start=start_page,
                page_end=len(page_texts)
            ))

        return sections

    def _extract_entities(self, text: str, patterns: List[str]) -> List[str]:
        results = set()
        for p in patterns:
            matches = re.findall(p, text, flags=re.IGNORECASE)
            for m in matches:
                if isinstance(m, tuple):
                    m = m[0]
                results.add(m.strip())
        return sorted(list(results))

    def _extract_ic50_snippets(self, text: str) -> List[str]:
        snippets = []
        for pattern in IC50_PATTERNS:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                start = max(0, match.start() - 60)
                end = min(len(text), match.end() + 60)
                snip = text[start:end].replace("\n", " ").strip()
                snippets.append(snip)
        return list(set(snippets))[:10]
