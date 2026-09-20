"""
Web Application: Trợ lý AI Nghiên cứu Dược liệu Vi sinh & Soạn thảo Bài báo Quốc tế.
Chạy bằng lệnh: streamlit run app.py
"""

# uikit dành cho python web app, giúp tạo giao diện đẹp và trực quan
import streamlit as st

from app.agent.assistant import ScientificResearchAssistant
from views import sidebar, tab_chemistry, tab_collect, tab_lab, tab_rag, tab_writer

# Cấu hình Streamlit
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

sidebar.render(assistant)

# Tabs giao diện chính, là 1 mảng
# config (biến dùng cho cấu hình)
TABS = [
    ("🔍 1. Thu Thập Bài Báo (PubMed / PMC)", tab_collect),
    ("🧪 2. Tra Cứu Hóa Dược & Lipinski", tab_chemistry),
    ("🧠 3. Kho Tri Thức RAG (Hybrid Search)", tab_rag),
    ("✍️ 4. Xưởng Soạn Thảo Paper Q1/Q2", tab_writer),
    ("📊 5. Dữ Liệu Phòng Lab", tab_lab),
    ("⚙️ 6. Cấu Hình & Hướng Dẫn", sidebar)
]

# Lấy danh sách nhãn để tạo thanh tab
tab_labels = []
for label, module in TABS:
    tab_labels.append(label)

# st.tabs() trả về các khung tab theo đúng thứ tự nhãn ở trên
tab_containers = st.tabs(tab_labels)

# Vẽ nội dung từng tab bằng module tương ứng
for index in range(len(TABS)):
    label, module = TABS[index]
    container = tab_containers[index]
    with container:
        # vẽ nội dung của module tương ứng
        module.render(assistant)
