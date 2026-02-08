# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""DSPy program module for agent response generation.

This module defines the agent program whose prompt will be optimized using
DSPy's teleprompter system. The program represents the core logic that
processes inputs and generates responses.
"""

from __future__ import annotations

import dspy

from .signature import AgentSignature


class AgentProgram(dspy.Module):
    """Agent program for response generation."""

    def __init__(self, current_prompt_text: str) -> None:
        super().__init__()

        self.instructions = current_prompt_text

        self.predictor = dspy.Predict(AgentSignature)

    def forward(self, input: str) -> dspy.Prediction:
        return self.predictor(input=input)