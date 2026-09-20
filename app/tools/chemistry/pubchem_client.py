"""
PubChem REST API Client.
Tra cứu thông tin cấu trúc hóa học, số nhận diện CID, Canonical SMILES và các thông số hóa lý.
"""

from typing import Optional, Dict, Any
import requests
from pydantic import BaseModel


class CompoundData(BaseModel):
    name: str
    cid: Optional[int] = None
    molecular_formula: str = "N/A"
    molecular_weight: float = 0.0
    canonical_smiles: str = "N/A"
    iupac_name: str = "N/A"
    xlogp: Optional[float] = None
    h_bond_donors: int = 0
    h_bond_acceptors: int = 0
    rotatable_bonds: int = 0
    pubchem_url: str = ""


class PubChemClient:
    """Tra cứu PUG REST API của NCBI PubChem."""

    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    def get_compound_by_name(self, compound_name: str) -> Optional[CompoundData]:
        """Tra cứu hợp chất qua tên thông thường (ví dụ: Staurosporine, Doxorubicin, Salinosporamide A)."""
        clean_name = compound_name.strip()
        url = (
            f"{self.BASE_URL}/compound/name/{clean_name}/property/"
            "MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName,XLogP,"
            "HBondDonorCount,HBondAcceptorCount,RotatableBondCount/JSON"
        )

        try:
            resp = requests.get(url, timeout=12)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()

            props = resp.json().get("PropertyTable", {}).get("Properties", [])
            if not props:
                return None

            p = props[0]
            cid = p.get("CID")
            mw_str = p.get("MolecularWeight", "0")
            try:
                mw = float(mw_str)
            except ValueError:
                mw = 0.0

            xlogp_val = p.get("XLogP")
            xlogp = float(xlogp_val) if xlogp_val is not None else None

            return CompoundData(
                name=clean_name,
                cid=cid,
                molecular_formula=p.get("MolecularFormula", "N/A"),
                molecular_weight=round(mw, 2),
                canonical_smiles=p.get("CanonicalSMILES", p.get("ConnectivitySMILES", "N/A")),
                iupac_name=p.get("IUPACName", "N/A"),
                xlogp=xlogp,
                h_bond_donors=int(p.get("HBondDonorCount", 0)),
                h_bond_acceptors=int(p.get("HBondAcceptorCount", 0)),
                rotatable_bonds=int(p.get("RotatableBondCount", 0)),
                pubchem_url=f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}" if cid else ""
            )
        except Exception as e:
            print(f"[PubChemClient] Lỗi khi tra cứu hợp chất '{compound_name}': {e}")
            return None

    def get_compound_by_cid(self, cid: int) -> Optional[CompoundData]:
        """Tra cứu hợp chất trực tiếp theo mã PubChem CID."""
        url = (
            f"{self.BASE_URL}/compound/cid/{cid}/property/"
            "MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName,XLogP,"
            "HBondDonorCount,HBondAcceptorCount,RotatableBondCount/JSON"
        )
        try:
            resp = requests.get(url, timeout=12)
            resp.raise_for_status()
            props = resp.json().get("PropertyTable", {}).get("Properties", [])
            if not props:
                return None
            p = props[0]
            mw = float(p.get("MolecularWeight", 0))
            xlogp_val = p.get("XLogP")
            xlogp = float(xlogp_val) if xlogp_val is not None else None

            return CompoundData(
                name=p.get("IUPACName", f"CID_{cid}"),
                cid=cid,
                molecular_formula=p.get("MolecularFormula", "N/A"),
                molecular_weight=round(mw, 2),
                canonical_smiles=p.get("CanonicalSMILES", "N/A"),
                iupac_name=p.get("IUPACName", "N/A"),
                xlogp=xlogp,
                h_bond_donors=int(p.get("HBondDonorCount", 0)),
                h_bond_acceptors=int(p.get("HBondAcceptorCount", 0)),
                rotatable_bonds=int(p.get("RotatableBondCount", 0)),
                pubchem_url=f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
            )
        except Exception as e:
            print(f"[PubChemClient] Lỗi CID {cid}: {e}")
            return None
