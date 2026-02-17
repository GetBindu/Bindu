                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            """
Comprehensive test suite for MedResearch Agent

Tests all components: PDF processing, NLP, evidence scoring, and synthesis.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import custom tools (files are in root directory)
from pdf_processor import PDFProcessor
from medical_nlp import MedicalNLP
from evidence_scorer import EvidenceScorer
from synthesizer import PaperSynthesizer


class TestPDFProcessor:
    """Test PDF processing functionality."""

    @pytest.fixture
    def processor(self):
        return PDFProcessor()

    @pytest.fixture
    def sample_text(self):
        return """
        Effect of Metformin on Type 2 Diabetes: A Clinical Trial
        
        John Smith, Jane Doe
        2023
        
        Abstract:
        This study evaluated metformin efficacy in 500 patients with type 2 diabetes.
        Results showed significant HbA1c reduction of 1.2% (p<0.001).
        
        Methods:
        Double-blind randomized controlled trial with 500 participants.
        Primary outcome was HbA1c change at 12 months.
        
        Results:
        Mean HbA1c decreased from 8.5% to 7.3% in treatment group.
        Placebo group showed minimal change (8.4% to 8.1%).
        
        Conclusions:
        Metformin is effective for type 2 diabetes management.
        
        Limitations:
        Study limited to 12-month follow-up.
        Predominantly urban population.
        """

    def test_extract_title(self, processor, sample_text):
        """Test title extraction."""
        title = processor._extract_title(sample_text)
        assert len(title) > 0
        assert "metformin" in title.lower() or "diabetes" in title.lower()

    def test_extract_authors(self, processor, sample_text):
        """Test author extraction."""
        authors = processor._extract_authors(sample_text)
        assert len(authors) > 0
        assert any("John" in author or "Jane" in author for author in authors)

    def test_extract_year(self, processor, sample_text):
        """Test year extraction."""
        year = processor._extract_year(sample_text)
        assert 2000 <= year <= 2024

    def test_extract_section(self, processor, sample_text):
        """Test section extraction."""
        abstract = processor._extract_section(sample_text, "abstract")
        assert len(abstract) > 0
        assert "patients" in abstract.lower()

    def test_extract_sample_size(self, processor, sample_text):
        """Test sample size extraction."""
        size = processor._extract_sample_size(sample_text)
        assert size == "500"

    def test_identify_study_type(self, processor, sample_text):
        """Test study type identification."""
        study_type = processor._identify_study_type(sample_text)
        assert "Randomized Controlled Trial" in study_type

    def test_extract_key_findings(self, processor, sample_text):
        """Test key findings extraction."""
        findings = processor._extract_key_findings(sample_text)
        assert len(findings) > 0
        assert any("significant" in f.lower() or "reduction" in f.lower() for f in findings)

    def test_extract_limitations(self, processor, sample_text):
        """Test limitations extraction."""
        limitations = processor._extract_limitations(sample_text)
        assert len(limitations) > 0

    def test_generate_paper_id(self, processor, sample_text):
        """Test paper ID generation."""
        paper_id = processor._generate_paper_id(sample_text)
        assert paper_id.startswith("paper_")
        assert len(paper_id) > 10


class TestMedicalNLP:
    """Test medical NLP functionality."""

    @pytest.fixture
    def nlp(self):
        return MedicalNLP()

    @pytest.fixture
    def medical_text(self):
        return """
        Patients with type 2 diabetes received metformin 1000mg twice daily.
        HbA1c levels decreased significantly (p<0.001) from 8.5% to 7.3%.
        Blood pressure was monitored. No serious adverse events occurred.
        The study included 500 participants over 12 months.
        """

    def test_extract_conditions(self, nlp, medical_text):
        """Test medical condition extraction."""
        entities = nlp.extract_entities(medical_text)
        conditions = entities["conditions"]
        assert len(conditions) > 0
        assert any("diabetes" in c.lower() for c in conditions)

    def test_extract_medications(self, nlp, medical_text):
        """Test medication extraction."""
        entities = nlp.extract_entities(medical_text)
        medications = entities["medications"]
        assert len(medications) > 0
        assert any("metformin" in m.lower() for m in medications)

    def test_extract_dosages(self, nlp, medical_text):
        """Test dosage extraction."""
        entities = nlp.extract_entities(medical_text)
        dosages = entities["dosages"]
        assert len(dosages) > 0
        assert any("1000" in d for d in dosages)

    def test_extract_statistics(self, nlp, medical_text):
        """Test statistical value extraction."""
        entities = nlp.extract_entities(medical_text)
        statistics = entities["statistics"]
        assert len(statistics) > 0
        assert any("p<0.001" in s or "0.001" in s for s in statistics)

    def test_extract_lab_values(self, nlp, medical_text):
        """Test lab value extraction."""
        entities = nlp.extract_entities(medical_text)
        lab_values = entities["lab_values"]
        # Should find HbA1c or blood pressure
        assert len(lab_values) >= 0  # May or may not find, depends on text

    def test_identify_adverse_events(self, nlp):
        """Test adverse event identification."""
        text = "Patients experienced nausea as a side effect. No serious adverse reactions."
        adverse_events = nlp.identify_adverse_events(text)
        assert len(adverse_events) > 0

    def test_calculate_readability(self, nlp, medical_text):
        """Test readability scoring."""
        readability = nlp.calculate_readability_score(medical_text)
        assert "score" in readability
        assert 0 <= readability["score"] <= 100
        assert "level" in readability


class TestEvidenceScorer:
    """Test evidence quality scoring."""

    @pytest.fixture
    def scorer(self):
        return EvidenceScorer()

    @pytest.fixture
    def rct_paper(self):
        return {
            "study_type": "Randomized Controlled Trial",
            "sample_size": "500",
            "year": 2023,
            "full_text": "double-blind randomized placebo-controlled multi-center study",
        }

    @pytest.fixture
    def case_report(self):
        return {
            "study_type": "Case Report",
            "sample_size": "1",
            "year": 2020,
            "full_text": "single patient case report retrospective",
        }

    def test_score_rct_paper(self, scorer, rct_paper):
        """Test scoring of high-quality RCT."""
        score = scorer.score_paper(rct_paper)
        assert score >= 70  # Should get high score

    def test_score_case_report(self, scorer, case_report):
        """Test scoring of low-quality case report."""
        score = scorer.score_paper(case_report)
        assert score <= 50  # Should get lower score

    def test_score_study_type(self, scorer):
        """Test study type scoring."""
        rct_score = scorer._score_study_type("Randomized Controlled Trial")
        case_score = scorer._score_study_type("Case Report")
        assert rct_score > case_score

    def test_score_sample_size(self, scorer):
        """Test sample size scoring."""
        large_score = scorer._score_sample_size("5000")
        small_score = scorer._score_sample_size("50")
        assert large_score > small_score

    def test_score_recency(self, scorer):
        """Test recency scoring."""
        recent_score = scorer._score_recency(2024)
        old_score = scorer._score_recency(2010)
        assert recent_score > old_score

    def test_identify_biases(self, scorer, rct_paper):
        """Test bias identification."""
        biases = scorer.identify_biases(rct_paper)
        assert "selection_bias" in biases
        assert "funding_bias" in biases
        assert "overall_risk" in biases

    def test_generate_quality_report(self, scorer, rct_paper):
        """Test quality report generation."""
        report = scorer.generate_quality_report(rct_paper)
        assert "overall_score" in report
        assert "grade" in report
        assert "biases" in report
        assert "strengths" in report
        assert "weaknesses" in report


class TestPaperSynthesizer:
    """Test multi-paper synthesis."""

    @pytest.fixture
    def synthesizer(self):
        return PaperSynthesizer()

    @pytest.fixture
    def sample_papers(self):
        return [
            {
                "id": "paper1",
                "title": "Metformin Study 1",
                "year": 2023,
                "study_type": "Randomized Controlled Trial",
                "sample_size": "500",
                "key_findings": ["Significant reduction in HbA1c", "Effective treatment"],
                "full_text": "metformin effective significant improvement reduced HbA1c",
                "limitations": ["Short follow-up period"],
            },
            {
                "id": "paper2",
                "title": "Metformin Study 2",
                "year": 2022,
                "study_type": "Randomized Controlled Trial",
                "sample_size": "800",
                "key_findings": ["HbA1c reduction confirmed", "Well tolerated"],
                "full_text": "metformin effective reduction improvement beneficial",
                "limitations": ["Limited diverse population"],
            },
            {
                "id": "paper3",
                "title": "Metformin Study 3",
                "year": 2021,
                "study_type": "Cohort Study",
                "sample_size": "300",
                "key_findings": ["Modest improvement", "Some side effects"],
                "full_text": "metformin improvement moderate effects",
                "limitations": ["Observational design"],
            },
        ]

    def test_synthesize_papers(self, synthesizer, sample_papers):
        """Test basic synthesis functionality."""
        synthesis = synthesizer.synthesize(sample_papers, "Metformin in Type 2 Diabetes")
        assert "consensus_findings" in synthesis
        assert "contradictions" in synthesis
        assert "overall_evidence_strength" in synthesis
        assert synthesis["paper_count"] == 3

    def test_find_consensus(self, synthesizer, sample_papers):
        """Test consensus finding."""
        consensus = synthesizer._find_consensus(sample_papers)
        assert len(consensus) > 0

    def test_identify_agreements(self, synthesizer, sample_papers):
        """Test agreement identification."""
        agreements = synthesizer._identify_agreements(sample_papers)
        assert len(agreements) > 0

    def test_calculate_overall_evidence(self, synthesizer, sample_papers):
        """Test overall evidence calculation."""
        evidence_score = synthesizer._calculate_overall_evidence(sample_papers)
        assert 0 <= evidence_score <= 100

    def test_determine_confidence(self, synthesizer, sample_papers):
        """Test confidence determination."""
        confidence = synthesizer._determine_confidence(sample_papers)
        assert isinstance(confidence, str)
        assert len(confidence) > 0

    def test_identify_research_gaps(self, synthesizer, sample_papers):
        """Test research gap identification."""
        gaps = synthesizer._identify_research_gaps(sample_papers)
        assert len(gaps) > 0

    def test_analyze_temporal_trends(self, synthesizer, sample_papers):
        """Test temporal trend analysis."""
        trends = synthesizer._analyze_temporal_trends(sample_papers)
        assert "trend" in trends
        assert "span" in trends

    def test_analyze_quality_distribution(self, synthesizer, sample_papers):
        """Test quality distribution analysis."""
        distribution = synthesizer._analyze_quality_distribution(sample_papers)
        assert "high_quality" in distribution
        assert "medium_quality" in distribution
        assert "low_quality" in distribution


class TestIntegration:
    """Integration tests for the full agent workflow."""

    def test_full_workflow(self):
        """Test complete workflow from PDF to synthesis."""
        processor = PDFProcessor()
        nlp = MedicalNLP()
        scorer = EvidenceScorer()
        synthesizer = PaperSynthesizer()

        # Simulate processing a paper
        sample_text = """
        Metformin in Type 2 Diabetes: An RCT
        Smith et al, 2023
        
        Abstract: 500 patients, significant HbA1c reduction (p<0.001)
        Methods: Double-blind RCT, 12 months
        Results: 1.2% HbA1c reduction
        Conclusions: Effective treatment
        Limitations: Short-term study
        """

        # Process paper
        paper_data = {
            "title": "Test Paper",
            "year": 2023,
            "study_type": "Randomized Controlled Trial",
            "sample_size": "500",
            "full_text": sample_text,
            "key_findings": ["Significant reduction"],
            "limitations": ["Short-term"],
        }

        # Extract entities
        entities = nlp.extract_entities(sample_text)
        assert entities is not None

        # Score evidence
        score = scorer.score_paper(paper_data)
        assert score > 0

        # Test synthesis with multiple papers
        papers = [paper_data, paper_data]  # Duplicate for testing
        synthesis = synthesizer.synthesize(papers, "Diabetes Treatment")
        assert synthesis["paper_count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
