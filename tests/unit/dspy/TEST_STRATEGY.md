# DSPy Module - Unit Test Strategy

## Overview

This document defines the comprehensive testing strategy for the `bindu/dspy` module, which implements offline prompt optimization using DSPy's teleprompter system. The strategy focuses on unit testing all components with proper mocking of external dependencies.

**Created:** January 28, 2026  
**Target Directory:** `tests/unit/dspy/`  
**Max Test Files:** 10 files  
**Testing Framework:** pytest with asyncio support

---

## Testing Principles

### 1. Test Philosophy
- **Unit tests only**: Test individual functions and classes in isolation
- **Mock external dependencies**: Mock database connections, DSPy LM calls, storage operations
- **Async-first**: All async functions must use `@pytest.mark.asyncio` decorator
- **Class-based organization**: Group related tests using Test* classes
- **Fast execution**: Unit tests should run in milliseconds, not seconds
- **Comprehensive coverage**: Test happy paths, edge cases, error conditions, and boundary values

### 2. Existing Patterns to Follow
Based on the codebase analysis, we follow these established patterns:

```python
# Pattern 1: Test class organization
class TestFunctionName:
    """Test function_name behavior."""
    
    def test_specific_behavior(self):
        """Test that specific behavior works correctly."""
        # Test implementation
```

```python
# Pattern 2: Async tests
@pytest.mark.asyncio
async def test_async_function():
    """Test async function behavior."""
    result = await some_async_function()
    assert result is not None
```

```python
# Pattern 3: Mock external dependencies
from unittest.mock import MagicMock, patch, AsyncMock

def test_with_mocks():
    """Test function with mocked dependencies."""
    mock_storage = AsyncMock()
    mock_storage.fetch_tasks.return_value = [...]
    result = await function_under_test(storage=mock_storage)
```

```python
# Pattern 4: Parametrized tests for multiple scenarios
@pytest.mark.parametrize("input_value,expected", [
    ("value1", "expected1"),
    ("value2", "expected2"),
])
def test_multiple_scenarios(input_value, expected):
    """Test function with different inputs."""
    assert function(input_value) == expected
```

### 3. Mocking Strategy
- **Database/Storage**: Mock `PostgresStorage` and its methods
- **DSPy LM calls**: Mock `dspy.LM` and `dspy.configure`
- **External APIs**: Mock any HTTP/API calls
- **Settings**: Use fixtures or patches to override `app_settings`
- **File I/O**: Mock file operations where necessary

### 4. Test Data Creation
- Use helper functions from `tests/utils.py` when applicable
- Create minimal, focused test data for each test
- Use factories or builders for complex objects
- Leverage existing patterns like `create_test_message()` and `create_test_task()`

---

## Module Structure Analysis

### Core Components
1. **Models** (`models.py`): Data classes (`Interaction`, `PromptCandidate`)
2. **Dataset Pipeline** (`dataset.py`): Data fetching, normalization, validation, deduplication
3. **Extraction** (`extractor.py`): `InteractionExtractor` and message cleaning
4. **Strategies** (`strategies/`): 8+ extraction strategies with base class
5. **Similarity** (`strategies/similarity.py`): Text similarity algorithms
6. **Training** (`train.py`): Main training orchestration
7. **Program** (`program.py`): DSPy program wrapper
8. **Signature** (`signature.py`): DSPy signature definition
9. **Optimizer** (`optimizer.py`): DSPy optimizer wrapper
10. **Guard** (`guard.py`): Training safety checks
11. **Prompts** (`prompts.py`): Prompt management CRUD operations
12. **Prompt Selector** (`prompt_selector.py`): Canary deployment selection
13. **Canary Controller** (`canary/controller.py`): A/B testing traffic management
14. **CLI** (`cli/`): Command-line interfaces for train and canary

---

## Test File Organization (Max 10 Files)

We'll chunk related functionality into logical test files:

### File 1: `test_models.py`
**Purpose:** Test data models and data classes  
**Components:** `Interaction`, `PromptCandidate`, `RawTaskData`

### File 2: `test_dataset_pipeline.py`
**Purpose:** Test dataset preparation pipeline and helper functions  
**Components:** 
- `normalize_feedback()`
- `validate_and_clean_interactions()`
- `deduplicate_interactions()`
- `prepare_golden_dataset()`
- `validate_dataset_size()`
- `convert_to_dspy_examples()`
- `build_golden_dataset()`
- `fetch_raw_task_data()`
- `extract_interactions()`

### File 3: `test_extractor.py` 
**Purpose:** Test interaction extractor and message cleaning (ALREADY EXISTS - update if needed)  
**Components:**
- `clean_messages()`
- `InteractionExtractor` class
- Strategy integration

### File 4: `test_strategies_basic.py`
**Purpose:** Test simple extraction strategies  
**Components:**
- `LastTurnStrategy`
- `FullHistoryStrategy`
- `FirstNTurnsStrategy`
- `LastNTurnsStrategy`
- Strategy registry (`STRATEGIES`, `get_strategy()`)
- `parse_turns()` utility

### File 5: `test_strategies_advanced.py`
**Purpose:** Test advanced extraction strategies  
**Components:**
- `ContextWindowStrategy`
- `SlidingWindowStrategy`
- `SummaryContextStrategy`
- `KeyTurnsStrategy`

### File 6: `test_similarity.py`
**Purpose:** Test text similarity algorithms  
**Components:**
- `jaccard_similarity()`
- `overlap_similarity()`
- `weighted_similarity()`
- `compute_similarity()`
- `tokenize()`

### File 7: `test_training.py`
**Purpose:** Test training orchestration and core workflow  
**Components:**
- `train()` function
- `train_async()` function
- Integration with optimizer, dataset, guard
- A/B test initialization

### File 8: `test_prompts_and_guard.py`
**Purpose:** Test prompt management and training guards  
**Components:**
- `get_active_prompt()`
- `get_candidate_prompt()`
- `insert_prompt()`
- `update_prompt_traffic()`
- `update_prompt_status()`
- `zero_out_all_except()`
- `ensure_system_stable()`
- `select_prompt_with_canary()`

### File 9: `test_canary_controller.py`
**Purpose:** Test canary deployment controller  
**Components:**
- `compare_metrics()`
- `promote_step()`
- `rollback_step()`
- `run_canary_controller()`
- Traffic adjustment logic
- Stabilization detection

### File 10: `test_dspy_wrappers.py`
**Purpose:** Test DSPy wrapper components and CLI  
**Components:**
- `AgentSignature`
- `AgentProgram`
- `optimize()` function
- CLI argument parsing (`cli/train.py`, `cli/canary.py`)
- `feedback_metric()` function
- `parse_strategy()` function

---

## Detailed Test Case Specifications

### File 1: `test_models.py`

#### Test Class: `TestInteraction`
- `test_interaction_creation_with_all_fields()` - Create Interaction with all fields
- `test_interaction_creation_minimal()` - Create Interaction with only required fields
- `test_interaction_is_frozen()` - Verify dataclass is immutable
- `test_interaction_without_feedback()` - Create Interaction with feedback_score=None
- `test_interaction_equality()` - Test two Interactions with same data are equal

#### Test Class: `TestPromptCandidate`
- `test_prompt_candidate_creation()` - Create PromptCandidate successfully
- `test_prompt_candidate_with_metadata()` - Create with various metadata
- `test_prompt_candidate_is_frozen()` - Verify immutability

#### Test Class: `TestRawTaskData`
- `test_raw_task_data_creation()` - Create RawTaskData with all fields
- `test_raw_task_data_without_feedback()` - Create without feedback_data
- `test_raw_task_data_with_empty_history()` - Handle empty history list

---

### File 2: `test_dataset_pipeline.py`

#### Test Class: `TestNormalizeFeedback`
- `test_normalize_rating_feedback()` - Rating 1-5 normalized to 0.0-1.0
- `test_normalize_rating_edge_cases()` - Rating=1 (0.2), rating=5 (1.0)
- `test_normalize_thumbs_up_true()` - thumbs_up=True returns (1.0, "thumbs_up")
- `test_normalize_thumbs_up_false()` - thumbs_up=False returns (0.0, "thumbs_up")
- `test_normalize_thumbs_up_string()` - Handle "true"/"false" strings
- `test_normalize_invalid_rating()` - Out of range returns (None, None)
- `test_normalize_missing_feedback()` - None/empty dict returns (None, None)
- `test_normalize_invalid_type()` - Invalid data types handled gracefully

#### Test Class: `TestValidateAndCleanInteractions`
- `test_validate_removes_short_input()` - Input below min_input_length filtered
- `test_validate_removes_short_output()` - Output below min_output_length filtered
- `test_validate_removes_identical_input_output()` - Identical input/output filtered
- `test_validate_cleans_whitespace()` - Multiple spaces normalized to single space
- `test_validate_keeps_valid_interactions()` - Valid interactions pass through
- `test_validate_with_empty_list()` - Empty input returns empty list

#### Test Class: `TestDeduplicateInteractions`
- `test_deduplicate_removes_exact_duplicates()` - Duplicate (input, output) removed
- `test_deduplicate_preserves_unique()` - Unique interactions preserved
- `test_deduplicate_keeps_first_occurrence()` - First occurrence retained
- `test_deduplicate_with_empty_list()` - Empty list handled
- `test_deduplicate_different_feedback_same_content()` - Deduplicates even with different feedback

#### Test Class: `TestPrepareGoldenDataset`
- `test_prepare_converts_to_dict_format()` - Converts Interaction to dict
- `test_prepare_includes_feedback()` - Feedback included in output
- `test_prepare_handles_none_feedback()` - None feedback handled correctly
- `test_prepare_with_empty_list()` - Empty input returns empty dataset

#### Test Class: `TestValidateDatasetSize`
- `test_validate_size_too_small_raises_error()` - Below min_examples raises ValueError
- `test_validate_size_acceptable()` - Within range passes
- `test_validate_size_too_large_logs_warning()` - Above max_examples logs warning but passes
- `test_validate_size_at_boundaries()` - Exactly min/max values handled

#### Test Class: `TestConvertToDSPyExamples`
- `test_convert_creates_dspy_examples()` - Converts dicts to dspy.Example
- `test_convert_sets_input_fields()` - with_inputs("input") called correctly
- `test_convert_preserves_feedback()` - Feedback attribute preserved
- `test_convert_with_empty_dataset()` - Empty input returns empty list

#### Test Class: `TestFetchRawTaskData`
- `test_fetch_connects_to_storage()` - Storage.connect() called (mock)
- `test_fetch_calls_fetch_tasks_with_feedback()` - Correct method called with limit
- `test_fetch_disconnects_on_success()` - Storage.disconnect() called
- `test_fetch_disconnects_on_error()` - Disconnect called even on error
- `test_fetch_uses_did_for_schema_isolation()` - DID passed to storage
- `test_fetch_converts_rows_to_raw_task_data()` - Rows converted to RawTaskData objects
- `test_fetch_handles_connection_error()` - Raises ConnectionError on DB failure
- `test_fetch_with_custom_limit()` - Custom limit parameter respected
- `test_fetch_with_default_limit()` - Uses settings limit when None

#### Test Class: `TestExtractInteractions`
- `test_extract_uses_strategy()` - Strategy.extract_all() called for each task
- `test_extract_normalizes_feedback()` - normalize_feedback() called
- `test_extract_collects_all_interactions()` - Multiple interactions from sliding window collected
- `test_extract_with_empty_tasks()` - Empty task list returns empty interactions
- `test_extract_skips_failed_extractions()` - Failed extractions (None) filtered out

#### Test Class: `TestBuildGoldenDataset`
- `test_build_full_pipeline_success()` - Complete pipeline runs successfully (mock all steps)
- `test_build_raises_on_no_tasks()` - ValueError if fetch returns empty
- `test_build_raises_on_no_interactions()` - ValueError if extraction fails
- `test_build_raises_on_no_valid_interactions()` - ValueError after validation
- `test_build_raises_on_dataset_too_small()` - ValueError from validate_dataset_size
- `test_build_uses_custom_strategy()` - Custom strategy passed through
- `test_build_uses_did_isolation()` - DID parameter propagated
- `test_build_with_require_feedback_false()` - Feedback not required

---

### File 3: `test_extractor.py` (Already exists - verify coverage)

Review existing tests and add missing test cases:

#### Test Class: `TestCleanMessages`
- `test_clean_removes_empty_content()` - Messages with empty content removed
- `test_clean_handles_direct_content_field()` - Direct "content" field handled
- `test_clean_handles_parts_array()` - Parts array with text kind handled
- `test_clean_handles_mixed_format()` - Both formats in same history
- `test_clean_strips_whitespace()` - Leading/trailing whitespace removed
- `test_clean_skips_non_text_parts()` - Non-text parts (images, etc.) skipped
- `test_clean_preserves_role()` - Role field preserved in output
- `test_clean_with_empty_history()` - Empty list returns empty list
- `test_clean_with_invalid_messages()` - Non-dict items filtered out

#### Test Class: `TestInteractionExtractor`
- `test_extractor_initialization_default_strategy()` - Defaults to LastTurnStrategy
- `test_extractor_initialization_custom_strategy()` - Custom strategy accepted
- `test_extract_calls_validate_and_clean()` - Message validation called
- `test_extract_delegates_to_strategy()` - Strategy.extract() called
- `test_extract_returns_none_on_empty_history()` - Empty history returns None
- `test_extract_returns_none_on_invalid_history()` - Invalid history returns None
- `test_extract_all_returns_list()` - extract_all returns list of Interactions
- `test_extract_all_with_sliding_window()` - Multiple interactions from sliding strategy
- `test_extract_all_with_single_strategy()` - Single interaction wrapped in list

---

### File 4: `test_strategies_basic.py`

#### Test Class: `TestStrategyRegistry`
- `test_all_strategies_registered()` - All 8 strategies in STRATEGIES dict
- `test_get_strategy_last_turn()` - Factory creates LastTurnStrategy
- `test_get_strategy_full_history()` - Factory creates FullHistoryStrategy
- `test_get_strategy_with_params()` - Parameters passed to strategy constructor
- `test_get_strategy_unknown_raises_error()` - Unknown name raises ValueError
- `test_get_strategy_lists_available()` - Error message lists available strategies

#### Test Class: `TestParseTurns`
- `test_parse_turns_single_exchange()` - One user-assistant pair parsed
- `test_parse_turns_multiple_exchanges()` - Multiple pairs parsed in order
- `test_parse_turns_skips_incomplete()` - User without assistant skipped
- `test_parse_turns_handles_agent_role()` - "agent" role treated like "assistant"
- `test_parse_turns_consecutive_users()` - Only last user before assistant used
- `test_parse_turns_empty_messages()` - Empty list returns empty list
- `test_parse_turns_no_complete_pairs()` - Only user messages returns empty

#### Test Class: `TestLastTurnStrategy`
- `test_name_property()` - Strategy name is "last_turn"
- `test_extract_last_turn_success()` - Last user-assistant pair extracted
- `test_extract_with_multiple_turns()` - Only last turn extracted
- `test_extract_no_assistant_message()` - Returns None if no assistant
- `test_extract_no_user_message()` - Returns None if no user message
- `test_extract_includes_feedback()` - Feedback score and type included
- `test_extract_handles_agent_role()` - Works with "agent" instead of "assistant"

#### Test Class: `TestFullHistoryStrategy`
- `test_name_property()` - Strategy name is "full_history"
- `test_extract_first_user_all_assistants()` - First user + all assistants concatenated
- `test_extract_formats_multiple_responses()` - Multiple responses numbered
- `test_extract_single_turn()` - Single turn not numbered
- `test_extract_respects_max_length()` - Truncates if exceeds max_full_history_length
- `test_extract_no_assistant_messages()` - Returns None if no assistants
- `test_extract_no_user_message()` - Returns None if no user

#### Test Class: `TestFirstNTurnsStrategy`
- `test_name_property()` - Strategy name is "first_n_turns"
- `test_extract_first_n_turns()` - First N turns extracted
- `test_extract_fewer_turns_available()` - Uses all available if less than N
- `test_extract_formats_user_messages()` - Multiple users numbered/separated
- `test_extract_uses_last_assistant()` - Last assistant in window is output
- `test_extract_default_n_turns()` - Uses app_settings.default_n_turns if None
- `test_extract_minimum_one_turn()` - n_turns < 1 treated as 1
- `test_extract_no_complete_turns()` - Returns None if no complete turns

#### Test Class: `TestLastNTurnsStrategy`
- `test_name_property()` - Strategy name is "last_n_turns"
- `test_extract_last_n_turns()` - Last N turns extracted
- `test_extract_fewer_turns_available()` - Uses all available if less than N
- `test_extract_formats_user_messages()` - Multiple users formatted correctly
- `test_extract_single_turn()` - Single turn not numbered
- `test_extract_default_n_turns()` - Uses app_settings default
- `test_extract_minimum_one_turn()` - Enforces minimum of 1

---

### File 5: `test_strategies_advanced.py`

#### Test Class: `TestContextWindowStrategy`
- `test_name_property()` - Strategy name is "context_window"
- `test_extract_with_system_prompt()` - System prompt prepended to user input
- `test_extract_without_system_prompt()` - Works without system prompt
- `test_extract_concatenates_user_messages()` - Multiple user messages concatenated
- `test_extract_small_window_simple_format()` - ≤3 turns use simple separator
- `test_extract_large_window_numbered_format()` - >3 turns numbered
- `test_extract_single_turn()` - Single turn not formatted
- `test_extract_uses_last_agent_response()` - Last assistant is output
- `test_extract_default_n_turns()` - Uses settings default
- `test_extract_minimum_one_turn()` - Enforces minimum

#### Test Class: `TestSlidingWindowStrategy`
- `test_name_property()` - Strategy name is "sliding_window"
- `test_extract_returns_last_window()` - Single extract returns last window
- `test_extract_all_overlapping_windows()` - stride=1 creates overlapping
- `test_extract_all_non_overlapping_windows()` - stride=window_size non-overlapping
- `test_extract_all_with_start_offset()` - start_offset skips first N turns
- `test_extract_all_not_enough_turns()` - Returns empty if fewer than window_size
- `test_extract_all_creates_multiple_interactions()` - Multiple Interactions created
- `test_extract_window_concatenates_users()` - Users in window concatenated
- `test_extract_default_params()` - Uses settings defaults
- `test_extract_minimum_values()` - Enforces minimums for window_size, stride

#### Test Class: `TestSummaryContextStrategy`
- `test_name_property()` - Strategy name is "summary_context"
- `test_extract_with_short_history()` - Short history uses full context
- `test_extract_with_long_history()` - Long history summarized
- `test_extract_summary_uses_first_turn()` - Summary includes first turn info
- `test_extract_summary_preserves_last_turns()` - Last N turns preserved
- `test_extract_formats_summary_section()` - Summary section clearly marked
- `test_extract_default_params()` - Uses settings defaults
- `test_extract_threshold_boundary()` - Exactly at threshold handled

#### Test Class: `TestKeyTurnsStrategy`
- `test_name_property()` - Strategy name is "key_turns"
- `test_extract_selects_relevant_turns()` - Most similar turns selected
- `test_extract_uses_similarity_method()` - Specified similarity method used
- `test_extract_default_similarity_method()` - Defaults to weighted
- `test_extract_all_available_turns()` - Uses all if fewer than n_turns
- `test_extract_includes_last_turn()` - Last turn always included
- `test_extract_sorts_by_similarity()` - Turns sorted by similarity score
- `test_extract_formats_selected_turns()` - Selected turns formatted
- `test_extract_default_n_turns()` - Uses settings default

---

### File 6: `test_similarity.py`

#### Test Class: `TestTokenize`
- `test_tokenize_basic()` - Simple string tokenized
- `test_tokenize_lowercases()` - Uppercase converted to lowercase
- `test_tokenize_splits_on_whitespace()` - Splits on spaces, tabs, newlines
- `test_tokenize_empty_string()` - Empty string returns empty list
- `test_tokenize_preserves_punctuation()` - Punctuation attached to words

#### Test Class: `TestJaccardSimilarity`
- `test_jaccard_identical_texts()` - Identical texts return 1.0
- `test_jaccard_no_overlap()` - No common words return 0.0
- `test_jaccard_partial_overlap()` - Partial overlap returns fraction
- `test_jaccard_different_case()` - Case-insensitive comparison
- `test_jaccard_empty_text()` - Empty text returns 0.0
- `test_jaccard_one_empty()` - One empty text returns 0.0
- `test_jaccard_example_calculation()` - Known example verified

#### Test Class: `TestOverlapSimilarity`
- `test_overlap_identical_texts()` - Identical texts return 1.0
- `test_overlap_no_overlap()` - No overlap returns 0.0
- `test_overlap_subset()` - Complete subset returns 1.0
- `test_overlap_partial_overlap()` - Partial overlap calculated correctly
- `test_overlap_different_lengths()` - Shorter text determines denominator
- `test_overlap_empty_text()` - Empty text returns 0.0

#### Test Class: `TestWeightedSimilarity`
- `test_weighted_identical_texts()` - Identical returns high score
- `test_weighted_no_overlap()` - No overlap returns 0.0
- `test_weighted_rare_terms_higher_weight()` - Rare words weighted more
- `test_weighted_common_terms_lower_weight()` - Common words weighted less
- `test_weighted_with_custom_corpus()` - Custom corpus used for IDF
- `test_weighted_without_corpus()` - Defaults to using both texts
- `test_weighted_empty_text()` - Empty text returns 0.0
- `test_weighted_normalization()` - Scores normalized to [0, 1]

#### Test Class: `TestComputeSimilarity`
- `test_compute_jaccard_method()` - Calls jaccard_similarity
- `test_compute_weighted_method()` - Calls weighted_similarity
- `test_compute_overlap_method()` - Calls overlap_similarity
- `test_compute_invalid_method_raises()` - Invalid method raises ValueError
- `test_compute_passes_corpus()` - Corpus passed to weighted method

---

### File 7: `test_training.py`

#### Test Class: `TestTrainAsync`
- `test_train_async_full_pipeline()` - Complete pipeline executes (all mocked)
- `test_train_async_checks_system_stable()` - ensure_system_stable called
- `test_train_async_raises_if_unstable()` - RuntimeError if candidate exists
- `test_train_async_fetches_active_prompt()` - get_active_prompt called
- `test_train_async_raises_if_no_active_prompt()` - ValueError if no active
- `test_train_async_configures_dspy()` - dspy.configure called with LM
- `test_train_async_builds_dataset()` - build_golden_dataset called
- `test_train_async_uses_custom_strategy()` - Custom strategy passed to dataset
- `test_train_async_converts_to_dspy_examples()` - convert_to_dspy_examples called
- `test_train_async_creates_agent_program()` - AgentProgram instantiated
- `test_train_async_validates_optimizer()` - Raises if optimizer is None
- `test_train_async_validates_optimizer_type()` - Raises if not SIMBA/GEPA
- `test_train_async_runs_optimization()` - optimize() called
- `test_train_async_extracts_instructions()` - Instructions extracted from program
- `test_train_async_raises_if_no_instructions()` - RuntimeError if empty instructions
- `test_train_async_inserts_candidate_prompt()` - insert_prompt called with candidate
- `test_train_async_updates_active_traffic()` - update_prompt_traffic called for active
- `test_train_async_zeros_other_prompts()` - zero_out_all_except called
- `test_train_async_uses_did_isolation()` - DID passed through all operations
- `test_train_async_disconnects_storage()` - Storage.disconnect called in finally
- `test_train_async_disconnects_on_error()` - Disconnect even if error occurs

#### Test Class: `TestTrain`
- `test_train_calls_asyncio_run()` - asyncio.run called with train_async
- `test_train_raises_if_in_event_loop()` - RuntimeError if already in async context
- `test_train_passes_parameters()` - All parameters passed to train_async
- `test_train_with_default_params()` - Works with all defaults

---

### File 8: `test_prompts_and_guard.py`

#### Test Class: `TestGetStorage`
- `test_get_storage_reuses_provided()` - Returns provided storage, should_disconnect=False
- `test_get_storage_creates_new()` - Creates PostgresStorage, should_disconnect=True
- `test_get_storage_uses_did()` - DID passed to PostgresStorage constructor
- `test_get_storage_connects_new()` - connect() called on new storage

#### Test Class: `TestGetActivePrompt`
- `test_get_active_prompt_success()` - Returns prompt dict
- `test_get_active_prompt_with_storage()` - Uses provided storage
- `test_get_active_prompt_creates_storage()` - Creates storage if None
- `test_get_active_prompt_disconnects_new_storage()` - Disconnects only new storage
- `test_get_active_prompt_uses_did()` - DID passed to storage
- `test_get_active_prompt_returns_none()` - Returns None if no active

#### Test Class: `TestGetCandidatePrompt`
- `test_get_candidate_prompt_success()` - Returns prompt dict
- `test_get_candidate_prompt_with_storage()` - Uses provided storage
- `test_get_candidate_prompt_disconnects()` - Proper disconnect behavior
- `test_get_candidate_prompt_returns_none()` - Returns None if no candidate

#### Test Class: `TestInsertPrompt`
- `test_insert_prompt_success()` - Returns prompt ID
- `test_insert_prompt_calls_storage()` - storage.insert_prompt called
- `test_insert_prompt_with_all_params()` - All parameters passed correctly
- `test_insert_prompt_disconnects()` - Disconnects new storage
- `test_insert_prompt_invalid_traffic()` - Raises ValueError for traffic > 1.0

#### Test Class: `TestUpdatePromptTraffic`
- `test_update_traffic_success()` - Updates traffic successfully
- `test_update_traffic_calls_storage()` - storage.update_prompt_traffic called
- `test_update_traffic_disconnects()` - Disconnects new storage
- `test_update_traffic_validates_range()` - Validates traffic in [0, 1]

#### Test Class: `TestUpdatePromptStatus`
- `test_update_status_success()` - Updates status successfully
- `test_update_status_calls_storage()` - storage.update_prompt_status called
- `test_update_status_disconnects()` - Disconnects new storage

#### Test Class: `TestZeroOutAllExcept`
- `test_zero_out_success()` - Zeros out other prompts
- `test_zero_out_calls_storage()` - storage.zero_out_all_except called
- `test_zero_out_with_multiple_ids()` - Multiple IDs preserved
- `test_zero_out_disconnects()` - Disconnects new storage

#### Test Class: `TestEnsureSystemStable`
- `test_ensure_stable_no_candidate()` - Passes if no candidate
- `test_ensure_stable_with_candidate_raises()` - Raises RuntimeError if candidate exists
- `test_ensure_stable_uses_provided_storage()` - Uses provided storage
- `test_ensure_stable_uses_did()` - DID passed to get_candidate_prompt
- `test_ensure_stable_logs_correctly()` - Proper logging messages

#### Test Class: `TestSelectPromptWithCanary`
- `test_select_no_prompts()` - Returns None if no prompts
- `test_select_only_active()` - Returns active if no candidate
- `test_select_only_candidate()` - Returns candidate if no active
- `test_select_weighted_random()` - Weighted random selection logic
- `test_select_active_chosen()` - Active selected based on traffic
- `test_select_candidate_chosen()` - Candidate selected based on traffic
- `test_select_zero_traffic()` - Defaults to active if both have 0 traffic
- `test_select_normalizes_traffic()` - Traffic normalized to sum to 1.0
- `test_select_uses_did()` - DID passed to prompt functions

---

### File 9: `test_canary_controller.py`

#### Test Class: `TestCompareMetrics`
- `test_compare_candidate_not_enough_interactions()` - Returns None if below threshold
- `test_compare_candidate_no_feedback()` - Returns None if no feedback scores
- `test_compare_candidate_winning()` - Returns "candidate" if higher score
- `test_compare_active_winning()` - Returns "active" if higher score
- `test_compare_tied_scores()` - Returns None if scores equal
- `test_compare_missing_active_score()` - Returns None if active score missing
- `test_compare_missing_candidate_score()` - Returns None if candidate score missing
- `test_compare_logs_correctly()` - Proper logging for each case

#### Test Class: `TestPromoteStep`
- `test_promote_increases_candidate_traffic()` - Candidate traffic increased by step
- `test_promote_decreases_active_traffic()` - Active traffic decreased by step
- `test_promote_caps_at_one()` - Candidate traffic capped at 1.0
- `test_promote_floors_at_zero()` - Active traffic floored at 0.0
- `test_promote_calls_update_traffic()` - update_prompt_traffic called twice
- `test_promote_checks_stabilization()` - _check_stabilization called
- `test_promote_uses_storage()` - Provided storage used
- `test_promote_uses_did()` - DID passed to update operations

#### Test Class: `TestRollbackStep`
- `test_rollback_decreases_candidate_traffic()` - Candidate traffic decreased
- `test_rollback_increases_active_traffic()` - Active traffic increased
- `test_rollback_caps_and_floors()` - Proper capping at boundaries
- `test_rollback_calls_update_traffic()` - update_prompt_traffic called
- `test_rollback_checks_stabilization()` - _check_stabilization called

#### Test Class: `TestCheckStabilization`
- `test_stabilization_active_won()` - Candidate set to rolled_back when active=1.0
- `test_stabilization_candidate_won()` - Candidate promoted, active deprecated
- `test_stabilization_not_stabilized()` - No status update if not at boundaries
- `test_stabilization_calls_update_status()` - update_prompt_status called
- `test_stabilization_uses_storage()` - Storage used for updates

#### Test Class: `TestRunCanaryController`
- `test_run_no_candidate()` - Returns early if no candidate
- `test_run_no_active()` - Logs warning if no active
- `test_run_compare_metrics_called()` - compare_metrics called
- `test_run_promote_on_candidate_win()` - promote_step called if candidate wins
- `test_run_rollback_on_active_win()` - rollback_step called if active wins
- `test_run_no_action_on_tie()` - No action if compare returns None
- `test_run_creates_storage()` - PostgresStorage created
- `test_run_connects_storage()` - Storage.connect called
- `test_run_disconnects_storage()` - Storage.disconnect called in finally
- `test_run_disconnects_on_error()` - Disconnect even on error
- `test_run_uses_did()` - DID passed to all operations

---

### File 10: `test_dspy_wrappers.py`

#### Test Class: `TestAgentSignature`
- `test_signature_has_input_field()` - input field defined
- `test_signature_has_output_field()` - output field defined
- `test_signature_input_description()` - Input field has description
- `test_signature_output_description()` - Output field has description
- `test_signature_is_dspy_signature()` - Inherits from dspy.Signature

#### Test Class: `TestAgentProgram`
- `test_program_initialization()` - Program created with prompt text
- `test_program_stores_instructions()` - instructions attribute set
- `test_program_creates_predictor()` - Predict(AgentSignature) created
- `test_program_forward_method()` - forward() returns dspy.Prediction
- `test_program_forward_calls_predictor()` - predictor called with input
- `test_program_is_dspy_module()` - Inherits from dspy.Module

#### Test Class: `TestOptimize`
- `test_optimize_validates_compile_method()` - Raises TypeError if no compile()
- `test_optimize_calls_optimizer_compile()` - optimizer.compile() called
- `test_optimize_passes_program_and_dataset()` - Correct parameters passed
- `test_optimize_returns_optimized_program()` - Returns compiled program
- `test_optimize_logs_correctly()` - Proper logging messages
- `test_optimize_with_simba()` - Works with SIMBA optimizer
- `test_optimize_with_gepa()` - Works with GEPA optimizer

#### Test Class: `TestFeedbackMetric`
- `test_metric_uses_explicit_feedback()` - Returns feedback score if available
- `test_metric_fallback_exact_match()` - Falls back to exact match
- `test_metric_exact_match_success()` - Returns 1.0 for exact match
- `test_metric_exact_match_failure()` - Returns 0.0 for no match
- `test_metric_no_prediction_output()` - Returns 0.0 if no output
- `test_metric_empty_output()` - Returns 0.0 for empty output
- `test_metric_normalizes_score()` - Feedback score converted to float

#### Test Class: `TestParseStrategy`
- `test_parse_last_turn()` - Returns LastTurnStrategy
- `test_parse_full_history()` - Returns FullHistoryStrategy
- `test_parse_last_n()` - Returns LastNTurnsStrategy with n_turns
- `test_parse_first_n()` - Returns FirstNTurnsStrategy with n_turns
- `test_parse_invalid_raises()` - Raises ValueError for unknown
- `test_parse_last_n_extracts_number()` - Correctly parses "last_n:5"

#### Test Class: `TestTrainCLI`
- `test_cli_train_main_simba()` - main() with --optimizer=simba
- `test_cli_train_main_gepa()` - main() with --optimizer=gepa
- `test_cli_train_with_strategy()` - --strategy parameter parsed
- `test_cli_train_with_require_feedback()` - --require-feedback flag
- `test_cli_train_with_did()` - --did parameter passed
- `test_cli_train_optimizer_params()` - bsize, num_candidates, max_steps
- `test_cli_train_calls_train()` - train() function called with args

#### Test Class: `TestCanaryCLI`
- `test_cli_canary_main()` - main() runs run_canary_controller
- `test_cli_canary_with_did()` - --did parameter passed
- `test_cli_canary_calls_asyncio_run()` - asyncio.run called

---

## Mock Fixtures and Helpers

Create a `conftest.py` in `tests/unit/dspy/` with common fixtures:

```python
"""Pytest fixtures for DSPy unit tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from bindu.dspy.models import Interaction, RawTaskData


@pytest.fixture
def mock_storage():
    """Mock PostgresStorage instance."""
    storage = AsyncMock()
    storage.connect = AsyncMock()
    storage.disconnect = AsyncMock()
    storage.fetch_tasks_with_feedback = AsyncMock(return_value=[])
    storage.get_active_prompt = AsyncMock(return_value=None)
    storage.get_candidate_prompt = AsyncMock(return_value=None)
    storage.insert_prompt = AsyncMock(return_value=1)
    storage.update_prompt_traffic = AsyncMock()
    storage.update_prompt_status = AsyncMock()
    storage.zero_out_all_except = AsyncMock()
    return storage


@pytest.fixture
def sample_interaction():
    """Create a sample Interaction for testing."""
    return Interaction(
        id=uuid4(),
        user_input="What is the capital of France?",
        agent_output="The capital of France is Paris.",
        feedback_score=0.9,
        feedback_type="rating",
    )


@pytest.fixture
def sample_raw_task():
    """Create a sample RawTaskData for testing."""
    return RawTaskData(
        id=uuid4(),
        history=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ],
        created_at="2026-01-28T00:00:00Z",
        feedback_data={"rating": 4},
    )


@pytest.fixture
def sample_messages():
    """Create sample cleaned messages."""
    return [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First answer"},
        {"role": "user", "content": "Second question"},
        {"role": "assistant", "content": "Second answer"},
    ]


@pytest.fixture
def mock_dspy_lm():
    """Mock dspy.LM for testing."""
    return MagicMock()


@pytest.fixture
def mock_optimizer():
    """Mock DSPy optimizer with compile method."""
    optimizer = MagicMock()
    optimizer.compile = MagicMock(return_value=MagicMock())
    return optimizer
```

---

## Testing Guidelines

### 1. Async Testing
```python
@pytest.mark.asyncio
async def test_async_function():
    mock_storage = AsyncMock()
    result = await function_under_test(storage=mock_storage)
    assert result is not None
```

### 2. Mocking Storage
```python
@pytest.mark.asyncio
async def test_with_storage(mock_storage):
    mock_storage.get_active_prompt.return_value = {
        "id": 1,
        "prompt_text": "You are helpful.",
        "status": "active",
        "traffic": 1.0,
    }
    result = await get_active_prompt(storage=mock_storage)
    assert result["id"] == 1
    mock_storage.get_active_prompt.assert_called_once()
```

### 3. Mocking DSPy Components
```python
def test_optimizer(mock_optimizer):
    from bindu.dspy.program import AgentProgram
    program = AgentProgram("Be helpful")
    
    with patch("dspy.configure"):
        result = optimize(program, [], mock_optimizer)
        mock_optimizer.compile.assert_called_once()
```

### 4. Parametrized Tests
```python
@pytest.mark.parametrize("feedback_data,expected", [
    ({"rating": 1}, (0.2, "rating")),
    ({"rating": 5}, (1.0, "rating")),
    ({"thumbs_up": True}, (1.0, "thumbs_up")),
    ({"thumbs_up": False}, (0.0, "thumbs_up")),
    (None, (None, None)),
])
def test_normalize_feedback(feedback_data, expected):
    assert normalize_feedback(feedback_data) == expected
```

### 5. Testing Exceptions
```python
def test_raises_value_error():
    with pytest.raises(ValueError, match="Unknown strategy"):
        get_strategy("invalid_strategy_name")
```

### 6. Mocking Settings
```python
from unittest.mock import patch

def test_with_custom_settings():
    with patch("bindu.dspy.dataset.app_settings") as mock_settings:
        mock_settings.dspy.min_examples = 5
        # Test code that uses settings
```

---

## Coverage Goals

- **Target:** 90%+ line coverage for all dspy modules
- **Critical paths:** 100% coverage for:
  - Error handling and validation
  - Database connection lifecycle
  - A/B test traffic calculations
  - Feedback normalization logic
  
---

## Test Execution

### Run all dspy tests:
```bash
pytest tests/unit/dspy/ -v
```

### Run specific test file:
```bash
pytest tests/unit/dspy/test_dataset_pipeline.py -v
```

### Run with coverage:
```bash
pytest tests/unit/dspy/ --cov=bindu.dspy --cov-report=html
```

### Run specific test class:
```bash
pytest tests/unit/dspy/test_strategies_basic.py::TestLastTurnStrategy -v
```

---

## Summary

This test strategy provides:
- ✅ Complete coverage of all 14 dspy modules
- ✅ 10 well-organized test files (chunked by functionality)
- ✅ 300+ specific test cases covering happy paths, edge cases, and errors
- ✅ Clear mocking strategies for external dependencies
- ✅ Consistent patterns following existing codebase conventions
- ✅ Async test support for all async functions
- ✅ Fixtures for common test data and mocks

**Next Steps:** Implement test files one by one following this strategy, starting with simpler modules (models, similarity) and progressing to complex ones (training, canary controller).
