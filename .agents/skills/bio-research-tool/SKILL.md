---
name: bio-research-tool
description: Thêm hoặc sửa một tool năng lực trong dự án anti-cancer-research (fetcher nguồn bài báo mới, bộ phân tích hóa dược, chiến lược RAG, module xuất bản thảo), và nối nó qua ScientificResearchAssistant ra CLI/Streamlit. Dùng khi người dùng nói "thêm nguồn ChEMBL/arXiv/bioRxiv", "thêm tool tính TPSA/ADMET", "thêm tab mới", "nối tool này vào assistant", "thêm bước vào pipeline nghiên cứu", hoặc khi sửa bất kỳ file nào dưới app/tools/.
---

# Thêm / sửa tool trong dự án anti-cancer-research

Dự án có kiến trúc 3 tầng một chiều: `views/` hoặc `cli.py` → `app/agent/assistant.py`
→ `app/tools/**`. Một tool mới chỉ "sống" khi đi đủ 5 bước dưới đây. Bỏ bước 2 thì
`__init__.py` lệch với thực tế; bỏ bước 3 thì UI không với tới được tool.

Đọc [CLAUDE.md](../../../CLAUDE.md) trước để nắm bảng tool hiện có và các quy tắc chung.

## Trước khi bắt đầu

Kiểm tra dự án import được không:

```bash
python -c "from app.agent.assistant import ScientificResearchAssistant; print('OK')"
```

Nếu fail, đọc mục "Cạm bẫy đã gặp trong repo này" ở cuối CLAUDE.md.

## Bước 1 — Viết module tool

Đặt tại `app/tools/<nhóm>/<tên>.py`. Nhóm hiện có: `fetchers`, `ingestion`, `rag`,
`chemistry`, `writer`. Tạo nhóm mới chỉ khi tool thật sự không thuộc nhóm nào.

Khuôn mẫu (bám theo `app/tools/chemistry/pubchem_client.py`):

```python
"""
Mô tả một dòng bằng tiếng Việt: tool này làm gì, gọi API nào.
"""

from typing import List, Optional
import requests
from pydantic import BaseModel

from app.config import SOME_API_KEY   # hằng số mới phải khai báo ở config.py


class ChemblCompound(BaseModel):
    """Kết quả trả về — luôn là pydantic model, không dùng dict trần."""
    chembl_id: str
    pref_name: str = ""
    max_phase: Optional[int] = None


class ChemblClient:
    """Tra cứu hợp chất trên ChEMBL REST API."""

    BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def search_compound(self, name: str) -> Optional[ChemblCompound]:
        """Tìm hợp chất theo tên, trả về None nếu không thấy hoặc lỗi mạng."""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/molecule/search",
                params={"q": name, "format": "json"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            items = resp.json().get("molecules", [])
        except Exception as exc:
            print(f"Lỗi khi gọi ChEMBL cho '{name}': {exc}")
            return None

        if not items:
            return None
        ...
```

Bắt buộc:

- Docstring và comment **tiếng Việt**, tên định danh **tiếng Anh**.
- Import tuyệt đối `from app....`, không import tương đối.
- **Không** import `streamlit` / `rich` / `views`.
- Mọi lời gọi mạng bọc `try/except`, trả `None` hoặc `[]` — không để exception nổi lên UI.
- Có `timeout` cho mọi request.

## Bước 2 — Re-export trong `__init__.py`

```python
from app.tools.chemistry.chembl_client import ChemblClient, ChemblCompound

__all__ = [..., "ChemblClient", "ChemblCompound"]
```

Nếu tạo nhóm mới, nhớ cả `app/tools/<nhóm>/__init__.py` lẫn việc nhóm đó phải có file
`__init__.py` ở **mọi** cấp thư mục con (lỗi thiếu `__init__.py` ở `fetchers/model/`
là bài học có sẵn trong repo này).

## Bước 3 — Nối vào ScientificResearchAssistant

Trong `app/agent/assistant.py`:

```python
    def __init__(self):
        ...
        self.chembl = ChemblClient()

    def lookup_chembl(self, compound_name: str) -> Optional[ChemblCompound]:
        """Tra cứu thông tin phát triển lâm sàng của hợp chất trên ChEMBL."""
        return self.chembl.search_compound(compound_name)
```

Phương thức điều phối giữ mỏng: gọi tool, ghép kết quả, trả về. Logic nghiệp vụ nằm
trong tool, không nằm ở đây. Nếu thao tác có nạp dữ liệu vào RAG thì **phải**
`self.vector_store.add_chunks(chunks)` rồi `self.retriever.reload()` — quên `reload()`
thì BM25 không thấy dữ liệu mới và kết quả hybrid search sẽ thiếu.

## Bước 4 — Lộ ra giao diện

### Streamlit

Tạo `views/tab_<tên>.py`, đúng một hàm `render(assistant)`:

```python
"""Tab N: Tra cứu ChEMBL."""

import streamlit as st


def render(assistant):
    st.header("Tra Cứu Dữ Liệu Lâm Sàng ChEMBL")

    name = st.text_input("Tên hợp chất", value="Staurosporine")
    if not st.button("🔎 Tra cứu", type="primary"):
        return

    with st.spinner("Đang gọi ChEMBL..."):
        result = assistant.lookup_chembl(name)

    if not result:
        st.warning(f"Không tìm thấy '{name}' trên ChEMBL.")
        return

    st.success(f"ChEMBL ID: {result.chembl_id}")
```

Quy ước của các tab hiện có, giữ nguyên: early-return sau `st.button`, bọc lời gọi
chậm trong `st.spinner`, kiểm tra rỗng trước khi render, dùng `st.warning` cho
"không có kết quả" và `st.success` cho thành công.

Đăng ký trong `appst.py`:

```python
TABS = [
    ...
    ("🧬 7. Tra Cứu ChEMBL", tab_chembl),
]
```

và thêm module vào `views/__init__.py`.

### CLI

Trong `cli.py`: viết hàm `run_<tên>(assistant)` dùng `rich` (`Panel`, `Table`,
`Prompt.ask`, `console.status`), thêm một dòng vào danh sách menu và một nhánh `elif`
trong vòng lặp `main()`. Nhớ dịch số thứ tự của mục "Thoát".

## Bước 5 — Test

Thêm method vào `TestScientificPipeline` trong `tests/test_pipeline.py`:

```python
    def test_chembl_lookup(self):
        """Kiểm tra tra cứu ChEMBL trả về đúng cấu trúc."""
        client = ChemblClient()
        result = client.search_compound("Staurosporine")
        if result is None:
            self.skipTest("Không kết nối được ChEMBL")
        self.assertTrue(result.chembl_id.startswith("CHEMBL"))
```

Test chạm mạng thì `skipTest` khi không kết nối được, đừng để nó fail giả. Phần logic
thuần (tính toán, phân loại, định dạng) tách thành hàm riêng và test trực tiếp — như
`evaluate_druglikeness` đã làm.

Chạy:

```bash
python -m unittest discover tests
```

## Checklist trước khi báo xong

- [ ] Module không import `streamlit` / `rich` / `views`
- [ ] Kết quả là pydantic `BaseModel`
- [ ] `__init__.py` của nhóm đã re-export và cập nhật `__all__`
- [ ] Mọi thư mục mới đều có `__init__.py`
- [ ] Assistant có phương thức điều phối kèm docstring tiếng Việt
- [ ] Nếu nạp dữ liệu vào RAG: đã gọi `retriever.reload()`
- [ ] Tab Streamlit đã đăng ký ở cả `appst.py` và `views/__init__.py`
- [ ] Có test, và `python -m unittest discover tests` chạy được
- [ ] Hằng số cấu hình mới nằm ở `app/config.py`, không hardcode key
- [ ] Đã cập nhật bảng tool trong `CLAUDE.md`
