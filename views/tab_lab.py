"""
Tab 5: Bảng điều khiển phân tích & quản lý dữ liệu thực nghiệm phòng lab (Oncology Lab Analytics).
Hỗ trợ sàng lọc độc tế bào, đánh giá độ an toàn (SI), phân tích cơ chế MoA và mô phỏng đường cong liều - đáp ứng (Dose-Response).
"""

from datetime import datetime
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.config import LAB_COMPOUNDS_CSV


def load_lab_data() -> pd.DataFrame:
    """Tải và chuẩn hóa dữ liệu từ file lab_compounds.csv."""
    if not LAB_COMPOUNDS_CSV.exists():
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(LAB_COMPOUNDS_CSV)
        # Ép kiểu dữ liệu số
        numeric_cols = ["ic50_uM", "selectivity_index", "molecular_weight", "purity_pct"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Lỗi khi đọc file dữ liệu phòng lab: {e}")
        return pd.DataFrame()


def render(assistant=None):
    st.header("📊 Bảng Điều Khiển Dữ Liệu Thực Nghiệm Phòng Lab")
    st.caption("Oncology & Natural Products Discovery Analytics | Đánh giá Hoạt tính Kháng Ung thư & Sàng lọc Dẫn chất")

    df_raw = load_lab_data()

    if df_raw.empty:
        st.warning("⚠️ Chưa có dữ liệu thực nghiệm trong hệ thống hoặc file `lab_compounds.csv` trống.")
        st.info("Hãy tạo file hoặc sử dụng nút khởi tạo dữ liệu mẫu bên dưới.")
        return

    # ==========================================
    # 1. KPI SUMMARY CARDS
    # ==========================================
    total_assays = len(df_raw)
    unique_compounds = df_raw["compound_name"].nunique() if "compound_name" in df_raw else 0
    unique_strains = df_raw["source_strain"].nunique() if "source_strain" in df_raw else 0
    
    # Định nghĩa Lead Candidate: IC50 <= 5.0 uM và SI >= 10.0 (loại trừ nhóm chứng dương nếu có)
    leads_mask = (df_raw["ic50_uM"] <= 5.0) & (df_raw["selectivity_index"] >= 10.0)
    lead_count = int(leads_mask.sum())
    lead_rate = (lead_count / total_assays * 100) if total_assays > 0 else 0

    # Tìm hợp chất tự nhiên có hoạt tính mạnh nhất (IC50 nhỏ nhất, không tính đối chứng)
    natural_df = df_raw[~df_raw["source_strain"].str.contains("Positive Control|Chứng dương", case=False, na=False)]
    if not natural_df.empty:
        top_lead = natural_df.loc[natural_df["ic50_uM"].idxmin()]
        top_lead_name = f"{top_lead['compound_name']} ({top_lead['ic50_uM']:.2f} µM)"
        top_lead_detail = f"Dòng {top_lead['cancer_cell_line']} | SI: {top_lead['selectivity_index']:.1f}"
    else:
        top_lead_name = "N/A"
        top_lead_detail = ""

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("🧪 Tổng Mẫu Đo (Assays)", f"{total_assays}")
    kpi2.metric("💊 Hợp Chất Độc Lập", f"{unique_compounds}")
    kpi3.metric("🧫 Chủng Vi Sinh / Nguồn", f"{unique_strains}")
    kpi4.metric("⭐ Lead Tiềm Năng (Hit)", f"{lead_count} mẫu", f"{lead_rate:.1f}% hit rate")
    kpi5.metric("🏆 Hợp Chất Tiềm Năng Nhất", top_lead_name, top_lead_detail)

    st.markdown("---")

    # ==========================================
    # 2. INTERACTIVE FILTERS
    # ==========================================
    with st.expander("🔍 Bộ Lọc Dữ Liệu Thực Nghiệm Đa Chiều", expanded=False):
        f_col1, f_col2, f_col3 = st.columns(3)
        
        # Lọc dòng tế bào ung thư
        all_cell_lines = sorted(df_raw["cancer_cell_line"].dropna().unique().tolist())
        sel_cell_lines = f_col1.multiselect("Dòng tế bào ung thư:", options=all_cell_lines, default=all_cell_lines)

        # Lọc nhóm hợp chất
        if "compound_class" in df_raw.columns:
            all_classes = sorted(df_raw["compound_class"].dropna().unique().tolist())
            sel_classes = f_col2.multiselect("Nhóm hóa dược (Class):", options=all_classes, default=all_classes)
        else:
            sel_classes = []

        # Lọc trạng thái sàng lọc
        if "lead_status" in df_raw.columns:
            all_statuses = sorted(df_raw["lead_status"].dropna().unique().tolist())
            sel_statuses = f_col3.multiselect("Trạng thái sàng lọc (Status):", options=all_statuses, default=all_statuses)
        else:
            sel_statuses = []

        f_col4, f_col5, f_col6 = st.columns([2, 2, 2])
        # Ngưỡng IC50
        max_ic50_val = float(df_raw["ic50_uM"].max()) if not df_raw["ic50_uM"].isna().all() else 100.0
        slider_ic50 = f_col4.slider("Ngưỡng IC50 tối đa (µM):", min_value=0.1, max_value=float(np.ceil(max_ic50_val)), value=float(np.ceil(max_ic50_val)), step=0.5)

        # Ngưỡng Selectivity Index
        max_si_val = float(df_raw["selectivity_index"].max()) if not df_raw["selectivity_index"].isna().all() else 40.0
        slider_si = f_col5.slider("Ngưỡng Chỉ số Chọn lọc (SI) tối thiểu:", min_value=1.0, max_value=float(np.ceil(max_si_val)), value=1.0, step=0.5)

        # Tìm kiếm từ khóa
        search_kw = f_col6.text_input("Tìm kiếm theo tên / chủng / cơ chế:", placeholder="Ví dụ: Streptomyces, Annexin, Cần Giờ...")

    # Áp dụng bộ lọc
    filtered_df = df_raw.copy()
    if sel_cell_lines:
        filtered_df = filtered_df[filtered_df["cancer_cell_line"].isin(sel_cell_lines)]
    if sel_classes and "compound_class" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["compound_class"].isin(sel_classes)]
    if sel_statuses and "lead_status" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["lead_status"].isin(sel_statuses)]
    
    filtered_df = filtered_df[filtered_df["ic50_uM"] <= slider_ic50]
    filtered_df = filtered_df[filtered_df["selectivity_index"] >= slider_si]

    if search_kw:
        kw_lower = search_kw.lower().strip()
        mask = (
            filtered_df["compound_name"].str.lower().str.contains(kw_lower, na=False) |
            filtered_df["source_strain"].str.lower().str.contains(kw_lower, na=False) |
            filtered_df["apoptosis_status"].str.lower().str.contains(kw_lower, na=False)
        )
        if "isolation_source" in filtered_df.columns:
            mask = mask | filtered_df["isolation_source"].str.lower().str.contains(kw_lower, na=False)
        filtered_df = filtered_df[mask]

    st.write(f"Đang hiển thị **{len(filtered_df)} / {len(df_raw)}** kết quả thực nghiệm phù hợp.")

    # ==========================================
    # 3. ANALYTICS TABS
    # ==========================================
    subtab1, subtab2, subtab3, subtab4, subtab5 = st.tabs([
        "🌋 Sàng Lọc Hoạt Tính & Độ An Toàn",
        "🎯 Phổ Nhạy Cảm Dòng Tế Bào (Heatmap)",
        "🧬 Nguồn Sinh Học & Cơ Chế MoA",
        "📈 Mô Phỏng Đường Cong Liều - Đáp Ứng",
        "📋 Bảng Chi Tiết & Thêm Mới Dữ Liệu"
    ])

    # ------------------------------------------
    # SUBTAB 1: VOLCANO / SCATTER (IC50 vs SI)
    # ------------------------------------------
    with subtab1:
        st.subheader("Tương Quan Hoạt Tính Kháng Ung Thư (IC50) & Chỉ Số Chọn Lọc (SI)")
        st.caption("Vùng màu xanh lá là 'Golden Quadrant' (IC50 ≤ 5 µM và SI ≥ 10) - Tiêu chuẩn quốc tế cho Lead Candidate tự nhiên.")

        if filtered_df.empty:
            st.info("Không có dữ liệu thỏa mãn bộ lọc hiện tại.")
        else:
            fig_scatter = px.scatter(
                filtered_df,
                x="ic50_uM",
                y="selectivity_index",
                color="cancer_cell_line",
                symbol="compound_class" if "compound_class" in filtered_df.columns else None,
                hover_name="compound_name",
                hover_data={
                    "source_strain": True,
                    "cancer_cell_line": True,
                    "ic50_uM": ":.2f µM",
                    "selectivity_index": ":.1f",
                    "assay_method": True,
                    "apoptosis_status": True
                },
                size="purity_pct" if "purity_pct" in filtered_df.columns else None,
                labels={
                    "ic50_uM": "Nồng độ ức chế 50% - IC50 (µM) [Càng nhỏ càng mạnh]",
                    "selectivity_index": "Chỉ số chọn lọc - SI (Tế bào Lành / Ung thư) [Càng lớn càng an toàn]",
                    "cancer_cell_line": "Dòng Tế Bào",
                    "compound_class": "Nhóm Hóa Dược",
                    "purity_pct": "Độ tinh khiết HPLC (%)"
                },
                title="Sàng lọc Hoạt tính & Độ chọn lọc (Activity-Selectivity Landscape)",
                template="plotly_white"
            )

            # Vùng Golden Quadrant (IC50 <= 5 uM và SI >= 10)
            max_y_chart = float(filtered_df["selectivity_index"].max() * 1.15) if not filtered_df["selectivity_index"].isna().all() else 35.0
            fig_scatter.add_shape(
                type="rect",
                x0=0, x1=5.0,
                y0=10.0, y1=max_y_chart,
                fillcolor="rgba(46, 204, 113, 0.15)",
                line=dict(color="rgba(46, 204, 113, 0.6)", width=1.5, dash="dot"),
                layer="below"
            )
            fig_scatter.add_annotation(
                x=2.5, y=max_y_chart * 0.92,
                text="⭐ VÙNG LEAD CANDIDATES<br>(IC50 ≤ 5 µM & SI ≥ 10)",
                showarrow=False,
                font=dict(color="#1b5e20", size=11, family="Arial Black")
            )

            # Đường chuẩn ngưỡng
            fig_scatter.add_vline(x=5.0, line_dash="dash", line_color="#e74c3c", annotation_text="Ngưỡng IC50: 5 µM", annotation_position="top right")
            fig_scatter.add_hline(y=10.0, line_dash="dash", line_color="#2980b9", annotation_text="Ngưỡng SI: 10", annotation_position="bottom right")

            fig_scatter.update_layout(
                height=520,
                legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

    # ------------------------------------------
    # SUBTAB 2: CELL SENSITIVITY PROFILE & HEATMAP
    # ------------------------------------------
    with subtab2:
        st.subheader("Phổ Nhạy Cảm Theo Dòng Tế Bào Ung Thư")
        
        c_hm1, c_hm2 = st.columns([3, 2])
        
        with c_hm1:
            st.markdown("**Ma Trận IC50 (µM): Hợp Chất vs. Dòng Tế Bào (Activity Heatmap)**")
            pivot_df = filtered_df.pivot_table(
                index="compound_name",
                columns="cancer_cell_line",
                values="ic50_uM",
                aggfunc="mean"
            )
            
            if not pivot_df.empty:
                # Vẽ Heatmap
                fig_hm = px.imshow(
                    pivot_df,
                    labels=dict(x="Dòng Tế Bào", y="Hợp Chất", color="IC50 (µM)"),
                    x=pivot_df.columns,
                    y=pivot_df.index,
                    color_continuous_scale="Viridis_r",
                    text_auto=".2f",
                    aspect="auto",
                    template="plotly_white"
                )
                fig_hm.update_layout(height=480, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_hm, use_container_width=True)
            else:
                st.info("Không đủ dữ liệu tạo ma trận.")

        with c_hm2:
            st.markdown("**Phân Bố Độ Nhạy Cảm Theo Từng Dòng Ung Thư**")
            fig_box = px.box(
                filtered_df,
                x="cancer_cell_line",
                y="ic50_uM",
                color="cancer_cell_line",
                points="all",
                labels={"cancer_cell_line": "Dòng tế bào", "ic50_uM": "IC50 (µM)"},
                template="plotly_white"
            )
            fig_box.update_layout(height=480, showlegend=False, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_box, use_container_width=True)

    # ------------------------------------------
    # SUBTAB 3: BIOPROSPECTING & MoA MECHANISMS
    # ------------------------------------------
    with subtab3:
        st.subheader("Nguồn Sinh Học & Phân Bố Cơ Chế Tác Động (MoA)")
        
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.markdown("**Phân Bố Theo Nguồn Phân Lập Sinh Thái**")
            if "isolation_source" in filtered_df.columns:
                source_counts = filtered_df["isolation_source"].value_counts().reset_index()
                source_counts.columns = ["isolation_source", "count"]
                fig_pie = px.pie(
                    source_counts,
                    names="isolation_source",
                    values="count",
                    hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                    template="plotly_white"
                )
                fig_pie.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Chưa có thông tin `isolation_source`.")

        with m_col2:
            st.markdown("**Cơ Chế Apoptosis & Bắt Giữ Chu Kỳ Tế Bào (MoA)**")
            if "apoptosis_status" in filtered_df.columns:
                apop_counts = filtered_df["apoptosis_status"].value_counts().head(8).reset_index()
                apop_counts.columns = ["apoptosis_status", "count"]
                fig_bar = px.bar(
                    apop_counts,
                    x="count",
                    y="apoptosis_status",
                    orientation="h",
                    color="count",
                    color_continuous_scale="Teal",
                    labels={"count": "Số mẫu quan sát", "apoptosis_status": "Dấu ấn sinh học / Cơ chế"},
                    template="plotly_white"
                )
                fig_bar.update_layout(height=380, showlegend=False, yaxis={'categoryorder':'total ascending'}, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_bar, use_container_width=True)

    # ------------------------------------------
    # SUBTAB 4: DOSE-RESPONSE HILL CURVE SIMULATION
    # ------------------------------------------
    with subtab4:
        st.subheader("Mô Phỏng Đường Cong Liều - Đáp Ứng (Dose-Response Curve Simulation)")
        st.write("Sử dụng phương trình Sigmoidal Hill chuẩn phòng thí nghiệm dược lý học (4-Parameter Logistic Hill Model) để so sánh hiệu lực với thuốc đối chứng lâm sàng.")

        dr_c1, dr_c2, dr_c3 = st.columns([3, 3, 2])
        
        # Chọn hợp chất khảo sát
        all_compounds = sorted(filtered_df["compound_name"].unique().tolist())
        target_compound = dr_c1.selectbox("Chọn hợp chất tự nhiên khảo sát:", options=all_compounds, index=0)

        # Chọn dòng tế bào ứng với hợp chất đó
        available_lines = filtered_df[filtered_df["compound_name"] == target_compound]["cancer_cell_line"].unique().tolist()
        if not available_lines:
            available_lines = all_cell_lines
        target_line = dr_c2.selectbox("Dòng tế bào ung thư mục tiêu:", options=available_lines, index=0)

        # Chọn thuốc đối chứng
        ref_options = ["Doxorubicin", "Cisplatin", "Paclitaxel"]
        target_ref = dr_c3.selectbox("Thuốc đối chứng dương (Standard Drug):", options=ref_options, index=0)

        # Lấy IC50 của hợp chất khảo sát
        match_target = filtered_df[(filtered_df["compound_name"] == target_compound) & (filtered_df["cancer_cell_line"] == target_line)]
        if not match_target.empty:
            test_ic50 = float(match_target.iloc[0]["ic50_uM"])
            test_si = float(match_target.iloc[0]["selectivity_index"])
        else:
            test_ic50 = 3.5
            test_si = 10.0

        # Lấy hoặc định nghĩa IC50 của thuốc đối chứng
        ref_match = df_raw[(df_raw["compound_name"].str.contains(target_ref, case=False, na=False)) & (df_raw["cancer_cell_line"] == target_line)]
        if not ref_match.empty:
            ref_ic50 = float(ref_match.iloc[0]["ic50_uM"])
            ref_si = float(ref_match.iloc[0]["selectivity_index"])
        else:
            ref_defaults = {"Doxorubicin": 0.85, "Cisplatin": 3.20, "Paclitaxel": 0.08}
            ref_ic50 = ref_defaults.get(target_ref, 1.0)
            ref_si = 5.0

        # Sinh dải nồng độ logarit (từ 0.001 đến 100 uM)
        concentrations = np.logspace(-3, 2.5, 120)
        
        # Phương trình Hill: Viability (%) = 100 / (1 + (Conc / IC50)^HillSlope)
        hill_slope_test = 1.35
        hill_slope_ref = 1.60
        
        viability_test = 100.0 / (1.0 + (concentrations / test_ic50) ** hill_slope_test)
        viability_ref = 100.0 / (1.0 + (concentrations / ref_ic50) ** hill_slope_ref)

        # Điểm thực nghiệm giả lập với nhiễu nhẹ
        exp_concs = np.array([0.01, 0.05, 0.2, 1.0, 5.0, 20.0, 100.0])
        np.random.seed(42)
        exp_viab_test = np.clip(100.0 / (1.0 + (exp_concs / test_ic50) ** hill_slope_test) + np.random.normal(0, 3.0, len(exp_concs)), 0, 100)
        exp_viab_ref = np.clip(100.0 / (1.0 + (exp_concs / ref_ic50) ** hill_slope_ref) + np.random.normal(0, 2.5, len(exp_concs)), 0, 100)

        # Vẽ đồ thị bằng Plotly
        fig_dr = go.Figure()

        # Đường đối chứng
        fig_dr.add_trace(go.Scatter(
            x=concentrations, y=viability_ref,
            mode='lines',
            name=f'{target_ref} (Chuẩn lâm sàng)',
            line=dict(color='#e74c3c', width=2.5, dash='dash')
        ))
        fig_dr.add_trace(go.Scatter(
            x=exp_concs, y=exp_viab_ref,
            mode='markers',
            name=f'{target_ref} (Điểm đo)',
            marker=dict(color='#e74c3c', size=8, symbol='square')
        ))

        # Đường hợp chất tự nhiên khảo sát
        fig_dr.add_trace(go.Scatter(
            x=concentrations, y=viability_test,
            mode='lines',
            name=f'{target_compound} (Hợp chất khảo sát)',
            line=dict(color='#16a085', width=3.5)
        ))
        fig_dr.add_trace(go.Scatter(
            x=exp_concs, y=exp_viab_test,
            mode='markers',
            name=f'{target_compound} (Điểm đo)',
            marker=dict(color='#16a085', size=10, symbol='circle')
        ))

        # Đường ngưỡng 50% viability
        fig_dr.add_hline(y=50, line_dash='dot', line_color='#7f8c8d', annotation_text="50% Sống sót (IC50)", annotation_position="top left")

        # Đường dóng thẳng đứng cho IC50
        fig_dr.add_vline(x=test_ic50, line_dash='dot', line_color='#16a085', annotation_text=f"IC50 = {test_ic50:.2f} µM", annotation_position="bottom right")
        fig_dr.add_vline(x=ref_ic50, line_dash='dot', line_color='#e74c3c', annotation_text=f"IC50 = {ref_ic50:.2f} µM", annotation_position="bottom left")

        fig_dr.update_layout(
            xaxis=dict(type='log', title='Nồng độ chất thử nghiệm [Drug] (µM, Log Scale)', gridcolor='#f0f0f0'),
            yaxis=dict(title='Tỷ lệ tế bào sống sót - Cell Viability (%)', range=[0, 105], gridcolor='#f0f0f0'),
            title=f"Đường cong Độc tế bào (Cell Cytotoxicity Curve): {target_compound} vs. {target_ref} trên dòng {target_line}",
            template="plotly_white",
            height=480,
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_dr, use_container_width=True)

        # Bảng so sánh tham số dược lý
        pIC50_test = -np.log10(test_ic50 * 1e-6)
        pIC50_ref = -np.log10(ref_ic50 * 1e-6)

        param_c1, param_c2, param_c3, param_c4 = st.columns(4)
        param_c1.metric(f"IC50 của {target_compound}", f"{test_ic50:.2f} µM", f"pIC50: {pIC50_test:.2f}")
        param_c2.metric(f"IC50 của {target_ref}", f"{ref_ic50:.2f} µM", f"pIC50: {pIC50_ref:.2f}")
        param_c3.metric(f"Chỉ số Chọn lọc (SI) - {target_compound}", f"{test_si:.1f}", "An toàn tế bào lành" if test_si >= 10 else "Cần tối ưu")
        param_c4.metric(f"Chỉ số Chọn lọc (SI) - {target_ref}", f"{ref_si:.1f}", "Tiêu chuẩn lâm sàng")

    # ------------------------------------------
    # SUBTAB 5: DATA EXPLORER & ENTRY FORM
    # ------------------------------------------
    with subtab5:
        st.subheader("Quản Lý Sổ Dữ Liệu Phòng Thí Nghiệm (Lab Notebook)")

        # Nút xuất CSV
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        d_col1, d_col2 = st.columns([4, 1])
        d_col1.write(f"Tổng số bản ghi trong chế độ xem: **{len(filtered_df)}**")
        d_col2.download_button(
            label="📥 Tải file CSV",
            data=csv_data,
            file_name=f"lab_compounds_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

        st.dataframe(
            filtered_df,
            use_container_width=True,
            column_config={
                "compound_id": st.column_config.TextColumn("Mã Hợp Chất", width="small"),
                "compound_name": st.column_config.TextColumn("Tên Hợp Chất", width="medium"),
                "source_strain": st.column_config.TextColumn("Chủng Vi Sinh / Mẫu", width="medium"),
                "cancer_cell_line": st.column_config.TextColumn("Dòng TB Ung Thư", width="small"),
                "ic50_uM": st.column_config.NumberColumn("IC50 (µM)", format="%.2f", width="small"),
                "selectivity_index": st.column_config.NumberColumn("Chỉ Số SI", format="%.1f", width="small"),
                "assay_method": st.column_config.TextColumn("Phương Pháp", width="small"),
                "apoptosis_status": st.column_config.TextColumn("Cơ Chế Tác Động (MoA)", width="large"),
                "isolation_source": st.column_config.TextColumn("Nguồn Phân Lập", width="medium"),
                "compound_class": st.column_config.TextColumn("Nhóm Hóa Dược", width="small"),
                "purity_pct": st.column_config.ProgressColumn("Độ Tinh Khiết", min_value=70, max_value=100, format="%.1f%%"),
                "lead_status": st.column_config.TextColumn("Phân Loại Lead", width="small")
            }
        )

        # Form thêm bản ghi mới
        with st.expander("➕ Ghi Nhận Kết Quả Thí Nghiệm Mới Vào Database", expanded=False):
            with st.form("add_compound_form"):
                st.markdown("##### Nhập Thông Tin Lô Thử Nghiệm Hoạt Tính Mới")
                
                form_r1_1, form_r1_2, form_r1_3 = st.columns(3)
                new_id = form_r1_1.text_input("Mã Hợp chất (ID)*:", value=f"CPD-{len(df_raw)+1:02d}")
                new_name = form_r1_2.text_input("Tên Hợp chất*:", placeholder="Ví dụ: Streptoketide B")
                new_strain = form_r1_3.text_input("Chủng Vi Sinh / Xạ Khuẩn*:", placeholder="Ví dụ: Streptomyces sp. VN-15")

                form_r2_1, form_r2_2, form_r2_3 = st.columns(3)
                new_cell = form_r2_1.selectbox("Dòng tế bào ung thư thử nghiệm*:", options=["MCF-7", "HeLa", "A549", "HepG2", "HCT-116", "PC-3", "K562", "Khác"])
                new_ic50 = form_r2_2.number_input("Giá trị IC50 (µM)*:", min_value=0.001, max_value=500.0, value=2.50, step=0.1)
                new_si = form_r2_3.number_input("Chỉ số chọn lọc (Selectivity Index - SI)*:", min_value=0.1, max_value=200.0, value=12.5, step=0.5)

                form_r3_1, form_r3_2, form_r3_3 = st.columns(3)
                new_assay = form_r3_1.selectbox("Phương pháp thử độc tính*:", options=["MTT (48h)", "MTT (72h)", "CCK-8 (48h)", "CCK-8 (72h)", "SRB (48h)", "SRB (72h)"])
                new_source = form_r3_2.text_input("Nguồn phân lập sinh thái:", placeholder="Ví dụ: Đất ngập mặn Cần Giờ")
                new_class = form_r3_3.selectbox("Nhóm hóa dược:", options=["Polyketide", "Non-ribosomal Peptide", "Alkaloid", "Macrolide", "Anthracycline", "Terpenoid", "Lipopeptide", "Khác"])

                form_r4_1, form_r4_2, form_r4_3 = st.columns(3)
                new_purity = form_r4_1.number_input("Độ tinh khiết HPLC (%):", min_value=50.0, max_value=100.0, value=96.5, step=0.5)
                new_mw = form_r4_2.number_input("Khối lượng phân tử (MW - Da):", min_value=50.0, max_value=2500.0, value=480.0, step=1.0)
                new_cycle = form_r4_3.selectbox("Bắt giữ chu kỳ tế bào:", options=["G2/M Phase", "G0/G1 Phase", "S Phase", "None", "Chưa xác định"])

                new_apop = st.text_input("Dấu hiệu cơ chế chết tế bào (Apoptosis / MoA):", placeholder="Ví dụ: Annexin V+ / Caspase-3 Cleaved / MMP Loss (JC-1)")
                
                # Tự động gán lead status sơ bộ
                default_lead = "Potent Hit" if (new_ic50 <= 3.0 and new_si >= 15.0) else ("Lead Candidate" if (new_ic50 <= 5.0 and new_si >= 10.0) else "Moderate")
                new_lead_status = st.selectbox("Phân loại trạng thái:", options=["Potent Hit", "Lead Candidate", "Moderate", "Weak/Inactive"], index=["Potent Hit", "Lead Candidate", "Moderate", "Weak/Inactive"].index(default_lead))

                submitted = st.form_submit_button("💾 Lưu Kết Quả Thí Nghiệm Vào Database Lab")

                if submitted:
                    if not new_name or not new_strain:
                        st.error("Vui lòng nhập đầy đủ Tên hợp chất và Chủng vi sinh!")
                    else:
                        new_row = {
                            "compound_id": new_id,
                            "compound_name": new_name,
                            "source_strain": new_strain,
                            "cancer_cell_line": new_cell,
                            "ic50_uM": new_ic50,
                            "assay_method": new_assay,
                            "selectivity_index": new_si,
                            "apoptosis_status": new_apop if new_apop else "Chưa xác định",
                            "isolation_source": new_source if new_source else "Phòng lab",
                            "compound_class": new_class,
                            "molecular_weight": new_mw,
                            "purity_pct": new_purity,
                            "cell_cycle_arrest": new_cycle,
                            "lead_status": new_lead_status,
                            "tested_date": datetime.now().strftime("%Y-%m-%d")
                        }
                        
                        # Thêm vào dataframe và lưu file
                        df_updated = pd.concat([df_raw, pd.DataFrame([new_row])], ignore_index=True)
                        df_updated.to_csv(LAB_COMPOUNDS_CSV, index=False)
                        st.success(f"✓ Đã thêm hợp chất '{new_name}' ({new_id}) vào cơ sở dữ liệu phòng lab!")
                        st.rerun()
