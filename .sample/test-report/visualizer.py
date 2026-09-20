"""Module trực quan hóa: biểu đồ phân tích y văn và mô hình protein 3D tương tác."""

from typing import Any, Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import py3Dmol
import seaborn as sns


def plot_publications_over_time(
    pub_by_year: Dict[str, int],
    protein_name: str,
    ax: Optional[plt.Axes] = None
) -> plt.Axes:
    """Vẽ biểu đồ xu hướng xuất bản bài báo nghiên cứu theo năm."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 4))

    years = sorted([y for y in pub_by_year.keys() if y.isdigit() and int(y) >= 2000])
    counts = [pub_by_year[y] for y in years]

    sns.set_theme(style="whitegrid")
    if years:
        sns.barplot(x=years, y=counts, ax=ax, palette="Blues_d", hue=years, legend=False)
        ax.set_xticks(range(len(years)))
        ax.set_xticklabels(years, rotation=45, ha="right")
    else:
        ax.text(0.5, 0.5, "Chưa đủ dữ liệu phân bố theo năm", ha="center", va="center")

    ax.set_title(f"Xu hướng bài báo khoa học về {protein_name} trên PubMed", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Năm xuất bản", fontsize=10)
    ax.set_ylabel("Số lượng bài báo", fontsize=10)
    plt.tight_layout()
    return ax


def plot_side_effects_chart(
    side_effects: List[Tuple[str, int]],
    protein_name: str,
    ax: Optional[plt.Axes] = None
) -> plt.Axes:
    """Vẽ biểu đồ tần suất xuất hiện các tác dụng phụ / hiệu ứng phụ trong tài liệu y văn."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 4.5))

    if not side_effects:
        ax.text(0.5, 0.5, "Không phát hiện từ khóa tác dụng phụ nổi bật", ha="center", va="center")
        ax.set_title(f"Tác dụng phụ liên quan đến {protein_name}", fontsize=12, fontweight="bold")
        return ax

    terms = [item[0].capitalize() for item in side_effects][::-1]
    counts = [item[1] for item in side_effects][::-1]

    sns.set_theme(style="whitegrid")
    colors = sns.color_palette("Reds_r", len(terms))
    bars = ax.barh(terms, counts, color=colors, edgecolor="none", height=0.65)
    
    # Gắn nhãn giá trị số lượng trên từng cột
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.2, bar.get_y() + bar.get_height() / 2, f"{int(width)}",
                va="center", ha="left", fontsize=9, color="#444444", fontweight="bold")

    ax.set_title(f"Top Hiệu ứng phụ / Độc tính phổ biến: {protein_name}", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Số lần nhắc đến trong abstracts", fontsize=10)
    ax.set_xlim(0, max(counts) * 1.15)
    plt.tight_layout()
    return ax


def plot_mechanisms_chart(
    mechanisms: List[Tuple[str, int]],
    protein_name: str,
    ax: Optional[plt.Axes] = None
) -> plt.Axes:
    """Vẽ biểu đồ các cơ chế hoạt động phân tử được nghiên cứu nhiều nhất."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 4.5))

    if not mechanisms:
        ax.text(0.5, 0.5, "Không phát hiện từ khóa cơ chế nổi bật", ha="center", va="center")
        ax.set_title(f"Cơ chế hoạt động của {protein_name}", fontsize=12, fontweight="bold")
        return ax

    terms = [item[0].capitalize() for item in mechanisms][::-1]
    counts = [item[1] for item in mechanisms][::-1]

    sns.set_theme(style="whitegrid")
    colors = sns.color_palette("viridis_r", len(terms))
    bars = ax.barh(terms, counts, color=colors, edgecolor="none", height=0.65)

    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.2, bar.get_y() + bar.get_height() / 2, f"{int(width)}",
                va="center", ha="left", fontsize=9, color="#444444", fontweight="bold")

    ax.set_title(f"Top Cơ chế hoạt động phân tử: {protein_name}", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Số lần nhắc đến trong abstracts", fontsize=10)
    ax.set_xlim(0, max(counts) * 1.15)
    plt.tight_layout()
    return ax


def view_3d_protein(
    pdb_id: Optional[str] = None,
    pdb_content: Optional[str] = None,
    style: str = "cartoon",
    color_scheme: str = "spectrum",
    show_surface: bool = False,
    width: int = 700,
    height: int = 500
) -> py3Dmol.view:
    """Tạo đối tượng hiển thị cấu trúc protein 3D tương tác bằng py3Dmol.
    
    Hỗ trợ render ngay trên Jupyter Notebook:
    - Xoay, zoom bằng chuột.
    - Style: cartoon, stick, sphere, line.
    - Phủ bề mặt phân tử (Molecular surface).
    """
    view = py3Dmol.view(width=width, height=height)

    if pdb_content:
        view.addModel(pdb_content, "pdb")
    elif pdb_id:
        view.addModel(f"pdb:{pdb_id}")
    else:
        raise ValueError("Cần cung cấp ít nhất pdb_id hoặc pdb_content.")

    # Cấu hình phong cách hiển thị
    if style == "cartoon":
        view.setStyle({'cartoon': {'color': color_scheme}})
    elif style == "stick":
        view.setStyle({'stick': {}})
    elif style == "sphere":
        view.setStyle({'sphere': {}})

    # Phủ bề mặt nếu được yêu cầu
    if show_surface:
        view.addSurface(py3Dmol.VDW, {'opacity': 0.65, 'color': 'white'})

    view.zoomTo()
    return view


def export_3d_viewer_html(
    pdb_id: str,
    width: str = "100%",
    height: str = "480px"
) -> str:
    """Tạo đoạn mã nhúng HTML độc lập có thể xem cấu trúc 3D trên trình duyệt qua 3Dmol.js CDN."""
    return f"""
    <div style="height: {height}; width: {width}; position: relative; border-radius: 8px; overflow: hidden; border: 1px solid #e0e0e0;">
        <div id="viewport_{pdb_id}" style="width: 100%; height: 100%;" class="viewer_3Dmoljs"
             data-pdb="{pdb_id}"
             data-backgroundcolor="0x0f172a"
             data-style="cartoon:color=spectrum">
        </div>
        <div style="position: absolute; bottom: 8px; right: 12px; font-size: 11px; color: #94a3b8; background: rgba(0,0,0,0.5); padding: 2px 8px; border-radius: 4px;">
            PDB: {pdb_id} | Click & kéo để xoay
        </div>
    </div>
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    """
