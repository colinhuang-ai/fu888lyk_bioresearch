"""
Web Application: Trợ lý AI Nghiên cứu Dược liệu Vi sinh & Soạn thảo Bài báo Quốc tế.
Chạy bằng lệnh: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import json

from src.agent.assistant import ScientificResearchAssistant
from src.writer.paper_generator import PaperMetadata
from src.config import LAB_COMPOUNDS_CSV, RAW_PAPERS_DIR, OUTPUT_DIR

st.set_page_config(
    page_title="Bio-Cancer Research & Paper Writing Studio",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Khởi tạo Assistant trong session state để không phải load lại nhiều lần
@st.cache_resource
def get_assistant():
    return ScientificResearchAssistant()

assistant = get_assistant()

# Sidebar
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

# Tabs giao diện chính
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 1. Thu Thập Bài Báo (PubMed / PMC)",
    "🧪 2. Tra Cứu Hóa Dược & Lipinski",
    "🧠 3. Kho Tri Thức RAG (Hybrid Search)",
    "✍️ 4. Xưởng Soạn Thảo Paper Q1/Q2",
    "📊 5. Dữ Liệu Phòng Lab"
])

# ==================== TAB 1: THU THẬP BÀI BÁO ====================
with tab1:
    st.header("Thu Thập Tài Liệu Khoa Học Tự Động")
    st.write("Tìm kiếm các công trình nghiên cứu mới nhất từ cơ sở dữ liệu NCBI PubMed và Europe PMC.")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input(
            "Từ khóa tìm kiếm (Tên chủng, cơ chế, dòng tế bào)",
            value="Streptomyces anticancer apoptosis HeLa"
        )
    with col2:
        max_res = st.number_input("Số lượng bài báo", min_value=1, max_value=20, value=5)
        
    search_source = st.radio("Nguồn tìm kiếm:", ["NCBI PubMed", "Europe PMC (Có link PDF Open Access)"], horizontal=True)

    if st.button("🚀 Bắt đầu Tìm kiếm & Nạp vào RAG", type="primary"):
        with st.spinner("Đang kết nối cơ sở dữ liệu và xử lý..."):
            if search_source == "NCBI PubMed":
                articles = assistant.search_and_index_pubmed(query=search_query, max_results=max_res)
            else:
                articles = assistant.europe_pmc.search_articles(query=search_query, max_results=max_res)
                # Tự động nạp vào RAG
                for a in articles:
                    text_to_split = f"Title: {a.title}\n\nAbstract:\n{a.abstract}"
                    chunks = assistant.splitter.split_text(text_to_split, {
                        "doc_id": f"pmc_{a.pmid}", "pmid": a.pmid, "title": a.title,
                        "source": "EuropePMC", "journal": a.journal, "pub_year": a.pub_year
                    })
                    assistant.vector_store.add_chunks(chunks)
                assistant.retriever.reload()

        if articles:
            st.success(f"✓ Đã tìm thấy và nạp thành công {len(articles)} bài báo vào hệ thống RAG!")
            for idx, art in enumerate(articles, start=1):
                with st.expander(f"[{idx}] {art.title} ({art.journal}, {art.pub_year})"):
                    st.markdown(f"**Tác giả:** {', '.join(art.authors) if art.authors else 'N/A'}")
                    st.markdown(f"**PMID:** [{art.pmid}]({art.url}) | **DOI:** {art.doi}")
                    st.markdown("**Tóm tắt (Abstract):**")
                    st.write(art.abstract)
                    if art.open_access_pdf:
                        st.markdown(f"📄 **PDF Open Access:** [Tải trực tiếp]({art.open_access_pdf})")
        else:
            st.warning("Không tìm thấy kết quả nào phù hợp. Hãy thử thay đổi từ khóa.")

# ==================== TAB 2: HÓA DƯỢC & LIPINSKI ====================
with tab2:
    st.header("Tra Cứu Cấu Trúc Hóa Học & Quy Tắc 5 Lipinski")
    st.write("Đánh giá các chỉ số hóa lý ADMET sơ bộ cho hợp chất tự nhiên kháng ung thư.")
    
    col_c1, col_c2 = st.columns([3, 1])
    with col_c1:
        comp_name = st.text_input("Nhập tên hợp chất (Ví dụ: Staurosporine, Doxorubicin, Salinosporamide A, Paclitaxel)", value="Staurosporine")
    with col_c2:
        st.write("")
        st.write("")
        check_btn = st.button("🔬 Phân Tích Cấu Trúc")
        
    if check_btn and comp_name:
        with st.spinner(f"Đang truy vấn PubChem cho '{comp_name}'..."):
            rep = assistant.analyze_chemical_compound(comp_name)
            
        if rep:
            comp_obj = assistant.pubchem.get_compound_by_name(comp_name)
            col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
            col_m1.metric("Khối lượng (MW)", f"{rep.molecular_weight} Da", "≤ 500 Da")
            col_m2.metric("XLogP", f"{rep.xlogp}", "≤ 5.0")
            col_m3.metric("H-Donors (HBD)", rep.h_bond_donors, "≤ 5")
            col_m4.metric("H-Acceptors (HBA)", rep.h_bond_acceptors, "≤ 10")
            col_m5.metric("Rotatable Bonds", rep.rotatable_bonds, "≤ 10 (Veber)")

            c_left, c_right = st.columns([1, 2])
            with c_left:
                if comp_obj and comp_obj.cid:
                    img_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{comp_obj.cid}/PNG"
                    st.image(img_url, caption=f"Cấu trúc 2D của {comp_name} (CID: {comp_obj.cid})")
                    st.caption(f"[Xem chi tiết trên NCBI PubChem]({comp_obj.pubchem_url})")
            with c_right:
                st.subheader("Kết quả Đánh giá Dược tính")
                if rep.is_lipinski_compliant:
                    st.success(f"✓ {rep.summary_verdict}")
                else:
                    st.warning(f"⚠️ {rep.summary_verdict}")

                st.markdown("**Canonical SMILES:**")
                st.code(comp_obj.canonical_smiles if comp_obj else "N/A", language="text")

                st.markdown("**Đoạn văn học thuật viết sẵn cho mục Thảo luận (Discussion):**")
                st.info(rep.scientific_narrative)
        else:
            st.error(f"Không tìm thấy dữ liệu hợp chất '{comp_name}' trên PubChem.")

# ==================== TAB 3: RAG HYBRID SEARCH ====================
with tab3:
    st.header("Kho Tri Thức RAG Hybrid (ChromaDB + BM25)")
    st.write("Truy xuất chính xác các phân đoạn bài báo khoa học dựa trên sự kết hợp Dense Vector và từ khóa chính xác (RRF).")
    
    col_u1, col_u2 = st.columns([2, 1])
    with col_u1:
        rag_query = st.text_input("Nhập câu hỏi tra cứu khoa học", value="apoptotic caspase-3 activation and mitochondrial pathway")
    with col_u2:
        top_k = st.slider("Số lượng đoạn trích", 1, 10, 4)

    if st.button("🔎 Truy Vấn Kho Tri Thức"):
        hits = assistant.query_rag(query=rag_query, top_k=top_k)
        if hits:
            st.write(f"Tìm thấy **{len(hits)}** phân đoạn liên quan nhất:")
            for h in hits:
                meta = h.get("metadata", {})
                with st.expander(f"Hạng #{h['rank']} | Điểm RRF: {h['rrf_score']} | Nguồn: {meta.get('title', 'Unknown')[:60]}..."):
                    st.markdown(f"**Tạp chí / Nguồn:** {meta.get('source')} | **Mục:** {meta.get('section', 'General')}")
                    if meta.get("pmid"):
                        st.markdown(f"**PMID:** {meta.get('pmid')}")
                    st.write(h["content"])
        else:
            st.info("Chưa có tài liệu nào trong kho RAG hoặc không có kết quả khớp. Hãy nạp bài báo ở Tab 1 hoặc tải lên file PDF bên dưới.")

    st.markdown("---")
    st.subheader("Nạp thêm file PDF bài báo nghiên cứu (.pdf)")
    uploaded_pdf = st.file_uploader("Chọn file PDF bài báo khoa học để nạp vào RAG", type=["pdf"])
    if uploaded_pdf is not None:
        save_dest = RAW_PAPERS_DIR / uploaded_pdf.name
        with open(save_dest, "wb") as f:
            f.write(uploaded_pdf.getbuffer())
        with st.spinner("Đang phân tích cấu trúc PDF và lập chỉ mục..."):
            res = assistant.ingest_pdf_file(save_dest)
        st.success(f"✓ Đã nạp thành công file '{uploaded_pdf.name}' ({res['chunks_indexed']} chunks đã lập chỉ mục)!")

# ==================== TAB 4: PAPER WRITING STUDIO ====================
with tab4:
    st.header("✍️ Xưởng Soạn Thảo Bản Thảo Bài Báo Chuẩn ISI/Scopus (Q1/Q2)")
    st.write("Tự động tổng hợp dữ liệu vi sinh, kết quả thử nghiệm sinh học, cơ chế MoA và sinh bản thảo hoàn chỉnh xuất Word (.docx).")

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
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            m_apop = st.checkbox("Apoptosis qua con đường ty thể (Mitochondrial Pathway)", value=True)
            m_casp = st.checkbox("Hoạt hóa Caspase-3 và Caspase-9", value=True)
            m_parp = st.checkbox("Phân cắt PARP (Tạo mảnh 89 kDa)", value=True)
        with col_m2:
            m_ros = st.checkbox("Gia tăng gốc tự do oxy hóa (ROS nội bào)", value=True)
            m_cycle = st.checkbox("Bắt giữ chu kỳ tế bào tại pha G2/M", value=True)
            m_mmp = st.checkbox("Mất điện thế màng ty thể (MMP loss qua nhuộm JC-1)", value=True)

        submit_paper = st.form_submit_button("📝 Tiến Hành Viết & Xuất Bản Thảo (Word & MD)", type="primary")

    if submit_paper:
        mechanisms = []
        if m_apop: mechanisms.append("Apoptosis induction via mitochondrial cascade")
        if m_casp: mechanisms.append("Proteolytic activation of Caspase-3 and Caspase-9")
        if m_parp: mechanisms.append("Cleavage of PARP (signature 89 kDa fragment)")
        if m_ros: mechanisms.append("Elevation of intracellular reactive oxygen species (ROS)")
        if m_cycle: mechanisms.append("G2/M phase cell cycle arrest")
        if m_mmp: mechanisms.append("Mitochondrial membrane depolarization (ΔΨm collapse)")

        cell_list = [c.strip() for c in f_cells.split(",") if c.strip()]
        paper_meta = PaperMetadata(
            title="",
            authors=[a.strip() for a in f_authors.split(",") if a.strip()],
            affiliations=[f_affil],
            target_journal=f_journal,
            bacterial_strain=f_strain,
            isolation_source=f_source,
            compound_name=f_compound,
            target_cancer_cells=cell_list,
            measured_ic50=f_ic50,
            observed_mechanisms=mechanisms
        )

        sample_bioassay = [
            {"compound": f_compound, "cell_line": cell_list[0] if cell_list else "MCF-7", "ic50": f_ic50, "selectivity_index": "14.2"},
            {"compound": f_compound, "cell_line": cell_list[1] if len(cell_list) > 1 else "HeLa", "ic50": "4.12 ± 0.35", "selectivity_index": "11.8"},
            {"compound": "Doxorubicin (Control)", "cell_line": cell_list[0] if cell_list else "MCF-7", "ic50": "0.85 ± 0.08", "selectivity_index": "5.1"}
        ]

        with st.spinner("Đang tổng hợp dữ liệu RAG và tạo bản thảo Word..."):
            manuscript = assistant.write_full_paper(
                meta=paper_meta,
                compound_name=f_compound,
                bioassay_data=sample_bioassay
            )

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
                file_name=f"Manuscript_{f_strain}_{f_compound}.md",
                mime="text/markdown"
            )

        st.markdown("### Xem trước Bản Thảo (Manuscript Preview)")
        st.markdown(manuscript.markdown_content)

# ==================== TAB 5: DỮ LIỆU PHÒNG LAB ====================
with tab5:
    st.header("Quản Lý Dữ Liệu Thực Nghiệm Phòng Lab")
    st.write("Bảng ghi nhận các chủng vi khuẩn, phân đoạn hoạt tính và giá trị IC50 đã thử nghiệm.")

    if LAB_COMPOUNDS_CSV.exists():
        df = pd.read_csv(LAB_COMPOUNDS_CSV)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Chưa có file lab_compounds.csv.")
