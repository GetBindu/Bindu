"""
Medical NLP - Extract medical entities from research papers

Uses pattern matching and medical terminology to identify conditions,
medications, procedures, and other medical entities.
"""

import re
from typing import Dict, List, Set
import logging

logger = logging.getLogger(__name__)


class MedicalNLP:
    """Extract medical entities from text using pattern matching and terminology."""

    def __init__(self):
        """Initialize with medical terminology databases."""
        # In production, these would come from UMLS, SNOMED CT, or RxNorm
        # For now, we'll use representative examples
        self.conditions = {
            "diabetes",
            "type 2 diabetes",
            "type 1 diabetes",
            "hypertension",
            "cardiovascular disease",
            "heart failure",
            "stroke",
            "cancer",
            "obesity",
            "alzheimer's disease",
            "parkinson's disease",
            "asthma",
            "copd",
            "depression",
            "anxiety",
            "arthritis",
            "osteoporosis",
            "kidney disease",
            "liver disease",
        }

        self.medications = {
            "metformin",
            "insulin",
            "aspirin",
            "statins",
            "atorvastatin",
            "lisinopril",
            "losartan",
            "amlodipine",
            "warfarin",
            "clopidogrel",
            "levothyroxine",
            "albuterol",
            "prednisone",
            "ibuprofen",
            "acetaminophen",
            "morphine",
            "omeprazole",
            "sertraline",
            "fluoxetine",
        }

        self.procedures = {
            "surgery",
            "angioplasty",
            "coronary artery bypass",
            "catheterization",
            "endoscopy",
            "colonoscopy",
            "biopsy",
            "mri",
            "ct scan",
            "x-ray",
            "ultrasound",
            "blood test",
            "ecg",
            "eeg",
            "dialysis",
            "chemotherapy",
            "radiation therapy",
            "physical therapy",
        }

        self.lab_values = {
            "hba1c",
            "glucose",
            "cholesterol",
            "ldl",
            "hdl",
            "triglycerides",
            "blood pressure",
            "heart rate",
            "creatinine",
            "egfr",
            "ast",
            "alt",
            "hemoglobin",
            "white blood cell",
            "platelet",
        }

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract all medical entities from text.

        Args:
            text: Medical text to analyze

        Returns:
            Dictionary with entity types and extracted entities
        """
        text_lower = text.lower()

        entities = {
            "conditions": self._extract_conditions(text_lower),
            "medications": self._extract_medications(text_lower),
            "procedures": self._extract_procedures(text_lower),
            "lab_values": self._extract_lab_values(text_lower),
            "dosages": self._extract_dosages(text),
            "statistics": self._extract_statistics(text),
        }

        logger.info(
            f"Extracted entities: {sum(len(v) for v in entities.values())} total"
        )
        return entities

    def _extract_conditions(self, text: str) -> List[str]:
        """Extract medical conditions/diagnoses."""
        found_conditions = set()

        for condition in self.conditions:
            if condition in text:
                found_conditions.add(condition.title())

        # Also look for common patterns
        # Pattern: "diagnosed with X", "suffering from X", "patients with X"
        diagnosis_patterns = [
            r"diagnosed with ([a-z\s]{3,30})",
            r"suffering from ([a-z\s]{3,30})",
            r"patients with ([a-z\s]{3,30})",
            r"history of ([a-z\s]{3,30})",
        ]

        for pattern in diagnosis_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                match = match.strip()
                if len(match) > 3 and match not in ["the", "and", "or"]:
                    found_conditions.add(match.title())

        return sorted(list(found_conditions))[:10]

    def _extract_medications(self, text: str) -> List[str]:
        """Extract medication names."""
        found_medications = set()

        for medication in self.medications:
            if medication in text:
                found_medications.add(medication.title())

        # Look for dosage patterns which often indicate medications
        # Pattern: "Drug XXXmg"
        dosage_pattern = r"([a-z]{3,20})\s*\d+\s*(?:mg|mcg|g|ml)"
        matches = re.findall(dosage_pattern, text)
        for match in matches:
            if len(match) > 3:
                found_medications.add(match.title())

        return sorted(list(found_medications))[:10]

    def _extract_procedures(self, text: str) -> List[str]:
        """Extract medical procedures."""
        found_procedures = set()

        for procedure in self.procedures:
            if procedure in text:
                found_procedures.add(procedure.title())

        return sorted(list(found_procedures))[:10]

    def _extract_lab_values(self, text: str) -> List[str]:
        """Extract laboratory test values."""
        found_labs = set()

        for lab in self.lab_values:
            if lab in text:
                found_labs.add(lab.upper() if len(lab) <= 5 else lab.title())

        return sorted(list(found_labs))[:10]

    def _extract_dosages(self, text: str) -> List[str]:
        """Extract medication dosages."""
        # Pattern: number + unit
        dosage_pattern = r"\b(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|units?|iu)(?:\s+(?:once|twice|three times)?\s*(?:daily|per day|bid|tid|qid)?)?)\b"

        matches = re.findall(dosage_pattern, text, re.IGNORECASE)
        unique_dosages = list(set(matches))

        return unique_dosages[:10]

    def _extract_statistics(self, text: str) -> List[str]:
        """Extract statistical findings (p-values, percentages, etc.)."""
        statistics = []

        # P-values
        p_values = re.findall(r"p\s*[<>=]\s*0\.\d+", text, re.IGNORECASE)
        statistics.extend(p_values[:5])

        # Percentages with context
        percentage_pattern = r"(\d+(?:\.\d+)?%)\s+(?:of|in|showed|demonstrated)"
        percentages = re.findall(percentage_pattern, text)
        statistics.extend(percentages[:5])

        # Confidence intervals
        ci_pattern = r"(?:95%\s+)?(?:CI|confidence interval)[:\s]+(\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?)"
        cis = re.findall(ci_pattern, text, re.IGNORECASE)
        statistics.extend(cis[:3])

        return statistics[:10]

    def identify_adverse_events(self, text: str) -> List[str]:
        """Identify mentions of adverse events or side effects."""
        adverse_terms = [
            "adverse",
            "side effect",
            "complication",
            "toxicity",
            "reaction",
            "withdrawal",
        ]

        text_lower = text.lower()
        adverse_events = []

        for term in adverse_terms:
            if term in text_lower:
                # Get surrounding context
                pattern = rf"(.{{0,50}}{term}.{{0,50}})"
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                adverse_events.extend(matches[:2])

        return adverse_events[:5]

    def extract_inclusion_exclusion_criteria(self, text: str) -> Dict[str, List[str]]:
        """Extract study inclusion and exclusion criteria."""
        criteria = {"inclusion": [], "exclusion": []}

        # Find inclusion criteria section
        inclusion_section = re.search(
            r"(?i)inclusion criteria[:\s]*(.*?)(?=exclusion|methods|\n\n)",
            text,
            re.DOTALL,
        )
        if inclusion_section:
            criteria["inclusion"] = self._parse_criteria_list(inclusion_section.group(1))

        # Find exclusion criteria section
        exclusion_section = re.search(
            r"(?i)exclusion criteria[:\s]*(.*?)(?=methods|results|\n\n)",
            text,
            re.DOTALL,
        )
        if exclusion_section:
            criteria["exclusion"] = self._parse_criteria_list(exclusion_section.group(1))

        return criteria

    def _parse_criteria_list(self, text: str) -> List[str]:
        """Parse criteria text into individual criteria."""
        # Split by bullet points, numbers, or new lines
        criteria = re.split(r"[•\-\n]\s*|\d+\.\s+", text)
        criteria = [c.strip() for c in criteria if len(c.strip()) > 10]
        return criteria[:5]

    def calculate_readability_score(self, text: str) -> Dict[str, any]:
        """
        Calculate readability metrics for medical text.

        Returns:
            Dictionary with readability scores
        """
        words = re.findall(r"\b\w+\b", text)
        sentences = re.split(r"[.!?]+", text)

        if not words or not sentences:
            return {"score": 0, "level": "Unknown"}

        avg_words_per_sentence = len(words) / len(sentences)
        avg_chars_per_word = sum(len(word) for word in words) / len(words)

        # Simplified readability score (0-100)
        # Lower score = harder to read
        score = max(0, 100 - (avg_words_per_sentence * 2) - (avg_chars_per_word * 5))

        if score > 80:
            level = "Easy to read"
        elif score > 60:
            level = "Moderate"
        elif score > 40:
            level = "Difficult"
        else:
            level = "Very difficult (technical)"

        return {
            "score": round(score, 1),
            "level": level,
            "avg_words_per_sentence": round(avg_words_per_sentence, 1),
            "avg_chars_per_word": round(avg_chars_per_word, 1),
        }
