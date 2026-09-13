"""
Cấu hình trung tâm cho hệ sinh thái Nghiên cứu Sinh dược học Kháng Ung thư.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Thư mục dữ liệu
DATA_DIR = BASE_DIR / "data"
RAW_PAPERS_DIR = DATA_DIR / "raw_papers"
VECTOR_DB_DIR = DATA_DIR / "vector_db"
OUTPUT_DIR = BASE_DIR / "outputs"

# Đảm bảo các thư mục luôn tồn tại
for path in [DATA_DIR, RAW_PAPERS_DIR, VECTOR_DB_DIR, OUTPUT_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# Tệp dữ liệu mẫu phòng lab
LAB_COMPOUNDS_CSV = DATA_DIR / "lab_compounds.csv"

# Cấu hình API Keys (tùy chọn nếu người dùng sử dụng LLM tạo văn phong)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Cấu hình NCBI Entrez API (tùy chọn thêm email để tăng rate limit từ 3 lên 10 req/s)
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "researcher@biotech-lab.org")
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")

# ChromaDB Collection
DEFAULT_COLLECTION_NAME = "cancer_bacteria_research"
