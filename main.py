"""
Điểm khởi chạy giao diện dòng lệnh (CLI Runner) cho Hệ thống Nghiên cứu Vi sinh & Soạn thảo Paper.
"""

import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from src.agent.assistant import ScientificResearchAssistant
from src.writer.paper_generator import PaperMetadata

console = Console()


def display_welcome():
    console.print(Panel.fit(
        "[bold cyan]HỆ THỐNG TRỢ LÝ AI NGHIÊN CỨU DƯỢC LIỆU VI SINH & SOẠN THẢO PAPER[/bold cyan]\n"
        "[italic green]Syllabus: Phân lập vi khuẩn -> Trích xuất -> Cơ chế MoA (Apoptosis/Caspase) -> Viết báo ISI/Scopus (Q1/Q2)[/italic green]",
        border_style="bright_blue"
    ))


def run_pubmed_search(assistant: ScientificResearchAssistant):
    console.print("\n[bold yellow]--- 1. TÌM KIẾM BÀI BÁO TRÊN PUBMED & NẠP VÀO RAG ---[/bold yellow]")
    query = Prompt.ask("Nhập từ khóa tìm kiếm (VD: 'Streptomyces apoptosis IC50')", default="Streptomyces apoptosis HeLa")
    with console.status("[bold green]Đang gọi PubMed E-Utilities và lập chỉ mục RAG...[/bold green]"):
        articles = assistant.search_and_index_pubmed(query=query, max_results=3)

    if not articles:
        console.print("[red]Không tìm thấy bài báo nào hoặc lỗi kết nối mạng.[/red]")
        return

    table = Table(title=f"Kết quả PubMed cho: '{query}'", show_lines=True)
    table.add_column("PMID", style="cyan", width=10)
    table.add_column("Tiêu đề bài báo", style="white", width=40)
    table.add_column("Tạp chí & Năm", style="green", width=25)
    table.add_column("Abstract Preview", style="dim", width=35)

    for a in articles:
        preview = (a.abstract[:140] + "...") if a.abstract else "No abstract"
        table.add_row(a.pmid, a.title, f"{a.journal} ({a.pub_year})", preview)

    console.print(table)
    console.print(f"[bold green]✓ Đã nạp thành công {len(articles)} bài báo vào hệ thống RAG Hybrid (ChromaDB + BM25)![/bold green]")


def run_chemical_analysis(assistant: ScientificResearchAssistant):
    console.print("\n[bold yellow]--- 2. TRA CỨU HÓA DƯỢC PUBCHEM & ĐÁNH GIÁ LIPINSKI ---[/bold yellow]")
    compound = Prompt.ask("Nhập tên hợp chất cần tra cứu", default="Staurosporine")
    with console.status(f"[bold green]Đang tra cứu PubChem PUG REST cho '{compound}'...[/bold green]"):
        report = assistant.analyze_chemical_compound(compound)

    if not report:
        console.print(f"[red]Không tìm thấy hợp chất '{compound}' trên PubChem.[/red]")
        return

    table = Table(title=f"Thông số Hóa lý & Lipinski Rule of 5: {report.compound_name}", show_lines=True)
    table.add_column("Thông số / Tiêu chuẩn", style="cyan")
    table.add_column("Giá trị tính toán", style="magenta")
    table.add_column("Tiêu chuẩn thuốc", style="green")

    table.add_row("Khối lượng phân tử (MW)", f"{report.molecular_weight} Da", "≤ 500 Da")
    table.add_row("Hệ số phân bố XLogP", str(report.xlogp), "≤ 5.0")
    table.add_row("Hydrogen Bond Donors (HBD)", str(report.h_bond_donors), "≤ 5")
    table.add_row("Hydrogen Bond Acceptors (HBA)", str(report.h_bond_acceptors), "≤ 10")
    table.add_row("Rotatable Bonds", str(report.rotatable_bonds), "≤ 10 (Veber)")
    table.add_row("Số vi phạm Lipinski", str(report.lipinski_violations), "≤ 1 (Đạt chuẩn)")

    console.print(table)
    console.print(f"[bold yellow]Đánh giá sơ bộ:[/bold yellow] {report.summary_verdict}")
    console.print(Panel(report.scientific_narrative, title="Đoạn văn học thuật cho mục Discussion", border_style="cyan"))


def run_rag_query(assistant: ScientificResearchAssistant):
    console.print("\n[bold yellow]--- 3. TRUY VẤN KHO TRI THỨC HYBRID RAG (VECTOR + BM25) ---[/bold yellow]")
    query = Prompt.ask("Nhập câu hỏi tra cứu cơ chế / chủng vi sinh", default="caspase-3 apoptosis mitochondrial pathway")
    with console.status("[bold green]Đang thực hiện Hybrid Search (RRF)...[/bold green]"):
        hits = assistant.query_rag(query=query, top_k=3)

    if not hits:
        console.print("[red]Chưa có tài liệu nào trong kho RAG. Hãy chạy mục 1 trước để nạp bài báo.[/red]")
        return

    for h in hits:
        meta = h.get("metadata", {})
        console.print(Panel(
            f"[bold]Tiêu đề:[/bold] {meta.get('title', 'N/A')}\n"
            f"[bold]Nguồn:[/bold] {meta.get('source', 'N/A')} (PMID: {meta.get('pmid', 'N/A')})\n"
            f"[bold]RRF Score:[/bold] {h.get('rrf_score')}\n\n"
            f"[italic]{h['content']}[/italic]",
            title=f"Kết quả Hạng #{h['rank']}",
            border_style="green"
        ))


def run_paper_writer(assistant: ScientificResearchAssistant):
    console.print("\n[bold yellow]--- 4. TỰ ĐỘNG SOẠN THẢO BẢN THẢO BÀI BÁO (WORD & MARKDOWN) ---[/bold yellow]")
    strain = Prompt.ask("Tên chủng vi khuẩn", default="Streptomyces sp. VN-08")
    source = Prompt.ask("Nguồn phân lập sinh thái", default="Marine sediment")
    compound = Prompt.ask("Tên hợp chất / Phân đoạn hoạt tính", default="Streptoketide A")
    cells = Prompt.ask("Dòng tế bào ung thư thử nghiệm (cách nhau dấu phẩy)", default="MCF-7, HeLa")
    ic50 = Prompt.ask("Giá trị IC50 thực nghiệm", default="3.45 ± 0.28 μM")

    meta = PaperMetadata(
        title="",
        authors=["Linh Nguyen", "Minh Tran", "Corresponding Author*"],
        affiliations=["Department of Marine Biotechnology, Institute of Natural Products"],
        target_journal="Journal of Natural Products",
        bacterial_strain=strain,
        isolation_source=source,
        compound_name=compound,
        target_cancer_cells=[c.strip() for c in cells.split(",") if c.strip()],
        measured_ic50=ic50,
        observed_mechanisms=[
            "Induction of apoptosis via intrinsic mitochondrial pathway",
            "Proteolytic activation of Caspase-3 and Caspase-9",
            "Cleavage of PARP protein (89 kDa fragment)",
            "G2/M cell cycle arrest and accumulation of intracellular ROS"
        ]
    )

    bioassay_data = [
        {"compound": compound, "cell_line": "MCF-7", "ic50": "3.45 ± 0.28", "selectivity_index": "14.2"},
        {"compound": compound, "cell_line": "HeLa", "ic50": "4.12 ± 0.35", "selectivity_index": "11.8"},
        {"compound": "Doxorubicin (Ref)", "cell_line": "MCF-7", "ic50": "0.85 ± 0.08", "selectivity_index": "5.1"}
    ]

    with console.status("[bold green]Đang tổng hợp dữ liệu RAG, tính toán và xuất bản thảo...[/bold green]"):
        manuscript = assistant.write_full_paper(meta=meta, compound_name=compound, bioassay_data=bioassay_data)

    console.print(Panel(
        f"[bold green]ĐÃ TẠO BẢN THẢO THÀNH CÔNG![/bold green]\n\n"
        f"[bold cyan]Tiêu đề bài báo:[/bold cyan] {manuscript.title}\n"
        f"[bold cyan]File Word đã xuất:[/bold cyan] [underline]{manuscript.docx_file_path}[/underline]\n"
        f"[bold cyan]Tạp chí mục tiêu:[/bold cyan] {meta.target_journal}\n"
        f"[bold cyan]Số lượng trích dẫn:[/bold cyan] {len(manuscript.references)} bài báo",
        border_style="bright_green"
    ))


def main():
    display_welcome()
    assistant = ScientificResearchAssistant()

    while True:
        console.print("\n[bold white]CHỌN TÁC VỤ:[/bold white]")
        console.print("1. Tìm kiếm & Tự động nạp bài báo từ PubMed vào RAG")
        console.print("2. Tra cứu cấu trúc PubChem & Phân tích Lipinski Rule of 5")
        console.print("3. Truy vấn kho RAG Hybrid (Vector + BM25)")
        console.print("4. Soạn thảo bản thảo bài báo chuẩn ISI/Scopus (Xuất Word .docx)")
        console.print("5. Thoát")

        choice = Prompt.ask("Chọn chức năng (1-5)", default="1")
        if choice == "1":
            run_pubmed_search(assistant)
        elif choice == "2":
            run_chemical_analysis(assistant)
        elif choice == "3":
            run_rag_query(assistant)
        elif choice == "4":
            run_paper_writer(assistant)
        elif choice == "5":
            console.print("[italic cyan]Tạm biệt và chúc công trình nghiên cứu của bạn sớm xuất bản Q1![/italic cyan]")
            break
        else:
            console.print("[red]Lựa chọn không hợp lệ, vui lòng chọn từ 1 đến 5.[/red]")


if __name__ == "__main__":
    main()
