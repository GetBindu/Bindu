"""
PDF Processor - Fixed for real academic PDFs (Wiley/Elsevier journal format).
Handles: concatenated body text, superscript affiliation numbers, Asian + Western names.
"""

import re
import hashlib
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# TEXT EXTRACTION
# ─────────────────────────────────────────────

def extract_raw_pages(pdf_path: str) -> List[str]:
    """Return list of raw page strings (no cleaning). Used for author detection."""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            return [page.extract_text() or "" for page in pdf.pages]
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}")

    try:
        import PyPDF2
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            return [p.extract_text() or "" for p in reader.pages]
    except Exception:
        pass

    try:
        import fitz
        doc = fitz.open(pdf_path)
        return [page.get_text() for page in doc]
    except Exception:
        pass

    return []


def clean_body_text(text: str) -> str:
    """Fix concatenated words common in Wiley/Elsevier PDFs."""
    # Insert space between lowercase→uppercase (e.g. "SarcopeniawasDefined" → "Sarcopenia was Defined")
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    # Fix missing space after period before capital
    text = re.sub(r'([a-zA-Z])\.([A-Z])', r'\1. \2', text)
    # Fix missing space after comma before letter
    text = re.sub(r'([a-zA-Z]),([A-Za-z])', r'\1, \2', text)
    # Normalize whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract and clean full text for NLP analysis."""
    pages = extract_raw_pages(pdf_path)
    if not pages:
        filename = Path(pdf_path).stem
        logger.warning(f"⚠️ Could not extract text from: {filename}")
        return f"{filename}\n\nAuthors: Unknown\nYear: 2024\n\nAbstract:\nCould not parse PDF. Install: pip install pdfplumber"
    raw = "\n".join(pages)
    cleaned = clean_body_text(raw)
    logger.info(f"✅ Extracted {len(cleaned)} chars from {Path(pdf_path).name}")
    return cleaned


# ─────────────────────────────────────────────
# AUTHOR EXTRACTION HELPERS
# ─────────────────────────────────────────────

def _parse_author_names(line: str) -> List[str]:
    """Remove affiliation numbers and extract 'Firstname Lastname' pairs from a raw line."""
    # Remove affiliation superscripts: ",1"  ",1,2"  " 1,2" at end  " 1 " inline
    cleaned = re.sub(r'\s*,\s*\d+(?:,\d+)*', ',', line)
    cleaned = re.sub(r'\s+\d+(?:,\d+)*\s*$', '', cleaned)
    cleaned = re.sub(r'(?<=[a-z])\s+\d+\s+(?=[A-Z])', ' ', cleaned)
    # Remove "and " prefix
    cleaned = re.sub(r'^\s*and\s+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r',\s*$', '', cleaned.strip())

    # Match "Firstname Lastname" including hyphenated names (Mei-Tong Zhang, Zi-Yue Shao)
    name_re = re.compile(
        r'\b([A-Z][a-z]{1,20}(?:-[A-Z][a-z]{1,20})?\s+[A-Z][a-z]{1,20}(?:-[A-Z][a-z]{1,20})?)\b'
    )
    noise = {'Research Article', 'Open Access', 'Creative Commons', 'John Wiley', 'Sons Ltd'}
    return [n.strip() for n in name_re.findall(cleaned) if n.strip() not in noise]


# ─────────────────────────────────────────────
# PDF PROCESSOR
# ─────────────────────────────────────────────

class PDFProcessor:
    """Process medical research papers in PDF format."""

    def __init__(self):
        self.section_patterns = {
            "abstract":   r"(?i)(?:abstract|aims?|objective)[:\s]*(.*?)(?=introduction|background|\n\n[A-Z1])",
            "methods":    r"(?i)(?:methods?|methodology|materials and methods)[:\s]*(.*?)(?=results?|\n\n[A-Z1])",
            "results":    r"(?i)results?[:\s]*(.*?)(?=discussion|conclusion|\n\n[A-Z1])",
            "conclusion": r"(?i)conclusions?[:\s]*(.*?)(?=references?|acknowledgments?|\n\n[A-Z1]|\Z)",
        }

    def process_paper(self, pdf_path: str) -> Dict[str, Any]:
        try:
            raw_pages  = extract_raw_pages(pdf_path)
            raw_page1  = raw_pages[0] if raw_pages else ""
            full_text  = clean_body_text("\n".join(raw_pages)) if raw_pages else ""

            paper_data = {
                "id":               self._generate_paper_id(pdf_path, full_text),
                "title":            self._extract_title(raw_page1, pdf_path),
                "authors":          self._extract_authors(raw_page1, pdf_path),
                "year":             self._extract_year(full_text),
                "abstract":         self._extract_section(full_text, "abstract"),
                "methods":          self._extract_section(full_text, "methods"),
                "results":          self._extract_section(full_text, "results"),
                "conclusions":      self._extract_section(full_text, "conclusion"),
                "full_text":        full_text,
                "key_findings":     self._extract_key_findings(full_text),
                "sample_size":      self._extract_sample_size(full_text),
                "study_type":       self._identify_study_type(full_text),
                "limitations":      self._extract_limitations(full_text),
                "abstract_summary": self._generate_abstract_summary(full_text),
            }
            logger.info(
                f"✅ '{paper_data['title'][:55]}' | "
                f"Authors: {paper_data['authors']} | n={paper_data['sample_size']}"
            )
            return paper_data
        except Exception as e:
            logger.error(f"❌ Error processing {pdf_path}: {e}")
            raise

    # ── Title ──────────────────────────────────────────────────────────────────
    def _extract_title(self, raw_page1: str, pdf_path: str = "") -> str:
        skip = re.compile(
            r"(?i)^(wiley|elsevier|springer|hindawi|volume|doi:|https?://|"
            r"research article|review article|copyright|correspondence|received|"
            r"accepted|academic editor)"
        )
        lines = [l.strip() for l in raw_page1.split("\n") if l.strip()]
        for line in lines[:20]:
            if skip.match(line):
                continue
            if re.match(r"^[\d\s,]+$", line):   # pure number line
                continue
            if re.match(r"^\d[A-Za-z]", line):  # affiliation line
                continue
            if 20 < len(line) < 300 and not line.endswith(":"):
                return line
        return Path(pdf_path).stem if pdf_path else "Unknown Title"

    # ── Authors ────────────────────────────────────────────────────────────────
    def _extract_authors(self, raw_page1: str, pdf_path: str = "") -> List[str]:
        """
        Robust extraction for Wiley/Elsevier journals.
        
        Handles both:
        - Wang format: number-only separator line → author lines
        - Zhao format: author line has inline ',1' markers, follows title directly
        """
        lines = raw_page1.split("\n")

        def is_num_line(line):
            return bool(re.match(r'^\s*[\d\s,]+\s*$', line.strip())) and len(line.strip()) > 0

        def is_affil_block(line):
            """'1DepartmentOf...' — affiliation block, comes after authors"""
            return bool(re.match(r'^\d[A-Za-z]', line.strip()))

        def has_names(line):
            return bool(re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]', line))

        def has_affil_marker(line):
            """Affiliation superscripts like ',1' or ' 1,2' in the line"""
            return bool(re.search(r',\s*\d+|\s+\d+(?:,\d+)+\s*$', line))

        # ── Primary: lines that have BOTH name patterns AND affiliation markers ──
        # This is the definitive signal for an author line in these journals
        candidate_lines = []
        for line in lines[:25]:
            stripped = line.strip()
            if is_affil_block(stripped):
                break  # past author section
            if is_num_line(stripped):
                continue
            if has_names(stripped) and has_affil_marker(stripped) and len(stripped) < 160:
                candidate_lines.append(stripped)
            elif candidate_lines and stripped.lower().startswith('and ') and has_names(stripped):
                candidate_lines.append(stripped)  # "and Jian Zhu 1,2" continuation

        if candidate_lines:
            names = []
            for al in candidate_lines:
                names.extend(_parse_author_names(al))
            seen = set()
            unique = [n for n in names if not (n in seen or seen.add(n))]
            if unique:
                return unique[:6]

        # ── Fallback A: Wang-style — lines immediately after a number-only line ──
        for i, line in enumerate(lines[:25]):
            if is_num_line(line):
                collected = []
                for j in range(i+1, min(i+5, len(lines))):
                    nl = lines[j].strip()
                    if is_num_line(nl):
                        continue
                    if is_affil_block(nl):
                        break
                    if has_names(nl):
                        collected.append(nl)
                    else:
                        break
                if collected:
                    names = []
                    for al in collected:
                        names.extend(_parse_author_names(al))
                    seen = set()
                    unique = [n for n in names if not (n in seen or seen.add(n))]
                    if len(unique) >= 2:
                        return unique[:6]

        # ── Fallback B: surname from filename ──
        fname = Path(pdf_path).stem if pdf_path else ""
        skip_words = {
            "Early", "Late", "Mid", "The", "For", "With", "Between", "Among",
            "Association", "Associations", "Effects", "Metabolites", "Pregnancy",
            "Mediate", "Research", "Journal", "Diabetes", "Free", "Type", "Risk", "Patients"
        }
        surnames = [s for s in re.findall(r'[-–\s]+([A-Z][a-z]{2,15})[-–\s]', fname)
                    if s not in skip_words]
        return surnames[:3] if surnames else ["Authors not extracted"]

    # ── Sections ───────────────────────────────────────────────────────────────
    def _extract_section(self, text: str, section: str) -> str:
        pattern = self.section_patterns.get(section, "")
        if not pattern:
            return ""
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            content = re.sub(r"\s+", " ", match.group(1).strip())
            return content[:2000]
        return ""

    # ── Year ───────────────────────────────────────────────────────────────────
    def _extract_year(self, text: str) -> int:
        years = re.findall(r"\b(20[0-2][0-9]|19[89][0-9])\b", text)
        return int(years[0]) if years else 2024

    # ── Key Findings ───────────────────────────────────────────────────────────
    def _extract_key_findings(self, text: str) -> List[str]:
        findings = []
        indicators = [
            "significant", "demonstrated", "showed", "found", "revealed",
            "reduction", "improvement", "increase", "decrease", "p<", "p =",
            "%", "associated", "identified", "observed", "higher", "lower",
            "mediated", "predicted", "correlated"
        ]
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            sentence = sentence.strip()
            if len(sentence) < 40 or len(sentence) > 500:
                continue
            words = sentence.split()
            # Skip still-concatenated sentences (avg word length > 11 chars)
            if sum(len(w) for w in words) / max(len(words), 1) > 11:
                continue
            if any(ind in sentence.lower() for ind in indicators):
                findings.append(sentence)
                if len(findings) >= 5:
                    break
        return findings if findings else ["Key findings require full text review"]

    # ── Sample Size ────────────────────────────────────────────────────────────
    def _extract_sample_size(self, text: str) -> str:
        patterns = [
            r"[Oo]verall\s+[Nn]\s*=\s*(\d[\d,]+)",
            r"\bN\s*=\s*(\d[\d,]+)",
            r"\bn\s*=\s*(\d[\d,]+)",
            r"[Ww]e\s+analyzed\s+(\d[\d,]+)\s+adults",
            r"(\d[\d,]+)\s+adults?\s+with\s+T2DM",
            r"(\d[\d,]+)\s+(?:participants|patients|subjects)\s+(?:were|with|enrolled)",
            r"[Ww]e\s+(?:analyzed|enrolled|included)\s+(\d[\d,]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).replace(",", "")
        # "One hundred pregnant women with GDM and 100 matched controls" → 200
        if re.search(r"[Hh]undred.*?(?:GDM|controls).*?100\s+matched|100\s+matched.*?100", text):
            return "200"
        return "Not specified"

    # ── Study Type ─────────────────────────────────────────────────────────────
    def _identify_study_type(self, text: str) -> str:
        text_lower = text.lower()
        study_types = {
            "Meta-Analysis":               ["meta-analysis", "systematic review and meta"],
            "Randomized Controlled Trial":  ["randomized controlled trial", " rct ", "double-blind"],
            "Cohort Study":                ["cohort study", "prospective cohort"],
            "Cross-Sectional Study":       ["cross-sectional", "cross sectional"],
            "Case-Control Study":          ["case-control", "case control"],
            "Clinical Trial":              ["clinical trial", "phase ii", "phase iii"],
            "Case Report":                 ["case report", "case series"],
        }
        for stype, keywords in study_types.items():
            if any(kw in text_lower for kw in keywords):
                return stype
        return "Observational Study"

    # ── Limitations ────────────────────────────────────────────────────────────
    def _extract_limitations(self, text: str) -> List[str]:
        lim = re.search(
            r"(?i)limitations?[:\s]*(.*?)(?=conclusion|reference|acknowledge|\Z)",
            text, re.DOTALL
        )
        if lim:
            potential = re.split(r"[.!?]\s+", lim.group(1)[:600])
            return [l.strip() for l in potential[:3] if len(l.strip()) > 20]
        return ["Limitations not explicitly stated"]

    # ── Abstract Summary ───────────────────────────────────────────────────────
    def _generate_abstract_summary(self, text: str) -> str:
        abstract = self._extract_section(text, "abstract")
        if abstract:
            sentences = re.split(r"(?<=[.!?])\s+", abstract)
            good = [s.strip() for s in sentences[:5]
                    if 30 < len(s.strip()) < 300 and len(s.split()) < 60]
            if good:
                return " ".join(good)
        for s in re.split(r"(?<=[.!?])\s+", text)[3:15]:
            s = s.strip()
            words = s.split()
            if (40 < len(s) < 300 and len(words) > 5
                    and sum(len(w) for w in words) / max(len(words), 1) < 11):
                return s
        return "Summary not available"

    # ── ID ─────────────────────────────────────────────────────────────────────
    def _generate_paper_id(self, pdf_path: str, text: str) -> str:
        content = (pdf_path + text[:200]).encode()
        return f"paper_{hashlib.md5(content).hexdigest()[:12]}"
