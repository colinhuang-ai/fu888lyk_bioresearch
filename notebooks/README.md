# Thư Mục Jupyter Notebooks / Python Books 📓

Thư mục này dành cho việc lưu trữ và thực thi các cuốn sổ tay phân tích dữ liệu (**Jupyter Notebooks** `.ipynb` hoặc Python scripts) phục vụ nghiên cứu vi sinh & kháng ung thư.

---

## 🔬 Các Module Sẵn Sàng Nhập (Import) Vào Notebook

Bạn có thể dễ dàng gọi toàn bộ công cụ của dự án trong Jupyter Notebook:

```python
import sys
from pathlib import Path

# Thêm thư mục gốc vào PYTHONPATH nếu cần
ROOT_DIR = Path.cwd().parent if Path.cwd().name == "books" else Path.cwd()
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# 1. Trợ lý AI toàn diện
from app.agent.assistant import ScientificResearchAssistant

assistant = ScientificResearchAssistant()

# 2. Tìm kiếm bài báo & nạp vào RAG
articles = assistant.search_and_index_pubmed(query="Streptomyces apoptosis IC50", max_results=5)
for a in articles:
    print(f"[{a.pmid}] {a.title} ({a.journal})")

# 3. Phân tích cấu trúc & quy tắc 5 Lipinski
report = assistant.analyze_chemical_compound("Staurosporine")
print(f"Khối lượng phân tử: {report.molecular_weight} Da | Lipinski: {report.is_lipinski_compliant}")
print("Đoạn văn thảo luận:\n", report.scientific_narrative)

# 4. Truy vấn RAG Hybrid (Vector + BM25)
results = assistant.query_rag(query="caspase-3 mitochondrial apoptosis", top_k=3)
for r in results:
    print(r["rank"], r["rrf_score"], r["content"][:100])

# 5. Soạn thảo bài báo và xuất Word (.docx)
from app.tools.writer.paper_generator import PaperMetadata

meta = PaperMetadata(
    title="",
    authors=["Linh Nguyen", "Minh Tran"],
    affiliations=["Biotechnology Department"],
    target_journal="Journal of Natural Products",
    bacterial_strain="Streptomyces sp. VN-08",
    isolation_source="Marine sediment",
    compound_name="Streptoketide A",
    target_cancer_cells=["MCF-7", "HeLa"],
    measured_ic50="3.45 ± 0.28 μM",
    observed_mechanisms=["Apoptosis via mitochondrial pathway", "Caspase-3 activation"]
)
manuscript = assistant.write_full_paper(meta=meta)
print("File Word đã xuất:", manuscript.docx_file_path)
```

---

## 📚 Danh Sách Các Notebook Trong Thư Mục

1. [01_anticancer_discovery_pipeline.ipynb](01_anticancer_discovery_pipeline.ipynb) — **Từ Vi Khuẩn Biển Đến Bản Thảo ISI**: Quy trình toàn diện 8 chương từ thu thập tài liệu PubMed, nạp kho RAG Hybrid, kiểm tra hóa dược Lipinski, phân tích thực nghiệm và xuất file Word `.docx`.
2. [02_visualize_lab_compounds.ipynb](02_visualize_lab_compounds.ipynb) — **Phân Tích & Trực Quan Hóa Dữ Liệu Lab Compounds**: Khai phá chuyên sâu 10 chương toàn bộ số liệu sàng lọc độc tế bào `data/lab_compounds.csv` với 7 biểu đồ khoa học chuẩn mực quốc tế (Heatmap, Activity-Selectivity Landscape, Boxplot, Cell Cycle Donut, Dose-Response Curves, Radar Optimization Chart).

---

## 💡 Gợi Ý Các Notebook Nghiên Cứu Mở Rộng:
1. `03_dose_response_ic50_curve.ipynb`: Vẽ đường cong liều - đáp ứng (Dose-response curve) tính $\text{IC}_{50}$ từ số liệu đo OD quang phổ kế.
2. `04_manuscript_drafting_pipeline.ipynb`: Tự động hóa tạo bản thảo bài báo theo mẻ.

