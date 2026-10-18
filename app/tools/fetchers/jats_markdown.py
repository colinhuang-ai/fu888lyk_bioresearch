"""
Chuyển full text JATS XML (định dạng của Europe PMC / PMC) sang Markdown.
Hàm thuần, không gọi mạng — nhận XML thô và trả về chuỗi Markdown.
"""

import re
import xml.etree.ElementTree as ET
from typing import List, Optional, Union

from app.tools.fetchers.model.article import AcademicArticle

XLINK_HREF = "{http://www.w3.org/1999/xlink}href"

# Thẻ khối: không nhúng vào dòng văn bản, được dựng riêng thành danh sách / hình / bảng
_BLOCK_TAGS = {"list", "fig", "table-wrap", "boxed-text"}
_ORDERED_LIST_TYPES = {"order", "alpha-lower", "alpha-upper", "roman-lower", "roman-upper"}
_MAX_AUTHORS = 10

# "[1]<sup>,</sup>[2]" hoặc "[30]–[32]" -> "[1,2]" / "[30–32]"
_CITATION_JOIN = re.compile(r"\[([\d,–\-]+)\](?:<sup>)?\s*([,–\-])\s*(?:</sup>)?\[(?=\d)")
_BARE_DOI = re.compile(r"^10\.\d{4,}/")


def _local(tag) -> str:
    """Bỏ namespace khỏi tên thẻ: '{ns}math' -> 'math'. Trả '' với comment/PI."""
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _is_bibr_xref(elem: ET.Element) -> bool:
    return _local(elem.tag) == "xref" and elem.get("ref-type") == "bibr"


def _tidy(text: str) -> str:
    """Chuẩn hóa khoảng trắng, gộp in đậm kề nhau ('****') và gộp trích dẫn '[1][,][2]' -> '[1,2]'."""
    text = _normalize(text).replace("****", "")
    previous = None
    while previous != text:
        previous = text
        text = _CITATION_JOIN.sub(r"[\1\2", text)
    return text


def _wrap(marker: str, inner: str) -> str:
    """Bọc inner bằng marker Markdown, giữ khoảng trắng đầu/cuối ở ngoài marker."""
    core = inner.strip()
    if not core:
        return inner
    lead = inner[: len(inner) - len(inner.lstrip())]
    trail = inner[len(inner.rstrip()):]
    return f"{lead}{marker}{core}{marker}{trail}"


def _formula(elem: ET.Element) -> str:
    """Công thức: ưu tiên MathML (chỉ lấy ký tự), tránh lặp khi có cả tex-math."""
    math = next((e for e in elem.iter() if _local(e.tag) == "math"), None)
    source = math if math is not None else elem
    return _normalize("".join(source.itertext()))


def _inline(elem: ET.Element) -> str:
    """Dựng văn bản một dòng của phần tử, giữ in nghiêng / in đậm / chỉ số / liên kết."""
    parts = [elem.text or ""]
    for child in elem:
        tag = _local(child.tag)
        if tag in _BLOCK_TAGS:
            inner = ""
        elif tag in ("italic", "i", "em"):
            inner = _wrap("*", _inline(child))
        elif tag in ("bold", "b", "strong"):
            inner = _wrap("**", _inline(child))
        elif _is_bibr_xref(child):
            text = re.sub(r"</?sup>", "", _inline(child)).strip()  # <sup> có thể nằm bên trong xref
            inner = text if text.startswith("[") else f"[{text}]"
        elif tag in ("sup", "sub"):
            inner_text = _inline(child)
            if tag == "sup" and any(_is_bibr_xref(e) for e in child.iter()):
                inner = inner_text  # chỉ số trích dẫn: đã có dạng [n], không cần <sup>
            else:
                inner = f"<{tag}>{inner_text.strip()}</{tag}>"
        elif tag == "ext-link":
            text = _inline(child).strip()
            href = child.get(XLINK_HREF)
            if href and _BARE_DOI.match(href):
                href = f"https://doi.org/{href}"
            inner = f"[{text or href}]({href})" if href else text
        elif tag in ("inline-formula", "disp-formula", "alternatives", "math"):
            inner = _formula(child)
        else:
            inner = _inline(child)
        parts.append(inner)
        parts.append(child.tail or "")
    return "".join(parts)


def _caption_text(elem: ET.Element) -> str:
    caption = elem.find("caption")
    if caption is None:
        return ""
    return " ".join(filter(None, (_tidy(_inline(c)) for c in caption)))


def _label_text(elem: ET.Element) -> str:
    label = elem.find("label")
    return _tidy(_inline(label)) if label is not None else ""


def _table_to_markdown(table: ET.Element) -> str:
    """Bảng JATS -> bảng Markdown (hàng đầu là tiêu đề; colspan/rowspan bị bỏ qua)."""
    rows: List[List[str]] = []
    for tr in table.iter():
        if _local(tr.tag) != "tr":
            continue
        cells = [
            _tidy(_inline(c)).replace("|", "\\|")
            for c in tr
            if _local(c.tag) in ("th", "td")
        ]
        if cells:
            rows.append(cells)
    if not rows:
        return ""

    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * width) + " |"]
    lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(lines)


def _render_block(elem: ET.Element, level: int, out: List[str]) -> None:
    """Dựng phần tử khối thành các khối Markdown, nối vào `out` (mỗi phần tử là một khối)."""
    tag = _local(elem.tag)

    if tag == "sec":
        title = elem.find("title")
        inner: List[str] = []
        for child in elem:
            if child is not title:
                _render_block(child, level + 1, inner)
        if inner:  # bỏ qua mục rỗng (vd. mục chỉ chứa ref-list, được dựng riêng ở cuối)
            if title is not None:
                out.append(f"{'#' * min(level, 6)} {_tidy(_inline(title))}")
            out.extend(inner)

    elif tag == "ref-list":
        return

    elif tag == "p":
        text = _tidy(_inline(elem))
        if text:
            out.append(text)
        for child in elem:  # danh sách / hình / bảng lồng trong đoạn văn
            if _local(child.tag) in _BLOCK_TAGS:
                _render_block(child, level, out)

    elif tag == "list":
        ordered = elem.get("list-type", "bullet") in _ORDERED_LIST_TYPES
        lines = []
        for index, item in enumerate(elem.findall("list-item"), 1):
            text = _tidy(" ".join(_inline(p) for p in item.findall("p"))) or _tidy(_inline(item))
            if text:
                lines.append(f"{index}. {text}" if ordered else f"- {text}")
        if lines:
            out.append("\n".join(lines))

    elif tag == "fig":
        label, caption = _label_text(elem), _caption_text(elem)
        text = f"**{label}** {caption}".strip() if label else caption
        if text:
            out.append(f"> {text}")

    elif tag == "table-wrap":
        label, caption = _label_text(elem), _caption_text(elem)
        heading = f"**{label.rstrip('.')}.** {caption}".strip() if label else caption
        if heading:
            out.append(heading)
        table = next((e for e in elem.iter() if _local(e.tag) == "table"), None)
        if table is not None:
            markdown_table = _table_to_markdown(table)
            if markdown_table:
                out.append(markdown_table)

    elif tag == "title":
        text = _tidy(_inline(elem))
        if text:
            out.append(f"**{text}**")

    elif tag == "label":
        return

    else:  # boxed-text và các thẻ bao khác: đi tiếp vào con
        for child in elem:
            _render_block(child, level, out)


def _mixed_citation_text(elem: ET.Element) -> str:
    """Văn bản của mixed-citation; pub-id (DOI/PMID) được tách ra bằng khoảng trắng."""
    parts = [elem.text or ""]
    for child in elem:
        if _local(child.tag) == "pub-id":
            value = _normalize("".join(child.itertext()))
            kind = child.get("pub-id-type", "")
            parts.append(f" https://doi.org/{value}" if kind == "doi" else f" {kind.upper()}:{value}" if kind else f" {value}")
        else:
            parts.append(_mixed_citation_text(child))
        parts.append(child.tail or "")
    return "".join(parts)


def _reference_text(ref: ET.Element) -> str:
    cite = next(
        (c for c in ref if _local(c.tag) in ("mixed-citation", "element-citation", "citation")),
        ref,
    )
    if _local(cite.tag) == "mixed-citation":
        return _normalize(_mixed_citation_text(cite))
    # element-citation có cấu trúc, không kèm dấu câu -> nối bằng khoảng trắng rồi dọn dấu
    text = _normalize(" ".join(cite.itertext()))
    return re.sub(r"\s+([,.;:)])", r"\1", text)


def jats_to_markdown(xml_content: Union[bytes, str], article: AcademicArticle) -> str:
    """
    Chuyển JATS XML của một bài báo sang Markdown.
    `article` cung cấp metadata dự phòng (tiêu đề, tác giả, DOI...) khi XML thiếu.
    """
    root = ET.fromstring(xml_content)

    title_elem = root.find(".//article-meta/title-group/article-title")
    title = _tidy(_inline(title_elem)) if title_elem is not None else article.title

    # --- Khối thông tin bài báo ---
    info: List[str] = []
    if article.authors:
        shown = ", ".join(article.authors[:_MAX_AUTHORS])
        info.append(f"- **Tác giả:** {shown}{' et al.' if len(article.authors) > _MAX_AUTHORS else ''}")
    if article.journal:
        info.append(f"- **Tạp chí:** {article.journal} ({article.pub_year})")
    if article.pmid:
        info.append(f"- **PMID:** [{article.pmid}](https://pubmed.ncbi.nlm.nih.gov/{article.pmid}/)")
    if article.pmcid:
        info.append(f"- **PMCID:** [{article.pmcid}](https://pmc.ncbi.nlm.nih.gov/articles/{article.pmcid}/)")
    if article.doi:
        info.append(f"- **DOI:** [{article.doi}](https://doi.org/{article.doi})")
    license_elem = root.find(".//permissions/license")
    license_url: Optional[str] = license_elem.get(XLINK_HREF) if license_elem is not None else None
    if license_url:
        info.append(f"- **Giấy phép:** {license_url}")
    info.append("- **Nguồn:** full text JATS XML từ Europe PMC, chuyển tự động sang Markdown")

    blocks: List[str] = [f"# {title}", "\n".join(info)]

    # --- Abstract ---
    abstract_blocks: List[str] = []
    for abstract in root.findall(".//article-meta/abstract"):
        if abstract.get("abstract-type"):  # bỏ graphical abstract / teaser
            continue
        for child in abstract:
            if _local(child.tag) != "title":
                _render_block(child, 3, abstract_blocks)
    if not abstract_blocks and article.abstract:
        abstract_blocks.append(article.abstract)
    if abstract_blocks:
        blocks.append("## Abstract")
        blocks.extend(abstract_blocks)

    # --- Thân bài ---
    body = root.find(".//body")
    if body is not None:
        for child in body:
            _render_block(child, 2, blocks)

    # --- Tài liệu tham khảo ---
    # Ưu tiên ref-list trong <back>; một số tạp chí đặt nó trong một <sec> của thân bài
    ref_list = root.find(".//back/ref-list")
    if ref_list is None:
        ref_list = root.find(".//ref-list")
    if ref_list is not None:
        lines = []
        for index, ref in enumerate(ref_list.findall("ref"), 1):
            text = _reference_text(ref)
            if text:
                lines.append(f"{index}. {text}")
        if lines:
            blocks.append("## References")
            blocks.append("\n".join(lines))

    return "\n\n".join(blocks) + "\n"
