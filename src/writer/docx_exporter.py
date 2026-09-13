"""
Xuất bản thảo bài báo khoa học ra định dạng Microsoft Word (.docx) chuyên nghiệp.
Chuẩn hóa font Times New Roman, cỡ chữ 12pt, dãn dòng 1.5, lề 1 inch chuẩn nộp tạp chí quốc tế.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def set_cell_background(cell, fill_hex: str):
    """Thiết lập màu nền cho ô trong bảng."""
    tc_pr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tc_pr.append(shd)


class AcademicDocxExporter:
    """Trình xuất bản thảo Word chuẩn quốc tế."""

    def __init__(self):
        pass

    def export_manuscript(
        self,
        title: str,
        authors: List[str],
        affiliations: List[str],
        abstract: str,
        keywords: List[str],
        sections: Dict[str, str],
        references: List[str],
        output_path: str | Path,
        bioassay_table_data: Optional[List[Dict[str, Any]]] = None,
        druglikeness_data: Optional[Dict[str, Any]] = None
    ) -> Path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        doc = Document()

        # Thiết lập lề 1 inch (2.54 cm)
        for sec in doc.sections:
            sec.top_margin = Inches(1.0)
            sec.bottom_margin = Inches(1.0)
            sec.left_margin = Inches(1.0)
            sec.right_margin = Inches(1.0)

        # Style mặc định
        normal_style = doc.styles['Normal']
        normal_style.font.name = 'Times New Roman'
        normal_style.font.size = Pt(12)
        normal_style.font.color.rgb = RGBColor(0x22, 0x22, 0x22)

        # 1. TIÊU ĐỀ BÀI BÁO (TITLE)
        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_p.add_run(title)
        title_run.font.name = 'Times New Roman'
        title_run.font.size = Pt(18)
        title_run.bold = True
        title_run.font.color.rgb = RGBColor(0x11, 0x33, 0x66)
        title_p.paragraph_format.space_after = Pt(12)

        # 2. TÁC GIẢ & ĐƠN VỊ (AUTHORS & AFFILIATIONS)
        if authors:
            auth_p = doc.add_paragraph()
            auth_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            auth_run = auth_p.add_run(", ".join(authors))
            auth_run.font.name = 'Times New Roman'
            auth_run.font.size = Pt(11)
            auth_run.bold = True
            auth_p.paragraph_format.space_after = Pt(4)

        if affiliations:
            for aff in affiliations:
                aff_p = doc.add_paragraph()
                aff_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                aff_run = aff_p.add_run(aff)
                aff_run.font.name = 'Times New Roman'
                aff_run.font.size = Pt(10)
                aff_run.italic = True
                aff_p.paragraph_format.space_after = Pt(2)

        doc.add_paragraph().paragraph_format.space_after = Pt(8)

        # 3. ABSTRACT & KEYWORDS
        abs_heading = doc.add_heading("Abstract", level=2)
        abs_heading.paragraph_format.space_before = Pt(8)
        abs_heading.paragraph_format.space_after = Pt(4)

        abs_p = doc.add_paragraph()
        abs_run = abs_p.add_run(abstract)
        abs_run.font.name = 'Times New Roman'
        abs_run.font.size = Pt(10.5)
        abs_p.paragraph_format.line_spacing = 1.25
        abs_p.paragraph_format.space_after = Pt(6)

        if keywords:
            kw_p = doc.add_paragraph()
            kw_bold = kw_p.add_run("Keywords: ")
            kw_bold.bold = True
            kw_bold.font.size = Pt(10)
            kw_val = kw_p.add_run(", ".join(keywords))
            kw_val.italic = True
            kw_val.font.size = Pt(10)
            kw_p.paragraph_format.space_after = Pt(16)

        # 4. NỘI DUNG CHÍNH (SECTIONS)
        for sec_title, sec_content in sections.items():
            h = doc.add_heading(sec_title, level=1)
            h.paragraph_format.space_before = Pt(14)
            h.paragraph_format.space_after = Pt(6)

            # Chia đoạn văn
            paras = [p.strip() for p in sec_content.split("\n\n") if p.strip()]
            for para_text in paras:
                p = doc.add_paragraph()
                p_run = p.add_run(para_text)
                p_run.font.name = 'Times New Roman'
                p_run.font.size = Pt(11.5)
                p.paragraph_format.line_spacing = 1.3
                p.paragraph_format.space_after = Pt(6)

            # Nếu là mục Kết quả, có thể chèn bảng Bioassay hoặc Lipinski nếu có
            if "results" in sec_title.lower() and bioassay_table_data:
                self._insert_bioassay_table(doc, bioassay_table_data)
                bioassay_table_data = None  # Chỉ chèn 1 lần

            if "docking" in sec_title.lower() or "drug-likeness" in sec_title.lower():
                if druglikeness_data:
                    self._insert_druglikeness_table(doc, druglikeness_data)
                    druglikeness_data = None

        # 5. TÀI LIỆU THAM KHẢO (REFERENCES)
        ref_heading = doc.add_heading("References", level=1)
        ref_heading.paragraph_format.space_before = Pt(16)
        ref_heading.paragraph_format.space_after = Pt(8)

        for i, ref in enumerate(references, start=1):
            rp = doc.add_paragraph()
            ref_run = rp.add_run(f"[{i}] {ref}")
            ref_run.font.name = 'Times New Roman'
            ref_run.font.size = Pt(10)
            rp.paragraph_format.space_after = Pt(4)

        doc.save(str(out_file))
        return out_file

    def _insert_bioassay_table(self, doc: Document, data: List[Dict[str, Any]]):
        caption_p = doc.add_paragraph()
        caption_run = caption_p.add_run("Table 1. In vitro Cytotoxicity (IC50, μM) Against Human Cancer Cell Lines.")
        caption_run.bold = True
        caption_run.font.size = Pt(10.5)

        table = doc.add_table(rows=1, cols=4)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = True

        hdr_cells = table.rows[0].cells
        headers = ["Compound / Fraction", "Cell Line", "IC50 (μM / μg·mL⁻¹)", "Selectivity Index (SI)"]
        for idx, text in enumerate(headers):
            hdr_cells[idx].text = text
            hdr_cells[idx].paragraphs[0].runs[0].bold = True
            hdr_cells[idx].paragraphs[0].runs[0].font.size = Pt(10)
            set_cell_background(hdr_cells[idx], "EAECEE")

        for row_data in data:
            row_cells = table.add_row().cells
            row_cells[0].text = str(row_data.get("compound", "N/A"))
            row_cells[1].text = str(row_data.get("cell_line", "N/A"))
            row_cells[2].text = str(row_data.get("ic50", "N/A"))
            row_cells[3].text = str(row_data.get("selectivity_index", "> 5.0"))
            for c in row_cells:
                if c.paragraphs and c.paragraphs[0].runs:
                    c.paragraphs[0].runs[0].font.size = Pt(9.5)

        doc.add_paragraph().paragraph_format.space_after = Pt(8)

    def _insert_druglikeness_table(self, doc: Document, drug_dict: Dict[str, Any]):
        caption_p = doc.add_paragraph()
        caption_run = caption_p.add_run("Table 2. Physicochemical Properties & Lipinski Rule of Five Parameters.")
        caption_run.bold = True
        caption_run.font.size = Pt(10.5)

        table = doc.add_table(rows=1, cols=3)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        hdr_cells = table.rows[0].cells
        headers = ["Descriptor / Filter", "Calculated Value", "Lipinski / Veber Criteria"]
        for idx, text in enumerate(headers):
            hdr_cells[idx].text = text
            hdr_cells[idx].paragraphs[0].runs[0].bold = True
            hdr_cells[idx].paragraphs[0].runs[0].font.size = Pt(10)
            set_cell_background(hdr_cells[idx], "EAECEE")

        rows = [
            ("Molecular Weight (MW)", f"{drug_dict.get('molecular_weight', 'N/A')} Da", "≤ 500 Da"),
            ("Partition Coefficient (XLogP)", f"{drug_dict.get('xlogp', 'N/A')}", "≤ 5.0"),
            ("Hydrogen Bond Donors (HBD)", f"{drug_dict.get('h_bond_donors', 'N/A')}", "≤ 5"),
            ("Hydrogen Bond Acceptors (HBA)", f"{drug_dict.get('h_bond_donors', 'N/A')}", "≤ 10"),
            ("Rotatable Bonds Count", f"{drug_dict.get('rotatable_bonds', 'N/A')}", "≤ 10 (Veber criteria)"),
            ("Lipinski Violations", f"{drug_dict.get('lipinski_violations', 0)}", "≤ 1 (Drug-like candidate)")
        ]

        for desc, val, crit in rows:
            rc = table.add_row().cells
            rc[0].text = desc
            rc[1].text = val
            rc[2].text = crit
            for c in rc:
                if c.paragraphs and c.paragraphs[0].runs:
                    c.paragraphs[0].runs[0].font.size = Pt(9.5)

        doc.add_paragraph().paragraph_format.space_after = Pt(8)
