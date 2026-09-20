"""Thanh điều hướng bên trái."""

import streamlit as st


def render(assistant):
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/dna-helix.png", width=64)
        st.title("Bio-Cancer AI Studio")
        st.caption("Trợ lý Nghiên cứu Khoa học & Xuất bản Q1/Q2")
        st.markdown("---")

        rag_count = assistant.vector_store.count()
        st.metric(label="Đoạn trích trong RAG", value=rag_count)

        st.markdown("### Danh mục Phím tắt")
        st.info(
            "1. **Thu thập**: PubMed / Europe PMC\n"
            "2. **Hóa dược**: PubChem + Lipinski\n"
            "3. **RAG**: Hybrid Search (BM25 + Vector)\n"
            "4. **Viết báo**: Xuất bản thảo Word (.docx)"
        )
        st.markdown("---")
        st.caption("Dựa trên Syllabus & RAG Blueprint 2026")
