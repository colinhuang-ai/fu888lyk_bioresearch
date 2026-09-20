"""Tab 2: Tra cứu hóa dược PubChem & quy tắc 5 Lipinski."""

import streamlit as st


def render(assistant):
    st.header("Tra Cứu Cấu Trúc Hóa Học & Quy Tắc 5 Lipinski")
    st.write("Đánh giá các chỉ số hóa lý ADMET sơ bộ cho hợp chất tự nhiên kháng ung thư.")

    col_c1, col_c2 = st.columns([3, 1])
    with col_c1:
        comp_name = st.text_input(
            "Nhập tên hợp chất (Ví dụ: Staurosporine, Doxorubicin, Salinosporamide A, Paclitaxel)",
            value="Staurosporine"
        )
    with col_c2:
        st.write("")
        st.write("")
        check_btn = st.button("🔬 Phân Tích Cấu Trúc")

    if not (check_btn and comp_name):
        return

    with st.spinner(f"Đang truy vấn PubChem cho '{comp_name}'..."):
        rep = assistant.analyze_chemical_compound(comp_name)

    if not rep:
        st.error(f"Không tìm thấy dữ liệu hợp chất '{comp_name}' trên PubChem.")
        return

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
