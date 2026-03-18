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

from bindu.utils.logging import get_logger
from .signature import AgentSignature

logger = get_logger("bindu.dspy.program")


# class AgentProgram(dspy.Module):
#     """Agent program for response generation."""

#     def __init__(self, current_prompt_text: str) -> None:
#         super().__init__()

#         self.instructions = current_prompt_text

#         self.predictor = dspy.Predict(AgentSignature)

#     def forward(self, input: str) -> dspy.Prediction:
#         return self.predictor(input=input)

class AgentProgram(dspy.Module):
    """Agent program for response generation."""

    def __init__(self, current_prompt_text: str) -> None:
        super().__init__()

        # Inject system prompt into signature so SIMBA can mutate it
        signature = AgentSignature.with_instructions(current_prompt_text)

        self.predictor = dspy.Predict(signature)

    @property
    def instructions(self) -> str:
        """Get the current instructions from the signature.
        
        The instructions are stored in the signature and can be modified by
        optimizers like SIMBA during training. This property provides easy access
        to the current instructions without needing to navigate the nested structure.
        
        Returns:
            The current instructions string from the signature
        """
        return self.predictor.signature.instructions

    def forward(self, input: str) -> dspy.Prediction:
        try:
            prediction = self.predictor(input=input)
            
            # Validate prediction has required output field
            if prediction is None:
                logger.error(f"Predictor returned None for input: {input[:50]}...")
                return None
            
            if not hasattr(prediction, 'output'):
                logger.error(f"Prediction missing 'output' field. Prediction: {prediction}")
                return None
            
            logger.debug(f"Generated output: {str(prediction.output)[:100]}...")
            return prediction
        except Exception as e:
            logger.exception(f"Error in AgentProgram.forward(): {e}")
            return None