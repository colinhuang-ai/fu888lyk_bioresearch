# CLAUDE.md

Hướng dẫn làm việc với codebase này. Đọc trước khi sửa code.

## Dự án là gì

Trợ lý nghiên cứu sinh dược học kháng ung thư: thu thập bài báo (PubMed / Europe PMC)
→ nạp vào kho RAG Hybrid (ChromaDB + BM25) → tra cứu hóa dược (PubChem + Lipinski)
→ sinh bản thảo bài báo ISI/Scopus xuất ra `.docx` / `.md`.

Ngôn ngữ: Python. Giao diện: Streamlit (web) và Rich (CLI).

Quy ước ngôn ngữ trong code: docstring, comment, chuỗi hiển thị viết **tiếng Việt**;
tên biến/hàm/lớp và thuật ngữ khoa học viết **tiếng Anh**. Giữ đúng quy ước này.

## Chạy dự án

```bash
pip install -r requirements.txt
streamlit run appst.py               # giao diện web (mặc định)
python cli.py                        # giao diện dòng lệnh
python -m unittest discover tests    # chạy test
```

Biến môi trường đọc từ `.env` qua `python-dotenv`, khai báo tập trung ở
[app/config.py](app/config.py): `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LLM_MODEL`,
`NCBI_EMAIL`, `NCBI_API_KEY`. Không rải `os.getenv` trong module — thêm hằng số mới
vào `config.py` rồi import từ đó.

## Cấu trúc thư mục

```text
anti-cancer-research/
├── appst.py                    # Entry point Streamlit: khởi tạo assistant, dựng danh sách TABS
├── cli.py                      # Entry point CLI (Rich): menu 5 chức năng
├── requirements.txt
├── research_syllabus_and_rag_blueprint.md   # Tài liệu nghiệp vụ gốc (syllabus nghiên cứu)
│
├── app/
│   ├── config.py               # Cấu hình trung tâm: đường dẫn, API key, tên collection
│   ├── agent/
│   │   └── assistant.py        # ScientificResearchAssistant — lớp điều phối duy nhất
│   └── tools/                  # Các "năng lực" độc lập, không biết gì về UI
│       ├── fetchers/           # Thu thập bài báo
│       │   ├── pubmed_fetcher.py   # PubMedFetcher (NCBI E-Utilities)
│       │   ├── europe_pmc.py       # EuropePMCFetcher (+ tải PDF Open Access)
│       │   └── model/article.py    # AcademicArticle (pydantic)
│       ├── ingestion/          # Đọc & chia nhỏ tài liệu
│       │   ├── pdf_parser.py       # PDFPaperParser (pypdfium2) + regex bắt strain/cell line/pathway
│       │   └── text_splitter.py    # ScientificTextSplitter → DocumentChunk
│       ├── rag/                # Kho tri thức
│       │   ├── vector_store.py     # VectorStore (ChromaDB persistent)
│       │   ├── bm25_index.py       # BM25Index (rank-bm25) + scientific_tokenize
│       │   └── hybrid_retriever.py # HybridRetriever — hợp nhất 2 nguồn bằng RRF
│       └── writer/             # Soạn thảo bản thảo
│           ├── templates.py        # Khung section chuẩn + system prompt
│           ├── paper_generator.py  # ScientificPaperGenerator, PaperMetadata, GeneratedManuscript
│           └── docx_exporter.py    # AcademicDocxExporter (python-docx)
│
├── views/                      # Streamlit UI — mỗi tab một module, mỗi module một hàm render(assistant)
│   └── sidebar.py, tab_collect.py, tab_chemistry.py, tab_rag.py, tab_writer.py, tab_lab.py
│
├── data/
│   ├── raw_papers/             # PDF tải về / upload
│   ├── vector_db/              # ChromaDB persistent (KHÔNG sửa tay, KHÔNG commit)
│   ├── test_vector_db/         # DB tạm của test, bị xóa trong tearDown
│   └── lab_compounds.csv       # Dữ liệu hoạt tính sinh học phòng lab
├── outputs/                    # Bản thảo xuất ra (.docx, .md)
├── books/                      # Notebook & script demo dạy học
└── tests/test_pipeline.py      # Unit + integration test (một số test gọi mạng thật)
```

## Kiến trúc: 3 tầng, một chiều

```text
views/  hoặc  cli.py           ← tầng giao diện
        ↓ chỉ gọi qua
app/agent/assistant.py         ← tầng điều phối (ScientificResearchAssistant)
        ↓ chỉ gọi qua
app/tools/**                   ← tầng năng lực
```

Quy tắc bắt buộc:

- **`app/tools/**` không import `streamlit`, `rich`, hay bất cứ thứ gì trong `views/`.**
  Tool chỉ nhận tham số thuần và trả về pydantic model hoặc `dict`.
- **`views/` không import trực tiếp từ `app/tools/`.** Mọi thứ đi qua tham số `assistant`
  (ví dụ `assistant.vector_store.count()`, `assistant.search_and_index_pubmed(...)`).
- **Mọi import dùng đường dẫn tuyệt đối từ gốc** — `from app.tools.rag.vector_store import VectorStore`,
  không dùng import tương đối.
- Mỗi package trong `app/tools/` có `__init__.py` **re-export** lớp/hàm công khai kèm `__all__`.
  Thêm module mới thì cập nhật `__init__.py` tương ứng.
- Dữ liệu trao đổi giữa các tầng là **pydantic `BaseModel`**, không phải dict trần.

## Các tool hiện có

| Tool | Lớp / hàm chính | Vào → Ra | Ghi chú |
|---|---|---|---|
| PubMed | `PubMedFetcher.search_articles(query, max_results)` | str → `List[AcademicArticle]` | NCBI E-Utilities; có `_fallback_esummary` khi efetch lỗi. Khai báo `NCBI_EMAIL` để nâng rate limit 3→10 req/s |
| Europe PMC | `EuropePMCFetcher.search_articles()`, `.download_pdf(article)` | str → `List[AcademicArticle]`; PDF → `data/raw_papers/` | Nguồn duy nhất lấy được PDF Open Access |
| PDF parser | `PDFPaperParser.parse_pdf(path)` | path → `ParsedPaper` | pypdfium2; nhận diện strain / cell line / pathway / đoạn IC50 bằng regex trong `STRAIN_PATTERNS`, `CELL_LINE_PATTERNS`, `PATHWAY_PATTERNS` |
| Splitter | `ScientificTextSplitter.split_text(text, base_metadata)` | str + dict → `List[DocumentChunk]` | mặc định `chunk_size=800`, `chunk_overlap=150` |
| Vector store | `VectorStore.add_chunks()`, `.search()`, `.count()`, `.get_all_documents()` | `List[DocumentChunk]` → ChromaDB | Persistent tại `data/vector_db`, collection `cancer_bacteria_research` |
| BM25 | `BM25Index.build_index(docs)`, `.search(query, top_k)` | list dict → list dict | `scientific_tokenize` giữ nguyên ký hiệu khoa học (MCF-7, IC50) |
| Hybrid RAG | `HybridRetriever.search(query, top_k)`, `.reload()`, `.format_context_for_prompt()` | str → list dict có `rrf_score`, `rank` | Reciprocal Rank Fusion, `rrf_k=60`. **Nạp dữ liệu mới xong phải gọi `.reload()`** để dựng lại BM25 |
| PubChem | `PubChemClient.get_compound_by_name()` / `.get_compound_by_cid()` | str/int → `CompoundData` hoặc `None` | PUG REST; trả `None` khi không tìm thấy — luôn kiểm tra |
| Lipinski | `evaluate_druglikeness(compound)` | `CompoundData` → `DruglikenessReport` | Hàm thuần, không gọi mạng — nơi dễ viết test nhất |
| Paper generator | `ScientificPaperGenerator.generate_manuscript(meta, druglikeness, bioassay_data)` | `PaperMetadata` → `GeneratedManuscript` | Lấy ngữ cảnh trích dẫn từ `HybridRetriever` |
| DOCX export | `AcademicDocxExporter.export_manuscript(...)` | manuscript → `outputs/*.docx` | Times New Roman 12pt, lề 1 inch |

Điểm vào duy nhất của tầng trên là 5 phương thức của `ScientificResearchAssistant`
trong [app/agent/assistant.py](app/agent/assistant.py):
`search_and_index_pubmed`, `ingest_pdf_file`, `analyze_chemical_compound`,
`query_rag`, `write_full_paper`.

## Thêm một tool mới

1. Tạo module trong `app/tools/<nhóm>/<tên>.py`, định nghĩa pydantic model cho kết quả.
2. Re-export trong `app/tools/<nhóm>/__init__.py` và cập nhật `__all__`.
3. Khởi tạo trong `ScientificResearchAssistant.__init__`, thêm một phương thức điều phối
   có docstring tiếng Việt một dòng.
4. Nếu cần lộ ra UI: thêm `views/tab_<tên>.py` với hàm `render(assistant)`, đăng ký vào
   `TABS` trong [appst.py](appst.py); thêm mục menu tương ứng trong [cli.py](cli.py) nếu hợp lý.
5. Thêm test vào `tests/test_pipeline.py`.

Chi tiết từng bước kèm mẫu code: [.agents/skills/bio-research-tool/SKILL.md](.agents/skills/bio-research-tool/SKILL.md).

## Quy ước khi gọi API bên ngoài

- Luôn `try/except` quanh lời gọi mạng, trả về `None` / `[]` thay vì để exception nổi lên UI.
- Tầng gọi phải xử lý trường hợp rỗng — xem `cli.py` và các `views/tab_*.py`, đều
  `if not result: ... return` trước khi render.
- Không hardcode API key; đọc từ `app/config.py`.

## Test

`tests/test_pipeline.py` trộn unit test và integration test gọi mạng thật
(`test_pubmed_fetcher_live`, `test_pubchem_and_lipinski`). Chúng fail khi mất mạng —
đó là hành vi đã biết, đừng "sửa" bằng cách xóa test. Test RAG dùng
`data/test_vector_db` và tự dọn trong `tearDown`.

## Không đụng vào

- `data/vector_db/`, `data/test_vector_db/` — dữ liệu nhị phân ChromaDB sinh tự động.
- `outputs/` — sản phẩm xuất ra, có thể tạo lại.
- `__pycache__/`.
- `../test-report/test/fu888lyk_bioresearch/` — bản sao cũ của dự án (vẫn dùng `src/`, cấu trúc phẳng,
  chưa có thư mục `tools/`). Chỉ để tham khảo, không đồng bộ thay đổi sang đó.

## Cạm bẫy đã gặp trong repo này

**Thiếu `__init__.py` ở thư mục con.** `app/tools/fetchers/model/` từng thiếu
`__init__.py` trong khi 5 file import `AcademicArticle` từ đó, khiến cả `appst.py`,
`cli.py` lẫn toàn bộ test chết ngay ở bước import. Đã sửa. Khi tạo thư mục mới trong
`app/`, luôn thêm `__init__.py` ở **mọi** cấp, kể cả thư mục chỉ chứa một model.

**Đổi tên thư mục package.** Mọi import trong dự án là đường dẫn tuyệt đối `from app...`,
kể cả các `__init__.py` tự trỏ về chính package của mình. Đổi tên thư mục mà không sửa
đồng loạt import là hỏng ngay. Tìm đủ tham chiếu bằng:

```bash
grep -rn "from app\.\|import app\.\|app/" --include=*.py --include=*.md --include=*.ipynb .
```

Nhớ tính cả `books/*.ipynb`, `README.md` và chính file này. Sau khi đổi, xóa hết
`__pycache__` để Python không nạp bytecode cũ.

**Console Windows và tiếng Việt.** `cli.py` in tiếng Việt qua `rich`; chạy trong
terminal dùng codepage cp1252 sẽ nổ `UnicodeEncodeError`. Đặt `PYTHONIOENCODING=utf-8`
hoặc `chcp 65001` trước khi chạy.
