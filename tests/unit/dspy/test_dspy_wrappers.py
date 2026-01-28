"""
Unit tests for DSPy integration wrappers and CLI.

Tests bindu/dspy/signature.py, program.py, optimizer.py, and cli/*.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY

from bindu.dspy.signature import AgentSignature
from bindu.dspy.program import AgentProgram
from bindu.dspy.optimizer import optimize


# ============================================================================
# Test AgentSignature
# ============================================================================
class TestAgentSignature:
    """Test DSPy signature wrapper."""
    
    def test_signature_initialization(self):
        """Test signature is a DSPy Signature class."""
        import dspy
        assert issubclass(AgentSignature, dspy.Signature)
    
    def test_signature_has_input_field(self):
        """Test signature defines input field."""
        # Check if input field is defined in the signature
        assert hasattr(AgentSignature, "__annotations__") or hasattr(AgentSignature, "input")
    
    def test_signature_has_output_field(self):
        """Test signature defines output field."""
        # Check if output field is defined in the signature
        assert hasattr(AgentSignature, "__annotations__") or hasattr(AgentSignature, "output")
    
    def test_signature_docstring(self):
        """Test signature has descriptive docstring."""
        assert AgentSignature.__doc__ is not None
        assert len(AgentSignature.__doc__) > 0


# ============================================================================
# Test AgentProgram
# ============================================================================
class TestAgentProgram:
    """Test DSPy program wrapper."""
    
    def test_program_initialization(self):
        """Test program is initialized with prompt text."""
        program = AgentProgram(current_prompt_text="Test prompt")
        
        assert program.instructions == "Test prompt"
        assert hasattr(program, "predictor")
    
    def test_program_forward_pass(self):
        """Test program forward pass."""
        import dspy
        
        program = AgentProgram(current_prompt_text="Test prompt")
        
        with patch.object(program, "predictor", MagicMock()) as mock_predictor:
            mock_predictor.return_value = MagicMock(output="Generated response")
            
            result = program.forward(input="Test input")
            
            # Verify predictor was called
            assert mock_predictor.called
    
    def test_program_is_dspy_module(self):
        """Test program is a DSPy Module."""
        import dspy
        program = AgentProgram(current_prompt_text="Test")
        
        assert isinstance(program, dspy.Module)


# ============================================================================
# Test optimize function
# ============================================================================
class TestOptimize:
    """Test DSPy optimizer wrapper."""
    
    def test_optimize_basic_success(self):
        """Test basic optimization workflow."""
        mock_program = MagicMock()
        mock_dataset = [MagicMock(), MagicMock()]
        mock_optimizer = MagicMock()
        mock_optimized_program = MagicMock()
        mock_optimizer.compile.return_value = mock_optimized_program
        
        result = optimize(
            program=mock_program,
            dataset=mock_dataset,
            optimizer=mock_optimizer
        )
        
        # Should call optimizer.compile
        mock_optimizer.compile.assert_called_once_with(
            mock_program,
            trainset=mock_dataset
        )
        
        assert result == mock_optimized_program
    
    def test_optimize_validates_optimizer_has_compile(self):
        """Test optimization raises if optimizer lacks compile method."""
        mock_program = MagicMock()
        mock_dataset = [MagicMock()]
        mock_optimizer = MagicMock(spec=[])  # No compile method
        del mock_optimizer.compile
        
        with pytest.raises(TypeError, match="does not implement compile"):
            optimize(
                program=mock_program,
                dataset=mock_dataset,
                optimizer=mock_optimizer
            )
    
    def test_optimize_with_simba(self):
        """Test optimization with SIMBA optimizer."""
        mock_program = MagicMock()
        mock_dataset = [MagicMock()] * 10
        mock_optimizer = MagicMock()
        mock_optimizer.compile.return_value = MagicMock()
        
        result = optimize(
            program=mock_program,
            dataset=mock_dataset,
            optimizer=mock_optimizer
        )
        
        assert result is not None
        mock_optimizer.compile.assert_called_once()


# ============================================================================
# Test feedback_metric
# ============================================================================
class TestFeedbackMetric:
    """Test custom DSPy metric function."""
    
    def test_feedback_metric_exact_match(self):
        """Test metric with exact output match."""
        from bindu.dspy.cli.train import feedback_metric
        
        example = MagicMock()
        example.output = "Expected output"
        
        prediction_dict = {"output": "Expected output"}
        
        score = feedback_metric(example, prediction_dict)
        
        # Exact match should score 1.0
        assert score == 1.0
    
    def test_feedback_metric_no_match(self):
        """Test metric with no match."""
        from bindu.dspy.cli.train import feedback_metric
        
        example = MagicMock()
        example.output = "Expected output"
        example.feedback = None  # Explicitly set to None to prevent MagicMock auto-creation
        
        prediction_dict = {"output": "Different output"}
        
        score = feedback_metric(example, prediction_dict)
        
        # No match should score 0.0
        assert score == 0.0
    
    def test_feedback_metric_with_explicit_feedback(self):
        """Test metric uses explicit feedback score if available."""
        from bindu.dspy.cli.train import feedback_metric
        
        example = MagicMock()
        example.output = "Some output"
        example.feedback = {"score": 0.85}
        
        prediction_dict = {"output": "Different output"}
        
        score = feedback_metric(example, prediction_dict)
        
        # Should use explicit feedback score
        assert score == 0.85
    
    def test_feedback_metric_empty_prediction(self):
        """Test metric with empty prediction."""
        from bindu.dspy.cli.train import feedback_metric
        
        example = MagicMock()
        example.output = "Expected"
        
        prediction_dict = {"output": ""}
        
        score = feedback_metric(example, prediction_dict)
        
        assert score == 0.0
    
    def test_feedback_metric_missing_output_key(self):
        """Test metric with missing output key."""
        from bindu.dspy.cli.train import feedback_metric
        
        example = MagicMock()
        example.output = "Expected"
        
        prediction_dict = {}
        
        score = feedback_metric(example, prediction_dict)
        
        assert score == 0.0


# ============================================================================
# Test parse_strategy CLI helper
# ============================================================================
class TestParseStrategy:
    """Test strategy parsing for CLI."""
    
    def test_parse_strategy_last_turn(self):
        """Test parsing last_turn strategy."""
        from bindu.dspy.cli.train import parse_strategy
        from bindu.dspy.strategies import LastTurnStrategy
        
        result = parse_strategy("last_turn")
        
        assert isinstance(result, LastTurnStrategy)
    
    def test_parse_strategy_full_history(self):
        """Test parsing full_history strategy."""
        from bindu.dspy.cli.train import parse_strategy
        from bindu.dspy.strategies import FullHistoryStrategy
        
        result = parse_strategy("full_history")
        
        assert isinstance(result, FullHistoryStrategy)
    
    def test_parse_strategy_last_n(self):
        """Test parsing last_n:N strategy."""
        from bindu.dspy.cli.train import parse_strategy
        from bindu.dspy.strategies import LastNTurnsStrategy
        
        result = parse_strategy("last_n:5")
        
        assert isinstance(result, LastNTurnsStrategy)
        assert result.n_turns == 5
    
    def test_parse_strategy_first_n(self):
        """Test parsing first_n:N strategy."""
        from bindu.dspy.cli.train import parse_strategy
        from bindu.dspy.strategies import FirstNTurnsStrategy
        
        result = parse_strategy("first_n:3")
        
        assert isinstance(result, FirstNTurnsStrategy)
        assert result.n_turns == 3
    
    def test_parse_strategy_unknown(self):
        """Test parsing unknown strategy raises ValueError."""
        from bindu.dspy.cli.train import parse_strategy
        
        with pytest.raises(ValueError, match="Unknown strategy"):
            parse_strategy("invalid_strategy")


# ============================================================================
# Test CLI entry point
# ============================================================================
class TestCLI:
    """Test CLI command entry points."""
    
    def test_cli_main_entry_point_exists(self):
        """Test main CLI entry point exists."""
        from bindu.dspy.cli.train import main
        
        # Should be callable
        assert callable(main)

