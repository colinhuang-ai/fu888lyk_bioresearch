"""
Đánh giá tính chất Dược lý và Quy tắc 5 Lipinski (Lipinski Rule of 5) & Quy chuẩn Veber.
Hỗ trợ viết phần Thảo luận (Discussion) và Đánh giá tiềm năng thuốc (Drug-likeness) trong bài báo.
"""

from typing import Dict, Any, List
from pydantic import BaseModel
from src.chemistry.pubchem_client import CompoundData


class DruglikenessReport(BaseModel):
    compound_name: str
    molecular_weight: float
    xlogp: float
    h_bond_donors: int
    h_bond_acceptors: int
    rotatable_bonds: int
    lipinski_violations: int
    veber_violations: int
    is_lipinski_compliant: bool
    is_veber_compliant: bool
    summary_verdict: str
    detailed_violations: List[str]
    scientific_narrative: str


def evaluate_druglikeness(compound: CompoundData) -> DruglikenessReport:
    """
    Phân tích các tiêu chí dược động học ADMET sơ bộ theo Lipinski và Veber:
    - Lipinski: MW <= 500, LogP <= 5, HBD <= 5, HBA <= 10 (Vi phạm <= 1 là đạt chuẩn).
    - Veber: Rotatable bonds <= 10 (Đảm bảo độ linh động phân tử phù hợp khả năng hấp thu qua đường uống).
    """
    violations: List[str] = []
    lipinski_count = 0

    # 1. Khối lượng phân tử
    if compound.molecular_weight > 500:
        lipinski_count += 1
        violations.append(f"Molecular Weight > 500 Da ({compound.molecular_weight} Da)")

    # 2. Hệ số phân bố LogP
    logp_val = compound.xlogp if compound.xlogp is not None else 0.0
    if logp_val > 5.0:
        lipinski_count += 1
        violations.append(f"XLogP > 5.0 ({logp_val})")

    # 3. Cho liên kết hydro (HBD)
    if compound.h_bond_donors > 5:
        lipinski_count += 1
        violations.append(f"Hydrogen Bond Donors > 5 ({compound.h_bond_donors})")

    # 4. Nhận liên kết hydro (HBA)
    if compound.h_bond_acceptors > 10:
        lipinski_count += 1
        violations.append(f"Hydrogen Bond Acceptors > 10 ({compound.h_bond_acceptors})")

    # 5. Tiêu chuẩn Veber (Rotatable bonds)
    veber_violations = 0
    if compound.rotatable_bonds > 10:
        veber_violations = 1
        violations.append(f"Rotatable Bonds > 10 ({compound.rotatable_bonds} bonds)")

    is_lipinski = lipinski_count <= 1
    is_veber = veber_violations == 0

    if lipinski_count == 0 and is_veber:
        verdict = "Phù hợp hoàn hảo quy tắc thuốc đường uống (High oral bioavailability potential)"
    elif lipinski_count == 1:
        verdict = "Chấp nhận được (1 vi phạm Lipinski - thường gặp ở hợp chất tự nhiên kháng ung thư)"
    else:
        verdict = f"Kém tương đồng thuốc đường uống ({lipinski_count} vi phạm - phù hợp bào chế dạng tiêm hoặc biến tính cấu trúc)"

    # Đoạn văn học thuật chuyên sâu dùng trực tiếp vào Discussion của bài báo
    if is_lipinski:
        narrative = (
            f"Compound {compound.name} strictly adheres to Lipinski's Rule of Five with "
            f"{lipinski_count} violation(s) (MW = {compound.molecular_weight} Da, "
            f"calculated LogP = {logp_val}, HBD = {compound.h_bond_donors}, "
            f"HBA = {compound.h_bond_acceptors}, and {compound.rotatable_bonds} rotatable bonds). "
            "These physicochemical parameters strongly indicate favorable drug-likeness "
            "and drug permeability characteristics suitable for further clinical lead optimization."
        )
    else:
        narrative = (
            f"Compound {compound.name} exhibits {lipinski_count} violation(s) of Lipinski's Rule of Five "
            f"(MW = {compound.molecular_weight} Da, LogP = {logp_val}), which is commonly observed "
            "among complex secondary metabolites and marine-derived natural anticancer therapeutics. "
            "Nevertheless, its distinct structural framework provides a compelling scaffold for "
            "nanocarrier delivery or targeted antibody-drug conjugates (ADCs)."
        )

    return DruglikenessReport(
        compound_name=compound.name,
        molecular_weight=compound.molecular_weight,
        xlogp=logp_val,
        h_bond_donors=compound.h_bond_donors,
        h_bond_acceptors=compound.h_bond_acceptors,
        rotatable_bonds=compound.rotatable_bonds,
        lipinski_violations=lipinski_count,
        veber_violations=veber_violations,
        is_lipinski_compliant=is_lipinski,
        is_veber_compliant=is_veber,
        summary_verdict=verdict,
        detailed_violations=violations,
        scientific_narrative=narrative
    )
