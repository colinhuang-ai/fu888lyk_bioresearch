"""Tab 3: Kho tri thức RAG Hybrid (ChromaDB + BM25)."""

import streamlit as st

from app.config import RAW_PAPERS_DIR


def render(assistant):
    st.header("Kho Tri Thức RAG Hybrid (ChromaDB + BM25)")
    st.write("Truy xuất chính xác các phân đoạn bài báo khoa học dựa trên sự kết hợp Dense Vector và từ khóa chính xác (RRF).")

    col_u1, col_u2 = st.columns([2, 1])
    with col_u1:
        rag_query = st.text_input(
            "Nhập câu hỏi tra cứu khoa học",
            value="apoptotic caspase-3 activation and mitochondrial pathway"
        )
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
    st.subheader("Nạp thêm bài báo nghiên cứu (.pdf / .md)")
    uploaded = st.file_uploader("Chọn file PDF hoặc Markdown để nạp vào RAG", type=["pdf", "md"])
    if uploaded is not None:
        save_dest = RAW_PAPERS_DIR / uploaded.name
        with open(save_dest, "wb") as f:
            f.write(uploaded.getbuffer())
        with st.spinner("Đang phân tích cấu trúc tài liệu và lập chỉ mục..."):
            res = assistant.ingest_document(save_dest)
        st.success(f"✓ Đã nạp thành công file '{uploaded.name}' ({res.chunks_indexed} chunks đã lập chỉ mục)!")

    if st.button("📂 Nạp toàn bộ thư mục data/raw_papers"):
        with st.spinner("Đang lập chỉ mục toàn bộ PDF / Markdown..."):
            results = assistant.ingest_directory(RAW_PAPERS_DIR)
        ok = [r for r in results if not r.error]
        st.success(f"✓ Đã nạp {len(ok)}/{len(results)} file ({sum(r.chunks_indexed for r in ok)} chunks).")
        for r in results:
            if r.error:
                st.warning(f"{r.file_name}: {r.error}")
