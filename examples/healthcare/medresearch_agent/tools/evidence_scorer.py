"""
Evidence Scorer - Assess the quality and strength of medical research

Evaluates studies based on design, sample size, methodology, and other factors.
"""

import re
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class EvidenceScorer:
    """Score the quality and strength of medical research evidence."""

    def __init__(self):
        """Initialize scorer with evidence hierarchy and criteria."""
        # Evidence hierarchy (higher = stronger evidence)
        self.study_type_scores = {
            "Systematic Review": 95,
            "Meta-Analysis": 90,
            "Randomized Controlled Trial": 85,
            "Cohort Study": 65,
            "Case-Control Study": 55,
            "Cross-Sectional Study": 45,
            "Case Series": 35,
            "Case Report": 25,
            "Observational Study": 50,
            "Expert Opinion": 15,
        }

    def score_paper(self, paper_data: Dict[str, Any]) -> int:
        """
        Calculate overall evidence quality score (0-100).

        Args:
            paper_data: Dictionary containing paper information

        Returns:
            Quality score from 0-100
        """
        score = 0
        max_score = 100

        # Component scores
        study_type_score = self._score_study_type(paper_data.get("study_type", ""))
        sample_size_score = self._score_sample_size(paper_data.get("sample_size", ""))
        recency_score = self._score_recency(paper_data.get("year", 2024))
        methodology_score = self._score_methodology(paper_data.get("full_text", ""))
        peer_review_score = self._score_peer_review(paper_data.get("full_text", ""))

        # Weighted combination
        score = (
            study_type_score * 0.35
            + sample_size_score * 0.25
            + methodology_score * 0.20
            + recency_score * 0.10
            + peer_review_score * 0.10
        )

        final_score = min(int(score), max_score)

        logger.info(f"Evidence score calculated: {final_score}/100")
        return final_score

    def _score_study_type(self, study_type: str) -> int:
        """Score based on study design type."""
        return self.study_type_scores.get(study_type, 40)

    def _score_sample_size(self, sample_size: str) -> int:
        """Score based on study sample size."""
        try:
            # Extract numeric value
            size = int(re.search(r"\d+", str(sample_size)).group())

            if size >= 5000:
                return 100
            elif size >= 1000:
                return 85
            elif size >= 500:
                return 70
            elif size >= 200:
                return 55
            elif size >= 100:
                return 40
            elif size >= 50:
                return 25
            else:
                return 15

        except (AttributeError, ValueError):
            # Sample size not specified or invalid
            return 30

    def _score_recency(self, year: int) -> int:
        """Score based on publication recency."""
        current_year = 2024

        if year >= current_year:
            return 100
        elif year >= current_year - 2:
            return 90
        elif year >= current_year - 5:
            return 75
        elif year >= current_year - 10:
            return 50
        else:
            return 25

    def _score_methodology(self, text: str) -> int:
        """Score based on methodological rigor indicators."""
        score = 50  # Base score
        text_lower = text.lower()

        # Positive indicators
        positive_indicators = {
            "double-blind": 15,
            "randomized": 10,
            "placebo-controlled": 10,
            "multi-center": 8,
            "prospective": 5,
            "intention-to-treat": 5,
            "statistical analysis plan": 5,
            "power calculation": 5,
        }

        for indicator, points in positive_indicators.items():
            if indicator in text_lower:
                score += points

        # Negative indicators (red flags)
        negative_indicators = {
            "conflicts of interest": -10,
            "industry-funded": -5,
            "small sample": -5,
            "limited by": -3,
        }

        for indicator, points in negative_indicators.items():
            if indicator in text_lower:
                score += points

        return max(0, min(score, 100))

    def _score_peer_review(self, text: str) -> int:
        """Score based on peer review and publication quality indicators."""
        score = 50
        text_lower = text.lower()

        # High-quality journal indicators
        if any(term in text_lower for term in ["new england journal", "lancet", "jama", "bmj", "nature medicine"]):
            score += 40

        # Peer review indicators
        if "peer-reviewed" in text_lower or "peer reviewed" in text_lower:
            score += 20

        # Preprint warning
        if "preprint" in text_lower or "not peer-reviewed" in text_lower:
            score -= 30

        return max(0, min(score, 100))

    def identify_biases(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify potential biases in the study.

        Args:
            paper_data: Dictionary containing paper information

        Returns:
            Dictionary with identified biases and risk levels
        """
        text = paper_data.get("full_text", "").lower()
        biases = {
            "selection_bias": self._check_selection_bias(text),
            "publication_bias": self._check_publication_bias(text),
            "funding_bias": self._check_funding_bias(text),
            "confirmation_bias": self._check_confirmation_bias(text),
            "overall_risk": "Low",
        }

        # Determine overall risk
        risk_count = sum(1 for v in biases.values() if v == "High")
        if risk_count >= 2:
            biases["overall_risk"] = "High"
        elif risk_count == 1:
            biases["overall_risk"] = "Medium"

        return biases

    def _check_selection_bias(self, text: str) -> str:
        """Check for selection bias indicators."""
        red_flags = [
            "convenience sample",
            "voluntary participation",
            "self-selected",
            "non-random",
        ]

        if any(flag in text for flag in red_flags):
            return "High"

        if "random" in text or "stratified" in text:
            return "Low"

        return "Medium"

    def _check_publication_bias(self, text: str) -> str:
        """Check for publication bias indicators."""
        if "negative results" in text or "null findings" in text:
            return "Low"  # Good sign - reporting negative results

        if "positive results" in text and "significant" in text:
            return "Medium"  # Could be selective reporting

        return "Low"

    def _check_funding_bias(self, text: str) -> str:
        """Check for funding-related bias."""
        funding_red_flags = [
            "sponsored by",
            "industry-funded",
            "pharmaceutical company",
            "grant from",
        ]

        if any(flag in text for flag in funding_red_flags):
            if "conflicts of interest" in text or "no conflicts" in text:
                return "Low"  # Disclosed conflicts
            else:
                return "High"  # Undisclosed potential conflicts

        return "Low"

    def _check_confirmation_bias(self, text: str) -> str:
        """Check for confirmation bias indicators."""
        # Look for balanced discussion of limitations
        if "limitations" in text and len(re.findall(r"limit", text)) >= 2:
            return "Low"

        # Look for one-sided conclusions
        if "clearly demonstrates" in text or "definitively shows" in text:
            return "Medium"

        return "Low"

    def generate_quality_report(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive quality assessment report.

        Args:
            paper_data: Dictionary containing paper information

        Returns:
            Detailed quality report
        """
        overall_score = self.score_paper(paper_data)
        biases = self.identify_biases(paper_data)

        # Determine quality grade
        if overall_score >= 85:
            grade = "A - Excellent"
        elif overall_score >= 70:
            grade = "B - Good"
        elif overall_score >= 55:
            grade = "C - Fair"
        elif overall_score >= 40:
            grade = "D - Poor"
        else:
            grade = "F - Very Poor"

        report = {
            "overall_score": overall_score,
            "grade": grade,
            "study_type": paper_data.get("study_type", "Unknown"),
            "sample_size": paper_data.get("sample_size", "Not specified"),
            "year": paper_data.get("year", "Unknown"),
            "biases": biases,
            "strengths": self._identify_strengths(paper_data),
            "weaknesses": self._identify_weaknesses(paper_data),
            "confidence_level": self._calculate_confidence(overall_score, biases),
        }

        return report

    def _identify_strengths(self, paper_data: Dict[str, Any]) -> List[str]:
        """Identify study strengths."""
        strengths = []
        text = paper_data.get("full_text", "").lower()

        if "randomized controlled trial" in paper_data.get("study_type", ""):
            strengths.append("Gold standard study design (RCT)")

        try:
            size = int(re.search(r"\d+", str(paper_data.get("sample_size", ""))).group())
            if size >= 500:
                strengths.append(f"Large sample size (n={size})")
        except (AttributeError, ValueError):
            pass

        if "double-blind" in text:
            strengths.append("Double-blind methodology reduces bias")

        if "multi-center" in text:
            strengths.append("Multi-center design improves generalizability")

        if paper_data.get("year", 0) >= 2020:
            strengths.append("Recent publication")

        return strengths[:5]

    def _identify_weaknesses(self, paper_data: Dict[str, Any]) -> List[str]:
        """Identify study weaknesses."""
        weaknesses = []
        text = paper_data.get("full_text", "").lower()

        limitations = paper_data.get("limitations", [])
        if limitations:
            weaknesses.extend(limitations[:2])

        try:
            size = int(re.search(r"\d+", str(paper_data.get("sample_size", ""))).group())
            if size < 100:
                weaknesses.append(f"Small sample size (n={size})")
        except (AttributeError, ValueError):
            weaknesses.append("Sample size not clearly specified")

        if "retrospective" in text:
            weaknesses.append("Retrospective design limits causality claims")

        if "single-center" in text or "single center" in text:
            weaknesses.append("Single-center study limits generalizability")

        return weaknesses[:5]

    def _calculate_confidence(self, score: int, biases: Dict[str, str]) -> str:
        """Calculate overall confidence level in findings."""
        if score >= 80 and biases["overall_risk"] == "Low":
            return "High confidence"
        elif score >= 60 and biases["overall_risk"] in ["Low", "Medium"]:
            return "Moderate confidence"
        elif score >= 40:
            return "Low confidence"
        else:
            return "Very low confidence"
