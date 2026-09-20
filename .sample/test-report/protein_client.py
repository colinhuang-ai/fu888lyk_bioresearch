"""Module kết nối UniProt và RCSB PDB API để lấy thông tin chức năng và cấu trúc 3D của protein."""

from typing import Any, Dict, List, Optional
import requests


class ProteinClient:
    """Client tương tác với UniProt KB và RCSB PDB API."""

    UNIPROT_API = "https://rest.uniprot.org/uniprotkb"
    RCSB_PDB_API = "https://data.rcsb.org/rest/v1/core/entry"
    RCSB_DOWNLOAD_URL = "https://files.rcsb.org/download"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def search_uniprot(self, protein_or_gene: str, organism: str = "human") -> Optional[Dict[str, Any]]:
        """Tìm kiếm thông tin protein từ UniProt KnowledgeBase.
        
        Ưu tiên protein ở người (Homo sapiens) và khớp chính xác tên Gene/Protein.
        """
        symbol = protein_or_gene.strip()
        org_filter = "AND (organism_id:9606)" if organism.lower() in ("human", "homo sapiens", "9606") else ""

        # Ưu tiên 1: Khớp chính xác tên Gene hoặc entry name trong Swiss-Prot reviewed
        queries = [
            f"(gene_exact:{symbol} OR id:{symbol.upper()}_HUMAN) {org_filter} AND (reviewed:true)",
            f"({symbol}) {org_filter} AND (reviewed:true)",
            f"({symbol}) AND (reviewed:true)",
            f"({symbol})"
        ]

        data = None
        for q in queries:
            url = f"{self.UNIPROT_API}/search"
            params = {"query": q, "format": "json", "size": 1}
            try:
                resp = self.session.get(url, params=params, timeout=15)
                if resp.status_code == 200:
                    res_json = resp.json()
                    if res_json.get("results"):
                        data = res_json
                        break
            except Exception:
                continue

        if not data or not data.get("results"):
            return None

        entry = data["results"][0]
        accession = entry.get("primaryAccession", "")
        
        # Tên protein
        protein_desc = entry.get("proteinDescription", {})
        rec_name = protein_desc.get("recommendedName", {}).get("fullName", {}).get("value", "")
        if not rec_name:
            alt_names = protein_desc.get("submissionNames", [])
            if alt_names:
                rec_name = alt_names[0].get("fullName", {}).get("value", protein_or_gene)
            else:
                rec_name = protein_or_gene

        # Gene names
        genes = [g.get("geneName", {}).get("value", "") for g in entry.get("genes", []) if "geneName" in g]

        # Comments: Function, Pathway, Disease, Pharmaceutical
        function_texts = []
        pathway_texts = []
        disease_texts = []
        pharmaceutical_texts = []

        for comment in entry.get("comments", []):
            c_type = comment.get("commentType", "")
            texts = [t.get("value", "") for t in comment.get("texts", [])]
            combined_text = " ".join(texts)

            if c_type == "FUNCTION":
                function_texts.append(combined_text)
            elif c_type == "PATHWAY":
                pathway_texts.append(combined_text)
            elif c_type == "DISEASE":
                note = comment.get("note", {}).get("texts", [])
                note_str = " ".join([n.get("value", "") for n in note])
                disease_name = comment.get("disease", {}).get("diseaseId", "")
                disease_texts.append(f"{disease_name}: {note_str}".strip(": "))
            elif c_type == "PHARMACEUTICAL":
                pharmaceutical_texts.append(combined_text)

        # Cross-references: PDB structures
        pdb_entries = []
        for xref in entry.get("uniProtKBCrossReferences", []):
            if xref.get("database") == "PDB":
                pdb_id = xref.get("id")
                properties = {p.get("key"): p.get("value") for p in xref.get("properties", [])}
                pdb_entries.append({
                    "pdb_id": pdb_id,
                    "method": properties.get("Method", "Unknown"),
                    "resolution": properties.get("Resolution", "N/A"),
                    "chains": properties.get("Chains", "N/A")
                })

        # Sắp xếp PDB ưu tiên X-ray diffraction độ phân giải cao nhất
        def parse_resolution(item):
            res_str = item.get("resolution", "").replace("A", "").strip()
            try:
                return float(res_str)
            except ValueError:
                return 999.0

        pdb_entries.sort(key=parse_resolution)

        return {
            "accession": accession,
            "protein_name": rec_name,
            "genes": genes,
            "organism": entry.get("organism", {}).get("scientificName", "Unknown"),
            "function": "\n".join(function_texts) if function_texts else "Không có mô tả chức năng chi tiết.",
            "pathways": pathway_texts,
            "diseases": disease_texts,
            "pharmaceuticals": pharmaceutical_texts,
            "pdb_structures": pdb_entries,
            "best_pdb_id": pdb_entries[0]["pdb_id"] if pdb_entries else None
        }

    def get_pdb_metadata(self, pdb_id: str) -> Dict[str, Any]:
        """Lấy thông tin chi tiết cấu trúc từ RCSB PDB."""
        url = f"{self.RCSB_PDB_API}/{pdb_id}"
        resp = self.session.get(url, timeout=15)
        if resp.status_code != 200:
            return {"pdb_id": pdb_id, "title": "Metadata not found"}

        data = resp.json()
        struct = data.get("struct", {})
        exptl = data.get("exptl", [{}])[0] if data.get("exptl") else {}
        rcsb_entry_info = data.get("rcsb_entry_info", {})

        return {
            "pdb_id": pdb_id,
            "title": struct.get("title", ""),
            "method": exptl.get("method", "Unknown"),
            "resolution": rcsb_entry_info.get("resolution_combined", [None])[0],
            "release_date": data.get("rcsb_accession_info", {}).get("initial_release_date", ""),
            "download_url": f"{self.RCSB_DOWNLOAD_URL}/{pdb_id}.pdb"
        }

    def download_pdb_file(self, pdb_id: str, save_path: Optional[str] = None) -> str:
        """Tải nội dung file PDB từ RCSB."""
        url = f"{self.RCSB_DOWNLOAD_URL}/{pdb_id}.pdb"
        resp = self.session.get(url, timeout=20)
        resp.raise_for_status()
        pdb_content = resp.text

        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(pdb_content)

        return pdb_content
