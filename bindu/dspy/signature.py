# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""DSPy signature definition for agent response generation.

This module defines the input-output signature used by DSPy to understand
the structure of the agent's task. The signature specifies what the program
receives as input and what it should produce as output.
"""

from __future__ import annotations

import dspy


class AgentSignature(dspy.Signature):
    """Signature for agent response generation."""

    input = dspy.InputField(desc="User query or request")
    output = dspy.OutputField(desc="Agent response")