"""
Paper Synthesizer - Compare and synthesize findings across multiple research papers

This is the "surprise feature" that makes this agent stand out.
"""

import re
from typing import Dict, List, Any, Set
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class PaperSynthesizer:
    """Synthesize findings from multiple research papers."""

    def __init__(self):
        """Initialize synthesizer."""
        self.agreement_threshold = 0.7  # 70% agreement = consensus

    def synthesize(self, papers: List[Dict[str, Any]], topic: str) -> Dict[str, Any]:
        """
        Perform multi-paper synthesis and meta-analysis.

        Args:
            papers: List of paper data dictionaries
            topic: Research topic for context

        Returns:
            Synthesis report with consensus findings and contradictions
        """
        logger.info(f"Synthesizing {len(papers)} papers on topic: {topic}")

        synthesis = {
            "topic": topic,
            "paper_count": len(papers),
            "consensus_findings": self._find_consensus(papers),
            "agreements": self._identify_agreements(papers),
            "contradictions": self._identify_contradictions(papers),
            "overall_evidence_strength": self._calculate_overall_evidence(papers),
            "confidence_level": self._determine_confidence(papers),
            "research_gaps": self._identify_research_gaps(papers),
            "temporal_trends": self._analyze_temporal_trends(papers),
            "study_quality_distribution": self._analyze_quality_distribution(papers),
        }

        return synthesis

    def _find_consensus(self, papers: List[Dict[str, Any]]) -> List[str]:
        """Find consensus findings across papers."""
        # Extract all findings
        all_findings = []
        for paper in papers:
            findings = paper.get("key_findings", [])
            all_findings.extend(findings)

        # Use simple keyword matching to find similar findings
        # In production, use semantic similarity (embeddings)
        consensus = []

        # Common medical findings keywords
        finding_keywords = [
            "reduction",
            "improvement",
            "increase",
            "decrease",
            "significant",
            "effective",
            "efficacy",
            "safety",
            "adverse",
        ]

        for keyword in finding_keywords:
            matching_findings = [
                f for f in all_findings if keyword.lower() in f.lower()
            ]
            if len(matching_findings) >= len(papers) * 0.5:  # 50% of papers
                # This is a consensus finding
                consensus.append(
                    f"{keyword.title()} was consistently reported across "
                    f"{len(matching_findings)}/{len(papers)} studies"
                )

        if not consensus:
            consensus.append(
                "Limited consensus found - studies examined different aspects or outcomes"
            )

        return consensus[:5]

    def _identify_agreements(self, papers: List[Dict[str, Any]]) -> List[str]:
        """Identify areas where papers agree."""
        agreements = []

        # Check study types
        study_types = [p.get("study_type", "") for p in papers]
        type_counts = Counter(study_types)
        most_common_type = type_counts.most_common(1)[0]

        if most_common_type[1] >= len(papers) * 0.5:
            agreements.append(
                f"Study design: {most_common_type[1]}/{len(papers)} studies "
                f"used {most_common_type[0]}"
            )

        # Check for common medications/interventions
        all_medications = []
        for paper in papers:
            text = paper.get("full_text", "").lower()
            # Extract common drug names (simplified)
            meds = re.findall(r"\b(metformin|insulin|aspirin|statins)\b", text)
            all_medications.extend(meds)

        if all_medications:
            med_counts = Counter(all_medications)
            top_med = med_counts.most_common(1)[0]
            if top_med[1] >= 2:
                agreements.append(
                    f"Intervention: {top_med[0].title()} was studied "
                    f"in {top_med[1]} papers"
                )

        # Check for consistent sample size ranges
        sample_sizes = []
        for paper in papers:
            try:
                size = int(
                    re.search(r"\d+", str(paper.get("sample_size", ""))).group()
                )
                sample_sizes.append(size)
            except (AttributeError, ValueError):
                pass

        if sample_sizes:
            avg_size = sum(sample_sizes) / len(sample_sizes)
            agreements.append(
                f"Sample sizes: Average n={int(avg_size)} across studies"
            )

        return agreements if agreements else ["Limited methodological alignment"]

    def _identify_contradictions(self, papers: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Identify contradictions or conflicting findings."""
        contradictions = []

        # Check for opposing results (simplified approach)
        # In production, use NLP to detect negations and conflicts

        positive_terms = ["effective", "significant improvement", "reduced", "beneficial"]
        negative_terms = ["ineffective", "no significant", "no reduction", "no benefit"]

        positive_papers = []
        negative_papers = []

        for paper in papers:
            text = paper.get("full_text", "").lower()
            findings = " ".join(paper.get("key_findings", [])).lower()

            has_positive = any(term in text or term in findings for term in positive_terms)
            has_negative = any(term in text or term in findings for term in negative_terms)

            if has_positive:
                positive_papers.append(paper)
            if has_negative:
                negative_papers.append(paper)

        if positive_papers and negative_papers:
            contradictions.append(
                {
                    "issue": "Treatment efficacy",
                    "position_a": f"{len(positive_papers)} studies reported positive effects",
                    "position_b": f"{len(negative_papers)} studies reported limited/no effects",
                    "possible_reasons": "Different populations, dosages, or outcome measures",
                }
            )

        # Check for different optimal doses/protocols
        dose_patterns = re.findall(r"(\d+)\s*mg", " ".join([p.get("full_text", "") for p in papers]))
        if dose_patterns:
            unique_doses = set(dose_patterns)
            if len(unique_doses) > 2:
                contradictions.append(
                    {
                        "issue": "Optimal dosing",
                        "position_a": f"Doses ranging from {min(unique_doses)}-{max(unique_doses)}mg used",
                        "position_b": "No consensus on optimal therapeutic dose",
                        "possible_reasons": "Dose-response relationships not fully established",
                    }
                )

        return contradictions if contradictions else []

    def _calculate_overall_evidence(self, papers: List[Dict[str, Any]]) -> int:
        """Calculate overall evidence strength across all papers."""
        if not papers:
            return 0

        # Use evidence hierarchy
        study_weights = {
            "Meta-Analysis": 95,
            "Randomized Controlled Trial": 85,
            "Cohort Study": 65,
            "Case-Control Study": 55,
            "Observational Study": 50,
            "Case Report": 25,
        }

        total_weight = 0
        for paper in papers:
            study_type = paper.get("study_type", "Observational Study")
            weight = study_weights.get(study_type, 40)

            # Adjust for sample size
            try:
                size = int(re.search(r"\d+", str(paper.get("sample_size", ""))).group())
                if size >= 1000:
                    weight += 5
                elif size < 100:
                    weight -= 5
            except (AttributeError, ValueError):
                pass

            total_weight += weight

        overall_score = int(total_weight / len(papers))
        return min(overall_score, 100)

    def _determine_confidence(self, papers: List[Dict[str, Any]]) -> str:
        """Determine overall confidence in synthesized findings."""
        evidence_score = self._calculate_overall_evidence(papers)

        # Check for consistency
        study_types = [p.get("study_type", "") for p in papers]
        has_rcts = "Randomized Controlled Trial" in study_types
        consistency = len(set(study_types)) / len(papers)

        if evidence_score >= 80 and has_rcts and consistency < 0.5:
            return "High confidence - Strong, consistent evidence from quality studies"
        elif evidence_score >= 60 and len(papers) >= 3:
            return "Moderate confidence - Reasonable evidence but some limitations"
        elif evidence_score >= 40:
            return "Low confidence - Limited or inconsistent evidence"
        else:
            return "Very low confidence - Insufficient or poor quality evidence"

    def _identify_research_gaps(self, papers: List[Dict[str, Any]]) -> List[str]:
        """Identify gaps in research that need further study."""
        gaps = []

        # Check limitations mentioned across papers
        all_limitations = []
        for paper in papers:
            all_limitations.extend(paper.get("limitations", []))

        # Common gap keywords
        gap_keywords = {
            "long-term": "Long-term outcomes not adequately studied",
            "larger sample": "Larger sample sizes needed for robust conclusions",
            "diverse population": "More diverse populations should be included",
            "mechanism": "Underlying mechanisms not fully understood",
            "cost-effectiveness": "Cost-effectiveness analysis needed",
        }

        for keyword, gap_description in gap_keywords.items():
            if any(keyword in lim.lower() for lim in all_limitations):
                gaps.append(gap_description)

        # Check for missing study types
        study_types = [p.get("study_type", "") for p in papers]
        if "Randomized Controlled Trial" not in study_types:
            gaps.append("High-quality RCTs needed to establish causality")

        if len(papers) < 10:
            gaps.append("More studies needed for definitive meta-analysis")

        return gaps[:5] if gaps else ["No major research gaps identified"]

    def _analyze_temporal_trends(self, papers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends over time in the research."""
        years = [p.get("year", 2024) for p in papers]

        if not years:
            return {"trend": "Unable to determine", "span": "Unknown"}

        year_range = max(years) - min(years)

        if year_range <= 2:
            trend = "Recent cluster of studies"
        elif year_range <= 5:
            trend = "Emerging research area"
        else:
            trend = "Well-established research area"

        return {
            "trend": trend,
            "span": f"{min(years)}-{max(years)}",
            "recent_activity": f"{sum(1 for y in years if y >= 2020)} papers from 2020 onwards",
        }

    def _analyze_quality_distribution(
        self, papers: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Analyze distribution of study quality."""
        study_types = [p.get("study_type", "Unknown") for p in papers]
        type_counts = Counter(study_types)

        distribution = {
            "high_quality": sum(
                count
                for study_type, count in type_counts.items()
                if study_type
                in ["Meta-Analysis", "Randomized Controlled Trial", "Systematic Review"]
            ),
            "medium_quality": sum(
                count
                for study_type, count in type_counts.items()
                if study_type in ["Cohort Study", "Case-Control Study"]
            ),
            "low_quality": sum(
                count
                for study_type, count in type_counts.items()
                if study_type in ["Case Report", "Case Series"]
            ),
        }

        return distribution

    def generate_recommendations(self, synthesis: Dict[str, Any]) -> List[str]:
        """Generate clinical or research recommendations based on synthesis."""
        recommendations = []

        evidence_strength = synthesis["overall_evidence_strength"]
        confidence = synthesis["confidence_level"]

        if evidence_strength >= 80:
            recommendations.append(
                "Evidence supports consideration for clinical implementation"
            )
        elif evidence_strength >= 60:
            recommendations.append(
                "Promising results warrant further investigation before widespread adoption"
            )
        else:
            recommendations.append(
                "Insufficient evidence for clinical recommendations at this time"
            )

        if synthesis["contradictions"]:
            recommendations.append(
                "Conflicting evidence suggests need for standardized protocols and larger trials"
            )

        if "Long-term outcomes" in " ".join(synthesis["research_gaps"]):
            recommendations.append(
                "Long-term follow-up studies are critically needed"
            )

        return recommendations[:4]
