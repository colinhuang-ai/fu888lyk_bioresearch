"""Tab 5: Dữ liệu thực nghiệm phòng lab."""

import pandas as pd
import streamlit as st

from app.config import LAB_COMPOUNDS_CSV


def render(assistant=None):
    st.header("Quản Lý Dữ Liệu Thực Nghiệm Phòng Lab")
    st.write("Bảng ghi nhận các chủng vi khuẩn, phân đoạn hoạt tính và giá trị IC50 đã thử nghiệm.")

    if LAB_COMPOUNDS_CSV.exists():
        df = pd.read_csv(LAB_COMPOUNDS_CSV)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Chưa có file lab_compounds.csv.")
