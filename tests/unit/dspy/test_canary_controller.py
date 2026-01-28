"""
Unit tests for bindu/dspy/canary/controller.py

Tests canary deployment A/B testing logic.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bindu.dspy.canary.controller import (
    compare_metrics,
    promote_step,
    rollback_step,
    run_canary_controller,
)


# ============================================================================
# Test compare_metrics
# ============================================================================
class TestCompareMetrics:
    """Test metric comparison logic."""
    
    def test_candidate_better(self):
        """Test candidate has better average_feedback_score."""
        active = {
            "num_interactions": 100,
            "average_feedback_score": 0.80
        }
        candidate = {
            "num_interactions": 50,
            "average_feedback_score": 0.85
        }
        
        result = compare_metrics(active, candidate)
        
        assert result == "candidate"
    
    def test_candidate_worse(self):
        """Test candidate has worse average_feedback_score."""
        active = {
            "num_interactions": 100,
            "average_feedback_score": 0.85
        }
        candidate = {
            "num_interactions": 50,
            "average_feedback_score": 0.80
        }
        
        result = compare_metrics(active, candidate)
        
        assert result == "active"
    
    def test_candidate_insufficient_interactions(self):
        """Test candidate with insufficient interactions returns None."""
        active = {
            "num_interactions": 100,
            "average_feedback_score": 0.85
        }
        candidate = {
            "num_interactions": 1,  # Below threshold of 2
            "average_feedback_score": 0.90
        }
        
        result = compare_metrics(active, candidate)
        
        assert result is None
    
    def test_candidate_equal_scores(self):
        """Test candidate with equal score returns None (tie)."""
        active = {
            "num_interactions": 100,
            "average_feedback_score": 0.85
        }
        candidate = {
            "num_interactions": 50,
            "average_feedback_score": 0.85
        }
        
        result = compare_metrics(active, candidate)
        
        assert result is None
    
    def test_missing_feedback_scores(self):
        """Test when feedback scores are None."""
        active = {
            "num_interactions": 100,
            "average_feedback_score": None
        }
        candidate = {
            "num_interactions": 50,
            "average_feedback_score": 0.85
        }
        
        result = compare_metrics(active, candidate)
        
        assert result is None
    
    def test_candidate_no_feedback(self):
        """Test when candidate has no feedback score."""
        active = {
            "num_interactions": 100,
            "average_feedback_score": 0.85
        }
        candidate = {
            "num_interactions": 50,
            "average_feedback_score": None
        }
        
        result = compare_metrics(active, candidate)
        
        assert result is None


# ============================================================================
# Test promote_step
# ============================================================================
class TestPromoteStep:
    """Test canary promotion step."""
    
    @pytest.mark.asyncio
    async def test_promote_step_success(self):
        """Test successful canary promotion."""
        mock_storage = AsyncMock()
        
        active = {"id": 1, "traffic": 0.7}
        candidate = {"id": 2, "traffic": 0.3}
        
        with patch("bindu.dspy.canary.controller.update_prompt_traffic") as mock_update:
            mock_update.return_value = None
            
            await promote_step(active, candidate, storage=mock_storage, did="agent-1")
            
            # Verify update_prompt_traffic called twice (candidate + active)
            assert mock_update.call_count == 2
    
    @pytest.mark.asyncio
    async def test_promote_step_increases_candidate_traffic(self):
        """Test candidate traffic increases by traffic_step."""
        mock_storage = AsyncMock()
        
        active = {"id": 1, "traffic": 0.6}
        candidate = {"id": 2, "traffic": 0.4}
        
        with patch("bindu.dspy.canary.controller.update_prompt_traffic") as mock_update:
            with patch("bindu.dspy.canary.controller.app_settings") as mock_settings:
                mock_settings.dspy.canary_traffic_step = 0.1
                
                await promote_step(active, candidate, storage=mock_storage, did="agent-1")
                
                # Check candidate gets increased traffic (0.4 + 0.1 = 0.5)
                calls = mock_update.call_args_list
                assert any(call[0][0] == 2 and abs(call[0][1] - 0.5) < 0.001 for call in calls)
    
    @pytest.mark.asyncio
    async def test_promote_step_storage_error(self):
        """Test promotion with storage error."""
        mock_storage = AsyncMock()
        
        active = {"id": 1, "traffic": 0.7}
        candidate = {"id": 2, "traffic": 0.3}
        
        with patch("bindu.dspy.canary.controller.update_prompt_traffic") as mock_update:
            mock_update.side_effect = Exception("DB error")
            
            with pytest.raises(Exception, match="DB error"):
                await promote_step(active, candidate, storage=mock_storage, did="agent-1")


# ============================================================================
# Test rollback_step
# ============================================================================
class TestRollbackStep:
    """Test canary rollback step."""
    
    @pytest.mark.asyncio
    async def test_rollback_step_success(self):
        """Test successful rollback."""
        mock_storage = AsyncMock()
        
        active = {"id": 1, "traffic": 0.6}
        candidate = {"id": 2, "traffic": 0.4}
        
        with patch("bindu.dspy.canary.controller.update_prompt_traffic") as mock_update:
            mock_update.return_value = None
            
            await rollback_step(active, candidate, storage=mock_storage, did="agent-1")
            
            # Verify update_prompt_traffic called twice
            assert mock_update.call_count == 2
    
    @pytest.mark.asyncio
    async def test_rollback_step_decreases_candidate_traffic(self):
        """Test candidate traffic decreases by traffic_step."""
        mock_storage = AsyncMock()
        
        active = {"id": 1, "traffic": 0.6}
        candidate = {"id": 2, "traffic": 0.4}
        
        with patch("bindu.dspy.canary.controller.update_prompt_traffic") as mock_update:
            with patch("bindu.dspy.canary.controller.app_settings") as mock_settings:
                mock_settings.dspy.canary_traffic_step = 0.1
                
                await rollback_step(active, candidate, storage=mock_storage, did="agent-1")
                
                # Check the actual calls - update_prompt_traffic(id, traffic, storage=, did=)
                calls = mock_update.call_args_list
                # First call should be for candidate with decreased traffic
                assert calls[0][0][0] == 2  # candidate id
                assert abs(calls[0][0][1] - 0.3) < 0.001  # 0.4 - 0.1 (with floating point tolerance)
                # Second call should be for active with increased traffic
                assert calls[1][0][0] == 1  # active id
                assert abs(calls[1][0][1] - 0.7) < 0.001  # 0.6 + 0.1
    
    @pytest.mark.asyncio
    async def test_rollback_step_storage_error(self):
        """Test rollback with storage error."""
        mock_storage = AsyncMock()
        
        active = {"id": 1, "traffic": 0.6}
        candidate = {"id": 2, "traffic": 0.4}
        
        with patch("bindu.dspy.canary.controller.update_prompt_traffic") as mock_update:
            mock_update.side_effect = Exception("DB error")
            
            with pytest.raises(Exception, match="DB error"):
                await rollback_step(active, candidate, storage=mock_storage, did="agent-1")


# ============================================================================
# Test run_canary_controller
# ============================================================================
class TestRunCanaryController:
    """Test main canary controller orchestration."""
    
    @pytest.mark.asyncio
    async def test_run_canary_controller_no_candidate(self):
        """Test controller when no candidate exists."""
        with patch("bindu.dspy.canary.controller.PostgresStorage") as MockStorage:
            mock_instance = AsyncMock()
            MockStorage.return_value = mock_instance
            
            # Mock no candidate prompt
            with patch("bindu.dspy.canary.controller.get_candidate_prompt", return_value=None):
                result = await run_canary_controller(did="agent-1")
                
                # Should return None (early exit)
                assert result is None
    
    @pytest.mark.asyncio
    async def test_run_canary_controller_candidate_wins(self):
        """Test controller when candidate is better."""
        with patch("bindu.dspy.canary.controller.PostgresStorage") as MockStorage:
            mock_instance = AsyncMock()
            MockStorage.return_value = mock_instance
            
            candidate = {
                "id": 2,
                "prompt_text": "New prompt",
                "status": "candidate",
                "traffic": 0.3,
                "num_interactions": 50,
                "average_feedback_score": 0.85
            }
            active = {
                "id": 1,
                "prompt_text": "Old prompt",
                "status": "active",
                "traffic": 0.7,
                "num_interactions": 100,
                "average_feedback_score": 0.80
            }
            
            with patch("bindu.dspy.canary.controller.get_candidate_prompt", return_value=candidate):
                with patch("bindu.dspy.canary.controller.get_active_prompt", return_value=active):
                    with patch("bindu.dspy.canary.controller.promote_step") as mock_promote:
                        result = await run_canary_controller(did="agent-1")
                        
                        # Should call promote_step since candidate is better
                        mock_promote.assert_called_once()
                        assert result is None
    
    @pytest.mark.asyncio
    async def test_run_canary_controller_active_wins(self):
        """Test controller when active is better."""
        with patch("bindu.dspy.canary.controller.PostgresStorage") as MockStorage:
            mock_instance = AsyncMock()
            MockStorage.return_value = mock_instance
            
            candidate = {
                "id": 2,
                "prompt_text": "New prompt",
                "status": "candidate",
                "traffic": 0.4,
                "num_interactions": 50,
                "average_feedback_score": 0.75
            }
            active = {
                "id": 1,
                "prompt_text": "Old prompt",
                "status": "active",
                "traffic": 0.6,
                "num_interactions": 100,
                "average_feedback_score": 0.85
            }
            
            with patch("bindu.dspy.canary.controller.get_candidate_prompt", return_value=candidate):
                with patch("bindu.dspy.canary.controller.get_active_prompt", return_value=active):
                    with patch("bindu.dspy.canary.controller.rollback_step") as mock_rollback:
                        result = await run_canary_controller(did="agent-1")
                        
                        # Should call rollback_step since active is better
                        mock_rollback.assert_called_once()
                        assert result is None
    
    @pytest.mark.asyncio
    async def test_run_canary_controller_tie(self):
        """Test controller when neither prompt is clearly better."""
        with patch("bindu.dspy.canary.controller.PostgresStorage") as MockStorage:
            mock_instance = AsyncMock()
            MockStorage.return_value = mock_instance
            
            candidate = {
                "id": 2,
                "prompt_text": "New prompt",
                "status": "candidate",
                "traffic": 0.5,
                "num_interactions": 50,
                "average_feedback_score": 0.80
            }
            active = {
                "id": 1,
                "prompt_text": "Old prompt",
                "status": "active",
                "traffic": 0.5,
                "num_interactions": 100,
                "average_feedback_score": 0.80
            }
            
            with patch("bindu.dspy.canary.controller.get_candidate_prompt", return_value=candidate):
                with patch("bindu.dspy.canary.controller.get_active_prompt", return_value=active):
                    with patch("bindu.dspy.canary.controller.promote_step") as mock_promote:
                        with patch("bindu.dspy.canary.controller.rollback_step") as mock_rollback:
                            result = await run_canary_controller(did="agent-1")
                            
                            # Should not call promote or rollback for a tie
                            mock_promote.assert_not_called()
                            mock_rollback.assert_not_called()
                            assert result is None
    
    @pytest.mark.asyncio
    async def test_run_canary_controller_no_active(self):
        """Test controller when no active prompt exists."""
        with patch("bindu.dspy.canary.controller.PostgresStorage") as MockStorage:
            mock_instance = AsyncMock()
            MockStorage.return_value = mock_instance
            
            candidate = {
                "id": 2,
                "prompt_text": "New prompt",
                "status": "candidate",
                "traffic": 0.5,
                "num_interactions": 50,
                "average_feedback_score": 0.80
            }
            
            with patch("bindu.dspy.canary.controller.get_candidate_prompt", return_value=candidate):
                with patch("bindu.dspy.canary.controller.get_active_prompt", return_value=None):
                    result = await run_canary_controller(did="agent-1")
                    
                    # Should return None and log warning
                    assert result is None

