# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Metric definitions for DSPy prompt optimization.

This module provides evaluation metrics used during DSPy training.
Metrics are designed to score newly generated predictions against
golden reference outputs.

Available metrics:
- embedding: Cosine similarity between embeddings
- llm_judge: LLM-as-judge scoring based on helpfulness and correctness
"""

from __future__ import annotations

from typing import Callable

import dspy
import numpy as np

from bindu.utils.logging import get_logger

logger = get_logger("bindu.dspy.metrics")


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def embedding_similarity_metric() -> Callable:
    """Embedding similarity metric compatible with SIMBA.
    
    Uses dspy.Embedder with OpenAI's text-embedding-3-small model.
    Computes cosine similarity between embeddings of reference vs generated outputs.
    """
    embedder = dspy.Embedder("openai/text-embedding-3-small")

    def metric(example: dspy.Example, pred) -> float:
        try:
            # Get reference output
            reference = example.output
            if not reference:
                return 0.0
            
            # Extract generated output - handle multiple input types
            generated = None
            if pred is None:
                logger.warning("Metric received None prediction")
                return 0.0
            elif isinstance(pred, dict):
                # pred is a dict (could happen with different DSPy versions)
                generated = pred.get("output")
            elif hasattr(pred, 'output'):
                # pred is a dspy.Prediction object
                generated = pred.output
            else:
                logger.warning(f"Unexpected pred type: {type(pred)}")
                return 0.0
            
            if not generated:
                return 0.0

            ref_vec = embedder(reference)
            gen_vec = embedder(generated)

            score = _cosine_similarity(ref_vec, gen_vec)
            return max(0.0, min(1.0, float(score)))

        except Exception as e:
            logger.exception(f"Embedding metric failed: {e}")
            return 0.0

    return metric

def llm_judge_metric() -> Callable:
    """LLM-as-judge metric compatible with SIMBA."""

    judge_signature = dspy.Signature(
        input=dspy.InputField(desc="User input"),
        reference=dspy.InputField(desc="Reference answer"),
        generated=dspy.InputField(desc="Generated answer"),
        score=dspy.OutputField(desc="Score between 0 and 1"),
    )

    judge = dspy.Predict(judge_signature)

    def metric(example: dspy.Example, pred) -> float:
        try:
            # Get reference output
            reference = example.output
            if not reference:
                return 0.0
            
            # Extract generated output - handle multiple input types
            generated = None
            if pred is None:
                logger.warning("Metric received None prediction")
                return 0.0
            elif isinstance(pred, dict):
                # pred is a dict (could happen with different DSPy versions)
                generated = pred.get("output")
            elif hasattr(pred, 'output'):
                # pred is a dspy.Prediction object
                generated = pred.output
            else:
                logger.warning(f"Unexpected pred type: {type(pred)}")
                return 0.0
            
            if not generated:
                return 0.0

            result = judge(
                input=example.input,
                reference=reference,
                generated=generated,
            )

            raw = result.score.strip()
            score = float(raw)

            return max(0.0, min(1.0, score))

        except Exception as e:
            logger.exception(f"LLM judge metric failed: {e}")
            return 0.0

    return metric

def get_metric(metric_type: str) -> Callable:
    """Factory method for metric selection."""

    metric_type = metric_type.lower()

    if metric_type == "embedding":
        logger.info("Using embedding similarity metric")
        return embedding_similarity_metric()

    if metric_type == "llm_judge":
        logger.info("Using LLM judge metric")
        return llm_judge_metric()

    raise ValueError(
        f"Unknown metric type '{metric_type}'. "
        "Available options: embedding, llm_judge"
    )