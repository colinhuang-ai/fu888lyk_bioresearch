"""Module phân tích dữ liệu y văn PubMed: trích xuất cơ chế hoạt động và tác dụng phụ."""

from collections import Counter
import re
from typing import Any, Dict, List, Tuple
import pandas as pd

# Từ điển các tác dụng phụ, độc tính và phản ứng bất lợi phổ biến trong nghiên cứu y sinh học
SIDE_EFFECT_KEYWORDS = [
    "hepatotoxicity", "liver injury", "nephrotoxicity", "renal toxicity",
    "cardiotoxicity", "heart failure", "arrhythmia", "qt prolongation",
    "neurotoxicity", "neuropathy", "headache",
    "rash", "dermatitis", "pruritus", "alopecia",
    "diarrhea", "nausea", "vomiting", "constipation", "gastrointestinal toxicity",
    "fatigue", "asthenia", "malaise",
    "hypertension", "hypotension",
    "anemia", "thrombocytopenia", "neutropenia", "leukopenia", "myelosuppression",
    "pneumonitis", "interstitial lung disease", "cough", "dyspnea",
    "drug resistance", "acquired resistance", "cross-resistance",
    "immunogenicity", "cytokine release syndrome", "infusion reaction",
    "weight loss", "anorexia", "edema"
]

# Từ điển các cơ chế hoạt động phân tử
MECHANISM_KEYWORDS = [
    "phosphorylation", "dephosphorylation",
    "kinase activity", "tyrosine kinase", "serine/threonine kinase",
    "inhibition", "competitive inhibition", "allosteric inhibition",
    "activation", "agonist", "antagonist",
    "dimerization", "oligomerization",
    "ligand binding", "receptor binding", "affinity",
    "downregulation", "upregulation",
    "ubiquitination", "proteasomal degradation",
    "conformational change", "cleavage",
    "signal transduction", "pathway activation",
    "apoptosis induction", "cell cycle arrest",
    "transcription factor", "gene expression",
    "cross-talk", "feedback loop"
]


class ProteinLiteratureAnalyzer:
    """Phân tích nội dung abstracts từ PubMed để phát hiện cơ chế và tác dụng phụ."""

    def __init__(self, side_effect_terms: List[str] = None, mechanism_terms: List[str] = None):
        self.side_effects = [t.lower() for t in (side_effect_terms or SIDE_EFFECT_KEYWORDS)]
        self.mechanisms = [t.lower() for t in (mechanism_terms or MECHANISM_KEYWORDS)]

    def extract_terms_frequency(self, df: pd.DataFrame, term_list: List[str]) -> Counter:
        """Đếm số lần xuất hiện của các từ khóa trong toàn bộ tập abstract và title."""
        counter = Counter()
        if df.empty or "abstract" not in df.columns:
            return counter

        text_corpus = (df["title"].fillna("") + " " + df["abstract"].fillna("")).str.lower()
        for term in term_list:
            # Tìm kiếm nguyên từ hoặc cụm từ
            pattern = r'\b' + re.escape(term) + r'\b'
            matches = text_corpus.apply(lambda x: len(re.findall(pattern, x)))
            total = matches.sum()
            if total > 0:
                counter[term] = int(total)

        return counter

    def analyze_side_effects(self, df: pd.DataFrame) -> List[Tuple[str, int]]:
        """Phân tích các hiệu ứng phụ xuất hiện nhiều nhất trong các bài báo."""
        counter = self.extract_terms_frequency(df, self.side_effects)
        return counter.most_common(15)

    def analyze_mechanisms(self, df: pd.DataFrame) -> List[Tuple[str, int]]:
        """Phân tích các cơ chế hoạt động được nhắc đến nhiều nhất."""
        counter = self.extract_terms_frequency(df, self.mechanisms)
        return counter.most_common(15)

    def extract_evidence_sentences(
        self,
        df: pd.DataFrame,
        keywords: List[str],
        max_sentences: int = 5
    ) -> List[Dict[str, str]]:
        """Trích xuất các câu chứa bằng chứng khoa học có kèm PMID dẫn chứng."""
        evidences = []
        if df.empty or "abstract" not in df.columns:
            return evidences

        patterns = [r'\b' + re.escape(k.lower()) + r'\b' for k in keywords]
        combined_regex = re.compile('|'.join(patterns), re.IGNORECASE)

        for _, row in df.iterrows():
            abstract = str(row.get("abstract", ""))
            pmid = str(row.get("pmid", ""))
            title = str(row.get("title", ""))
            year = str(row.get("year", ""))

            # Tách các câu theo dấu chấm
            sentences = re.split(r'(?<=[.!?])\s+', abstract)
            for s in sentences:
                s_clean = s.strip()
                if len(s_clean) > 30 and combined_regex.search(s_clean):
                    evidences.append({
                        "pmid": pmid,
                        "year": year,
                        "title": title,
                        "sentence": s_clean
                    })
                    if len(evidences) >= max_sentences:
                        return evidences

        return evidences

    def summarize_findings(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Tổng hợp toàn diện phát hiện từ các bài báo PubMed."""
        top_side_effects = self.analyze_side_effects(df)
        top_mechanisms = self.analyze_mechanisms(df)

        side_effect_evidence = self.extract_evidence_sentences(
            df,
            [t[0] for t in top_side_effects[:5]],
            max_sentences=6
        )
        mechanism_evidence = self.extract_evidence_sentences(
            df,
            [t[0] for t in top_mechanisms[:5]],
            max_sentences=6
        )

        # Thống kê xuất bản theo năm
        year_counts = {}
        if not df.empty and "year" in df.columns:
            year_series = df["year"].astype(str).str.extract(r'(\d{4})')[0].dropna()
            year_counts = year_series.value_counts().sort_index().to_dict()

        return {
            "total_articles": len(df),
            "top_side_effects": top_side_effects,
            "top_mechanisms": top_mechanisms,
            "side_effect_evidence": side_effect_evidence,
            "mechanism_evidence": mechanism_evidence,
            "publications_by_year": year_counts
        }
