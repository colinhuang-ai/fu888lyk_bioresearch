"""Script CLI tự động phân tích và tạo báo cáo nghiên cứu Protein toàn diện (Markdown + HTML)."""

import argparse
import os
import sys
import matplotlib.pyplot as plt
import pandas as pd

# ==============================================================================
# UNIT OF WORK 1: KHỞI TẠO MÔI TRƯỜNG & THIẾT LẬP MÃ HÓA (ENCODING SETUP)
# Mục đích: Đảm bảo tương thích với console Windows, tránh lỗi UnicodeEncodeError
# khi in các ký tự đặc biệt hoặc tiếng Việt có dấu.
# ==============================================================================
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Import các module chức năng chuyên biệt trong hệ sinh thái
from pubmed_client import PubMedClient
from protein_client import ProteinClient
from analyzer import ProteinLiteratureAnalyzer
import visualizer


def generate_full_report(
    protein_query: str,
    max_articles: int = 30,
    output_dir: str = "./reports"
):
    """Hàm trung tâm điều phối toàn bộ quy trình nghiên cứu protein."""

    # ==============================================================================
    # UNIT OF WORK 2: CHUẨN BỊ THƯ MỤC VÀ ĐỊNH DANH ĐỐI TƯỢNG (TARGET INITIALIZATION)
    # Mục đích:
    # 1. Tạo thư mục đích để lưu trữ các biểu đồ và báo cáo đầu ra.
    # 2. Làm sạch tên protein (loại bỏ ký tự lạ) để dùng an toàn cho tên file.
    # ==============================================================================
    os.makedirs(output_dir, exist_ok=True)
    clean_name = "".join(c for c in protein_query if c.isalnum() or c in ("-", "_"))

    print(f"\n=======================================================")
    print(f"[+] BAT DAU NGHIEN CUU PROTEIN: {protein_query}")
    print(f"=======================================================")

    # ==============================================================================
    # UNIT OF WORK 3: TRUY VẤN UNIPROT VÀ CẤU TRÚC 3D PDB (PROTEIN & 3D METADATA QUERY)
    # Mục đích:
    # 1. Tra cứu UniProt KB để lấy: tên chính thức, gene, chức năng phân tử chuẩn,
    #    các đường truyền tín hiệu (pathways) và bệnh liên quan.
    # 2. Tìm mã PDB ID (RCSB Protein Data Bank) có cấu trúc thực nghiệm tốt nhất
    #    (ưu tiên X-ray diffraction độ phân giải cao).
    # ==============================================================================
    print("\n[1/4] Đang lấy thông tin chức năng & cấu trúc từ UniProt & RCSB PDB...")
    prot_client = ProteinClient()
    uniprot_data = prot_client.search_uniprot(protein_query)

    if not uniprot_data:
        print(f"  [!] Khong tim thay thong tin UniProt cho '{protein_query}'. Su dung thong tin mac dinh.")
        uniprot_data = {
            "accession": "N/A",
            "protein_name": protein_query,
            "genes": [protein_query],
            "organism": "Homo sapiens",
            "function": "Không có mô tả chức năng từ UniProt.",
            "pathways": [],
            "diseases": [],
            "pharmaceuticals": [],
            "best_pdb_id": "1IVO"  # fallback mẫu cấu trúc
        }
    else:
        print(f"  [+] Tim thay: {uniprot_data['protein_name']} (UniProt: {uniprot_data['accession']})")
        print(f"  [+] Sinh vat: {uniprot_data['organism']}")
        print(f"  [+] Best PDB ID: {uniprot_data.get('best_pdb_id')}")

    best_pdb = uniprot_data.get("best_pdb_id") or "1IVO"

    # ==============================================================================
    # UNIT OF WORK 4: KÉO DỮ LIỆU Y VĂN TỪ PUBMED (PUBMED DATA INGESTION)
    # Mục đích:
    # 1. Gọi NCBI E-Utilities API (esearch.fcgi) để tìm danh sách các PMID mới nhất.
    # 2. Gọi efetch.fcgi để tải chi tiết: Title, Abstract, Journal, Year, Authors, DOI.
    # 3. Trả về cấu trúc bảng Pandas DataFrame để phục vụ khai phá dữ liệu.
    # ==============================================================================
    print(f"\n[2/4] Dang keo {max_articles} bai bao nghien cuu tu PubMed...")
    pubmed_client = PubMedClient()
    df_articles = pubmed_client.search_protein(protein_query, max_results=max_articles)
    print(f"  [+] Da tai thanh cong {len(df_articles)} bai bao kem Abstracts.")

    # ==============================================================================
    # UNIT OF WORK 5: KHAI PHÁ VĂN BẢN VÀ BẰNG CHỨNG (NLP & TEXT-MINING)
    # Mục đích:
    # 1. Quét tần suất từ khóa về Cách thức hoạt động phân tử (inhibition, phosphorylation,...).
    # 2. Quét tần suất từ khóa về Hiệu ứng phụ & Độc tính (hepatotoxicity, rash, resistance,...).
    # 3. Trích xuất các câu văn cụ thể trong abstract chứa bằng chứng khoa học có kèm PMID.
    # ==============================================================================
    print("\n[3/4] Dang phan tich co che hoat dong va hieu ung phu tu Abstracts...")
    analyzer = ProteinLiteratureAnalyzer()
    findings = analyzer.summarize_findings(df_articles)

    print(f"  [+] Top tac dung phu: {[t[0] for t in findings['top_side_effects'][:5]]}")
    print(f"  [+] Top co che: {[t[0] for t in findings['top_mechanisms'][:5]]}")

    # ==============================================================================
    # UNIT OF WORK 6: TRỰC QUAN HÓA DỮ LIỆU & VẼ BIỂU ĐỒ (DATA VISUALIZATION)
    # Mục đích:
    # 1. Vẽ biểu đồ ngang tần suất các tác dụng phụ / độc tính (Seaborn + Matplotlib).
    # 2. Vẽ biểu đồ ngang phân loại cơ chế hoạt động phân tử.
    # 3. Vẽ biểu đồ cột xu hướng xuất bản bài báo theo từng năm.
    # 4. Xuất các biểu đồ thành các file ảnh PNG chất lượng cao (dpi=200).
    # ==============================================================================
    print("\n[4/4] Dang ve bieu do phan tich va xuat bao cao...")
    chart_files = {}

    # 6.1 Biểu đồ tác dụng phụ
    fig, ax = plt.subplots(figsize=(8, 4.5))
    visualizer.plot_side_effects_chart(findings["top_side_effects"], protein_query, ax=ax)
    se_chart_path = os.path.join(output_dir, f"{clean_name}_side_effects.png")
    fig.savefig(se_chart_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    chart_files["side_effects"] = os.path.basename(se_chart_path)

    # 6.2 Biểu đồ cơ chế hoạt động
    fig, ax = plt.subplots(figsize=(8, 4.5))
    visualizer.plot_mechanisms_chart(findings["top_mechanisms"], protein_query, ax=ax)
    mech_chart_path = os.path.join(output_dir, f"{clean_name}_mechanisms.png")
    fig.savefig(mech_chart_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    chart_files["mechanisms"] = os.path.basename(mech_chart_path)

    # 6.3 Biểu đồ số lượng bài báo theo năm
    if findings["publications_by_year"]:
        fig, ax = plt.subplots(figsize=(8, 4))
        visualizer.plot_publications_over_time(findings["publications_by_year"], protein_query, ax=ax)
        pub_chart_path = os.path.join(output_dir, f"{clean_name}_publications.png")
        fig.savefig(pub_chart_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        chart_files["publications"] = os.path.basename(pub_chart_path)

    # ==============================================================================
    # UNIT OF WORK 7: XUẤT DỮ LIỆU BÀI BÁO THÔ RA CSV (RAW DATA EXPORT)
    # Mục đích: Giúp nhà nghiên cứu có thể mở và tra cứu toàn bộ bài báo trên Excel.
    # ==============================================================================
    csv_path = os.path.join(output_dir, f"{clean_name}_pubmed_articles.csv")
    df_articles.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # ==============================================================================
    # UNIT OF WORK 8: TỔNG HỢP BÁO CÁO DẠNG MARKDOWN (MARKDOWN REPORT GENERATION)
    # Mục đích: Tạo tài liệu chuẩn markdown có chèn ảnh biểu đồ, link PubMed,
    # định dạng phù hợp để lưu trữ trong Git, Wiki, hoặc xem trên IDE/Notion.
    # ==============================================================================
    md_report_path = os.path.join(output_dir, f"{clean_name}_report.md")
    with open(md_report_path, "w", encoding="utf-8") as f:
        f.write(f"# BÁO CÁO NGHIÊN CỨU PROTEIN: {protein_query.upper()}\n\n")
        f.write(f"- **Tên chính thức:** {uniprot_data['protein_name']}\n")
        f.write(f"- **Mã UniProt:** [{uniprot_data['accession']}](https://www.uniprot.org/uniprotkb/{uniprot_data['accession']})\n")
        f.write(f"- **Gen:** {', '.join(uniprot_data['genes'])}\n")
        f.write(f"- **Sinh vật:** {uniprot_data['organism']}\n")
        f.write(f"- **Mã cấu trúc 3D (RCSB PDB):** [{best_pdb}](https://www.rcsb.org/structure/{best_pdb})\n\n")

        f.write("## 1. Cách Thức Hoạt Động & Chức Năng Sinh Học\n\n")
        f.write(f"{uniprot_data['function']}\n\n")

        if uniprot_data.get("pathways"):
            f.write("### Các con đường truyền tín hiệu (Pathways):\n")
            for p in uniprot_data["pathways"]:
                f.write(f"- {p}\n")
            f.write("\n")

        f.write("## 2. Phân Tích Cơ Chế Hoạt Động Từ Y Văn (PubMed)\n\n")
        f.write(f"![Cơ chế hoạt động]({chart_files.get('mechanisms')})\n\n")
        f.write("### Dẫn chứng cơ chế từ các nghiên cứu gần nhất:\n")
        for ev in findings["mechanism_evidence"][:4]:
            f.write(f"- **[PMID:{ev['pmid']} - {ev['year']}]**: \"{ev['sentence']}\"\n")
        f.write("\n")

        f.write("## 3. Phân Tích Hiệu Ứng Phụ & Độc Tính (Side Effects & Toxicity)\n\n")
        f.write(f"![Tác dụng phụ]({chart_files.get('side_effects')})\n\n")
        f.write("### Dẫn chứng tác dụng phụ phát hiện trong y văn:\n")
        for ev in findings["side_effect_evidence"][:4]:
            f.write(f"- **[PMID:{ev['pmid']} - {ev['year']}]**: \"{ev['sentence']}\"\n")
        f.write("\n")

        f.write("## 4. Danh Sách Bài Báo Tiêu Biểu\n\n")
        f.write(f"Tổng số bài báo thu thập: **{len(df_articles)}** (Chi tiết lưu trong `{os.path.basename(csv_path)}`).\n\n")
        for _, r in df_articles.head(8).iterrows():
            f.write(f"- **{r['title']}** ({r['year']})\n  *Tạp chí:* {r['journal']} | [PMID:{r['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{r['pmid']}/)\n")

    # ==============================================================================
    # UNIT OF WORK 9: XÂY DỰNG BÁO CÁO HTML TƯƠNG TÁC CÓ NHÚNG 3D VIEWER (INTERACTIVE HTML)
    # Mục đích:
    # 1. Tạo giao diện Web hiện đại (Dark theme).
    # 2. Tích hợp thư viện 3Dmol.js qua CDN để render cấu trúc 3D trực tiếp trong trình duyệt,
    #    cho phép xoay, phóng to, thu nhỏ mô hình protein bằng chuột.
    # 3. Trình bày song song: Khung 3D | Mô tả chức năng | Biểu đồ cơ chế & Tác dụng phụ.
    # ==============================================================================
    html_report_path = os.path.join(output_dir, f"{clean_name}_report.html")
    with open(html_report_path, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Báo Cáo Nghiên Cứu Protein - {clean_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 24px; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        .header {{ background: #1e293b; padding: 24px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 24px; }}
        h1 {{ color: #38bdf8; margin-top: 0; }}
        h2 {{ color: #818cf8; border-bottom: 2px solid #334155; padding-bottom: 8px; margin-top: 32px; }}
        .badge {{ background: #0284c7; color: white; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .card {{ background: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; }}
        .evidence-card {{ background: #0b132b; border-left: 4px solid #38bdf8; padding: 12px 16px; margin-bottom: 12px; border-radius: 0 8px 8px 0; font-size: 14px; }}
        img {{ max-width: 100%; border-radius: 8px; }}
        a {{ color: #38bdf8; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔬 Báo Cáo Nghiên Cứu Protein: {uniprot_data['protein_name']} ({clean_name})</h1>
            <p><span class="badge">UniProt: {uniprot_data['accession']}</span> <span class="badge">PDB: {best_pdb}</span> <span class="badge">Sinh vật: {uniprot_data['organism']}</span></p>
            <p><strong>Gen:</strong> {', '.join(uniprot_data['genes'])} | <strong>Tổng số bài báo phân tích:</strong> {len(df_articles)} bài từ PubMed</p>
        </div>

        <div class="grid">
            <div class="card">
                <h2>🧬 Cấu Trúc 3D Protein ({best_pdb})</h2>
                <div style="height: 400px; position: relative; border-radius: 8px; overflow: hidden;">
                    <div id="viewport_3d" style="width: 100%; height: 100%;" class="viewer_3Dmoljs"
                         data-pdb="{best_pdb}" data-backgroundcolor="0x111827" data-style="cartoon:color=spectrum"></div>
                </div>
                <p style="font-size: 12px; color: #94a3b8; text-align: center; margin-top: 8px;">Dùng chuột kéo để xoay, lăn chuột để phóng to/thu nhỏ mô hình 3D</p>
            </div>
            <div class="card">
                <h2>⚙️ Cách Thức Hoạt Động & Chức Năng</h2>
                <p style="line-height: 1.6; font-size: 14px;">{uniprot_data['function'][:550]}...</p>
                {"<h3 style='font-size: 15px; color: #a5b4fc;'>Đường truyền tín hiệu chính:</h3><ul>" + "".join(f"<li>{p}</li>" for p in uniprot_data['pathways'][:3]) + "</ul>" if uniprot_data.get("pathways") else ""}
            </div>
        </div>

        <div class="grid" style="margin-top: 24px;">
            <div class="card">
                <h2>📊 Top Cơ Chế Hoạt Động Phân Tử</h2>
                <img src="{chart_files.get('mechanisms')}" alt="Mechanisms Chart">
            </div>
            <div class="card">
                <h2>⚠️ Top Hiệu Ứng Phụ & Độc Tính</h2>
                <img src="{chart_files.get('side_effects')}" alt="Side Effects Chart">
            </div>
        </div>

        <h2>📝 Dẫn Chứng Khoa Học Từ Abstracts</h2>
        <div class="card">
            <h3 style="color: #f87171;">Bằng chứng về Hiệu Ứng Phụ & Tác Dụng Bất Lợi:</h3>
            {"".join(f'''<div class="evidence-card">
                <strong>PMID:{ev['pmid']} ({ev['year']}):</strong> "{ev['sentence']}"
                <br><a href="https://pubmed.ncbi.nlm.nih.gov/{ev['pmid']}/" target="_blank">Xem trên PubMed &rarr;</a>
            </div>''' for ev in findings['side_effect_evidence'])}
        </div>
    </div>
</body>
</html>
""")

    print(f"\n[+] HOAN THANH TAO BAO CAO CHO: {protein_query}")
    print(f"  * Bao cao Markdown: {md_report_path}")
    print(f"  * Bao cao HTML 3D:  {html_report_path}")
    print(f"  * Thu muc chua bieu do: {output_dir}")
    return md_report_path, html_report_path


# ==============================================================================
# UNIT OF WORK 10: XỬ LÝ DÒNG LỆNH & ĐIỂM VÀO CHƯƠNG TRÌNH (CLI ENTRYPOINT)
# Mục đích:
# 1. Khởi tạo ArgumentParser để nhận tham số linh hoạt từ dòng lệnh:
#    --protein: Tên protein mục tiêu
#    --max_articles: Số lượng bài báo cần tải
#    --output_dir: Đường dẫn thư mục xuất kết quả
# 2. Gọi hàm thực thi chính generate_full_report.
# ==============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chương trình nghiên cứu protein tự động từ PubMed, UniProt và PDB.")
    parser.add_argument("--protein", type=str, default="EGFR", help="Tên protein hoặc gene (mặc định: EGFR)")
    parser.add_argument("--max_articles", type=int, default=25, help="Số lượng bài báo PubMed tối đa cần kéo (mặc định: 25)")
    parser.add_argument("--output_dir", type=str, default="./reports", help="Thư mục lưu báo cáo (mặc định: ./reports)")

    args = parser.parse_args()
    generate_full_report(args.protein, args.max_articles, args.output_dir)
