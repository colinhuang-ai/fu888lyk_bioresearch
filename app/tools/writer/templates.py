"""
Bộ khung sườn (Templates) & Prompts chuẩn cho bài báo khoa học y sinh / hóa dược ISI/Scopus (Q1/Q2).
Áp dụng cho các tạp chí: Journal of Natural Products, European Journal of Medicinal Chemistry, Bioorganic Chemistry.
"""

from typing import Dict, Any, List

RESEARCH_PAPER_STRUCTURE = {
    "sections": [
        "Title",
        "Abstract & Keywords",
        "1. Introduction",
        "2. Results and Discussion",
        "   2.1. Isolation, Dereplication and Structural Elucidation",
        "   2.2. In Vitro Cytotoxicity Against Human Cancer Cell Lines",
        "   2.3. Mechanism of Action: Apoptosis Induction and Cell Cycle Arrest",
        "   2.4. Mitochondrial Membrane Depolarization and ROS Generation",
        "   2.5. Western Blot Verification of Apoptotic Cascade (Caspase-3, PARP, Bax/Bcl-2)",
        "   2.6. In Silico Molecular Docking and Drug-Likeness Evaluation",
        "3. Experimental Section (Materials and Methods)",
        "   3.1. General Experimental Procedures",
        "   3.2. Microbial Fermentation and Extraction",
        "   3.3. Cell Culture and MTT Cytotoxicity Assays",
        "   3.4. Flow Cytometry Analysis (Annexin V-FITC/PI & Cell Cycle)",
        "   3.5. Western Blotting Protocol",
        "4. Conclusion",
        "References"
    ]
}

SYSTEM_SCIENTIFIC_WRITER_PROMPT = """You are an elite principal investigator and senior corresponding author specializing in natural products chemistry, microbial secondary metabolites, and cancer molecular pharmacology.
Your task is to synthesize high-impact, rigorous scientific manuscripts tailored for premier journals such as Journal of Natural Products, ACS Chemical Biology, or European Journal of Medicinal Chemistry.

Writing Guidelines:
1. Academic Rigor: Use precise biochemical and pharmacological nomenclature (e.g., IC50 values with standard errors, micromolar concentrations, cleaved caspase cascades, mitochondrial membrane potential ΔΨm).
2. Logical Flow: Progress systematically from microbial origin -> dereplication & chemical structure -> cytotoxic efficacy -> deep molecular mechanism (MoA).
3. Literature Citations: Ground every assertion in the provided reference context with in-text scientific citations [1], [2].
4. Objective Tone: Maintain an impartial, measured, and evidence-based voice. Avoid colloquialisms or unsubstantiated hyperbole.
"""
