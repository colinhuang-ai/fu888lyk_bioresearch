"""Tab 1: Thu thập bài báo từ PubMed / Europe PMC."""

import streamlit as st


def render(assistant):
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

    search_source = st.radio(
        "Nguồn tìm kiếm:",
        ["NCBI PubMed", "Europe PMC (Có link PDF Open Access)"],
        horizontal=True
    )

    if not st.button("🚀 Bắt đầu Tìm kiếm & Nạp vào RAG", type="primary"):
        return

    with st.spinner("Đang kết nối cơ sở dữ liệu và xử lý..."):
        if search_source == "NCBI PubMed":
            articles = assistant.search_and_index_pubmed(query=search_query, max_results=max_res)
        else:
            articles = assistant.europe_pmc.search_articles(query=search_query, max_results=max_res)
            # Tự động nạp vào RAG với mỗi bài báo
            for a in articles:
                print(f"Nạp bài báo PMC {a.pmid} vào RAG...")
                text_to_split = f"Title: {a.title}\n\nAbstract:\n{a.abstract}"
                chunks = assistant.splitter.split_text(text_to_split, {
                    "doc_id": f"pmc_{a.pmid}", "pmid": a.pmid, "title": a.title,
                    "source": "EuropePMC", "journal": a.journal, "pub_year": a.pub_year
                })
                assistant.vector_store.add_chunks(chunks)
            assistant.retriever.reload()

    if not articles:
        st.warning("Không tìm thấy kết quả nào phù hợp. Hãy thử thay đổi từ khóa.")
        return

    st.success(f"✓ Đã tìm thấy và nạp thành công {len(articles)} bài báo vào hệ thống RAG!")
    for idx, art in enumerate(articles, start=1):
        with st.expander(f"[{idx}] {art.title} ({art.journal}, {art.pub_year})"):
            st.markdown(f"**Tác giả:** {', '.join(art.authors) if art.authors else 'N/A'}")
            st.markdown(f"**PMID:** [{art.pmid}]({art.url}) | **DOI:** {art.doi}")
            st.markdown("**Tóm tắt (Abstract):**")
            st.write(art.abstract)
            if art.open_access_pdf:
                st.markdown(f"📄 **PDF Open Access:** [Tải trực tiếp]({art.open_access_pdf})")
