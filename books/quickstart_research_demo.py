"""
Jupyter / Interactive Python Script: Demo Khai Phá Dữ Liệu và Soạn Thảo Paper.
Có thể chạy trực tiếp bằng python hoặc mở dưới dạng Interactive Window / Notebook.
"""

import sys
from pathlib import Path

# Đảm bảo in tiếng Việt chuẩn trên Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Đảm bảo import được src từ thư mục gốc
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.agent.assistant import ScientificResearchAssistant
from src.writer.paper_generator import PaperMetadata

def main():
    print("=== DEMO KHAI THÁC DỮ LIỆU & RAG TRONG BOOKS ===")
    assistant = ScientificResearchAssistant()

    # 1. Tra cứu hợp chất mẫu
    print("\n[1] Tra cứu PubChem & Lipinski cho Staurosporine...")
    report = assistant.analyze_chemical_compound("Staurosporine")
    if report:
        print(f"  - Khối lượng: {report.molecular_weight} Da")
        print(f"  - XLogP: {report.xlogp}")
        print(f"  - Vi phạm Lipinski: {report.lipinski_violations}")
        print(f"  - Đánh giá: {report.summary_verdict}")

    # 2. Truy vấn kho RAG
    print("\n[2] Truy vấn kho RAG về cơ chế Caspase-3...")
    hits = assistant.query_rag("Caspase-3 apoptosis mitochondrial", top_k=2)
    for h in hits:
        print(f"  - [Rank #{h['rank']}] Điểm RRF: {h['rrf_score']} | {h['content'][:120]}...")

    print("\n✓ Hoàn thành demo. Bạn có thể tạo thêm các file .ipynb trong thư mục này!")

if __name__ == "__main__":
    main()
