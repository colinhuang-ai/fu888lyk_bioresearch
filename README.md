# Bio-Cancer Research Assistant & Paper Writing Studio 🧬

Hệ thống AI & Công cụ Tin sinh/Hóa dược hỗ trợ nhà nghiên cứu thu thập bài báo về **vi khuẩn sinh chất hoạt tính**, **cơ chế phân tử kháng ung thư (Apoptosis, Caspase, ROS, Chu kỳ tế bào)** và **hỗ trợ soạn thảo bài báo khoa học chuẩn ISI/Scopus (Q1/Q2)**.

Dựa trên giáo trình và kiến trúc chuẩn tại: [`research_syllabus_and_rag_blueprint.md`](research_syllabus_and_rag_blueprint.md)

---

## 🌟 Các Tính Năng Cốt Lõi

1. **Thu Thập Bài Báo Tự Động (Literature Mining)**:
   - Tích hợp trực tiếp **NCBI PubMed API (E-Utilities)** để lấy các công trình mới nhất theo từ khóa vi khuẩn (*Streptomyces*, *Bacillus*, xạ khuẩn biển) và đích ung thư (*MCF-7, HeLa, A549, HepG2, Caspase-3, Apoptosis*).
   - Tích hợp **Europe PMC API** hỗ trợ định danh và tải bài báo Open Access PDF trực tiếp về máy.
2. **Kho Tri Thức RAG Hybrid (ChromaDB + BM25)**:
   - Kết hợp Dense Semantic Vector (ChromaDB) và Sparse Keyword Indexing (BM25Okapi).
   - Thuật toán **Reciprocal Rank Fusion (RRF)** giúp truy xuất chính xác từng danh pháp vi sinh, mã hợp chất, gen và dòng tế bào.
   - Hỗ trợ nạp file PDF nội bộ của phòng lab bằng bộ parser chuyên dụng (`pypdfium2`).
3. **Phân Tích Hóa Dược & Tính Toán ADMET (PubChem & Lipinski)**:
   - Tra cứu cấu trúc 2D, CID, Canonical SMILES, IUPAC qua PubChem PUG REST.
   - Đánh giá **Quy tắc 5 Lipinski (Rule of 5)**: Khối lượng phân tử ($MW \le 500$), $XLogP \le 5$, số liên kết cho/nhận hydro ($HBD \le 5$, $HBA \le 10$) và tiêu chuẩn Veber ($Rotatable\ bonds \le 10$).
   - Tự động sinh đoạn văn học thuật đánh giá độ tương đồng thuốc (*druglikeness narrative*) để đưa vào mục Discussion.
4. **Xưởng Soạn Thảo Bài Báo Khoa Học (Paper Writing Studio)**:
   - Tạo cấu trúc chuẩn các tạp chí chuyên ngành Q1/Q2 (*Journal of Natural Products, European Journal of Medicinal Chemistry, Bioorganic Chemistry*).
   - Soạn thảo đầy đủ: **Title, Abstract, 1. Introduction, 2. Results and Discussion, 3. Experimental Section, 4. Conclusion, References**.
   - Tự động tích hợp bảng dữ liệu thử nghiệm độc tính sinh học ($\text{IC}_{50}$, Selectivity Index) và bảng thông số Lipinski.
   - **Xuất trực tiếp ra file Microsoft Word (.docx)** với định dạng chuẩn mực (Times New Roman 12pt, lề 1 inch) và file Markdown (.md).

---

## 📂 Cấu Trúc Codebase

```text
anti-cancer-research/
├── data/
│   ├── raw_papers/            # Chứa các file PDF bài báo khoa học
│   ├── vector_db/             # ChromaDB persistent vector storage
│   └── lab_compounds.csv      # Bảng dữ liệu hoạt tính sinh học phòng lab
├── src/
│   ├── fetchers/              # Module thu thập dữ liệu (PubMed & Europe PMC)
│   ├── ingestion/             # Module đọc PDF (pypdfium2) & chia đoạn ngữ nghĩa
│   ├── chemistry/             # Module hóa dược (PubChem & Lipinski Rule of 5)
│   ├── rag/                   # Lõi Hybrid RAG (ChromaDB + BM25 + RRF)
│   ├── writer/                # Bộ máy soạn thảo paper & xuất Microsoft Word (.docx)
│   └── agent/                 # Lớp điều phối tổng thể (ScientificResearchAssistant)
├── outputs/                   # Nơi lưu các bản thảo bài báo (.docx & .md) được sinh ra
├── tests/                     # Bộ kiểm thử tự động
├── app.py                     # Giao diện Web trực quan (Streamlit Dashboard)
├── main.py                    # Giao diện dòng lệnh (Interactive CLI)
├── requirements.txt           # Danh mục thư viện Python
└── research_syllabus_and_rag_blueprint.md  # Giáo trình & thiết kế kiến trúc chuẩn
```

---

## 🚀 Hướng Dẫn Khởi Chạy

### 1. Khởi chạy Giao diện Web Trực quan (Khuyên dùng)
Giao diện Web thân thiện, hỗ trợ đầy đủ các tab trực quan:
```bash
streamlit run app.py
```
Trình duyệt sẽ tự động mở tại: `http://localhost:8501`. Tại đây bạn có thể:
- Tìm kiếm và tải bài báo từ PubMed vào RAG chỉ với 1 click.
- Tra cứu cấu trúc hóa học và ảnh 2D từ PubChem.
- Điền thông tin chủng vi khuẩn và số liệu $\text{IC}_{50} \rightarrow$ Bấm nút để tải ngay bản thảo Word `.docx`.

### 2. Khởi chạy Giao diện Dòng lệnh (CLI Runner)
Chạy menu dòng lệnh tương tác trực tiếp trong Terminal:
```bash
python main.py
```

### 3. Chạy Kiểm thử Toàn diện
```bash
python -m unittest tests/test_pipeline.py
```

---

## 💡 Tùy Chọn Cấu Hình Nâng Cao (.env)

Tạo file `.env` nếu bạn muốn tích hợp OpenAI API (tùy chọn, hệ thống vẫn hoạt động hoàn hảo ở chế độ offline):
```env
OPENAI_API_KEY=your_api_key_here
LLM_MODEL=gpt-4o-mini
NCBI_EMAIL=researcher@university.edu.vn
```
