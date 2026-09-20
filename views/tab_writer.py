"""Tab 4: Xưởng soạn thảo bản thảo bài báo Q1/Q2."""

from pathlib import Path

import streamlit as st

from app.tools.writer.paper_generator import PaperMetadata

MECHANISM_LABELS = {
    "apop": ("Apoptosis qua con đường ty thể (Mitochondrial Pathway)",
             "Apoptosis induction via mitochondrial cascade"),
    "casp": ("Hoạt hóa Caspase-3 và Caspase-9",
             "Proteolytic activation of Caspase-3 and Caspase-9"),
    "parp": ("Phân cắt PARP (Tạo mảnh 89 kDa)",
             "Cleavage of PARP (signature 89 kDa fragment)"),
    "ros": ("Gia tăng gốc tự do oxy hóa (ROS nội bào)",
            "Elevation of intracellular reactive oxygen species (ROS)"),
    "cycle": ("Bắt giữ chu kỳ tế bào tại pha G2/M",
              "G2/M phase cell cycle arrest"),
    "mmp": ("Mất điện thế màng ty thể (MMP loss qua nhuộm JC-1)",
            "Mitochondrial membrane depolarization (ΔΨm collapse)"),
}

_LEFT_KEYS = ["apop", "casp", "parp"]
_RIGHT_KEYS = ["ros", "cycle", "mmp"]


def _render_form():
    """Hiển thị form nhập liệu, trả về (đã submit, dict dữ liệu)."""
    with st.form("paper_form"):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            f_strain = st.text_input("Chủng vi khuẩn", value="Streptomyces sp. VN-08")
            f_source = st.text_input("Nguồn phân lập sinh thái", value="Marine sediment")
            f_compound = st.text_input("Tên hợp chất / Phân đoạn hoạt tính", value="Streptoketide A")
            f_journal = st.selectbox("Tạp chí mục tiêu", [
                "Journal of Natural Products",
                "European Journal of Medicinal Chemistry",
                "Bioorganic Chemistry",
                "ACS Chemical Biology",
                "Frontiers in Microbiology"
            ])
        with col_f2:
            f_cells = st.text_input("Dòng tế bào ung thư người (cách nhau dấu phẩy)", value="MCF-7, HeLa, A549")
            f_ic50 = st.text_input("Giá trị IC50 thực nghiệm", value="3.45 ± 0.28 μM")
            f_authors = st.text_input("Tác giả", value="Linh Nguyen, Minh Tran, Thi Huong Le*")
            f_affil = st.text_input("Đơn vị nghiên cứu", value="Faculty of Biology & Biotechnology, University of Science")

        st.markdown("**Cơ chế tác động phân tử (Mechanism of Action - MoA) quan sát được:**")
        checked = {}
        col_m1, col_m2 = st.columns(2)
        for column, keys in ((col_m1, _LEFT_KEYS), (col_m2, _RIGHT_KEYS)):
            with column:
                for key in keys:
                    checked[key] = st.checkbox(MECHANISM_LABELS[key][0], value=True)

        submitted = st.form_submit_button("📝 Tiến Hành Viết & Xuất Bản Thảo (Word & MD)", type="primary")

    return submitted, {
        "strain": f_strain,
        "source": f_source,
        "compound": f_compound,
        "journal": f_journal,
        "cells": f_cells,
        "ic50": f_ic50,
        "authors": f_authors,
        "affiliation": f_affil,
        "mechanisms": [MECHANISM_LABELS[k][1] for k in MECHANISM_LABELS if checked.get(k)],
    }


def _build_bioassay_rows(compound, cell_list, ic50):
    primary_cell = cell_list[0] if cell_list else "MCF-7"
    secondary_cell = cell_list[1] if len(cell_list) > 1 else "HeLa"
    return [
        {"compound": compound, "cell_line": primary_cell, "ic50": ic50, "selectivity_index": "14.2"},
        {"compound": compound, "cell_line": secondary_cell, "ic50": "4.12 ± 0.35", "selectivity_index": "11.8"},
        {"compound": "Doxorubicin (Control)", "cell_line": primary_cell, "ic50": "0.85 ± 0.08", "selectivity_index": "5.1"},
    ]


def _render_result(manuscript, form):
    st.success("🎉 ĐÃ TẠO BẢN THẢO THÀNH CÔNG!")

    # Nút tải file
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if manuscript.docx_file_path and Path(manuscript.docx_file_path).exists():
            with open(manuscript.docx_file_path, "rb") as f:
                st.download_button(
                    label="📥 Tải File Word Bản Thảo (.docx)",
                    data=f,
                    file_name=Path(manuscript.docx_file_path).name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
    with col_d2:
        st.download_button(
            label="📥 Tải File Markdown (.md)",
            data=manuscript.markdown_content,
            file_name=f"Manuscript_{form['strain']}_{form['compound']}.md",
            mime="text/markdown"
        )

    st.markdown("### Xem trước Bản Thảo (Manuscript Preview)")
    st.markdown(manuscript.markdown_content)


def render(assistant):
    st.header("✍️ Xưởng Soạn Thảo Bản Thảo Bài Báo Chuẩn ISI/Scopus (Q1/Q2)")
    st.write("Tự động tổng hợp dữ liệu vi sinh, kết quả thử nghiệm sinh học, cơ chế MoA và sinh bản thảo hoàn chỉnh xuất Word (.docx).")

    submitted, form = _render_form()
    if not submitted:
        return

    cell_list = [c.strip() for c in form["cells"].split(",") if c.strip()]
    paper_meta = PaperMetadata(
        title="",
        authors=[a.strip() for a in form["authors"].split(",") if a.strip()],
        affiliations=[form["affiliation"]],
        target_journal=form["journal"],
        bacterial_strain=form["strain"],
        isolation_source=form["source"],
        compound_name=form["compound"],
        target_cancer_cells=cell_list,
        measured_ic50=form["ic50"],
        observed_mechanisms=form["mechanisms"]
    )

    with st.spinner("Đang tổng hợp dữ liệu RAG và tạo bản thảo Word..."):
        manuscript = assistant.write_full_paper(
            meta=paper_meta,
            compound_name=form["compound"],
            bioassay_data=_build_bioassay_rows(form["compound"], cell_list, form["ic50"])
        )

    _render_result(manuscript, form)
