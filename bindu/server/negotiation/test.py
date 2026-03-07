"""
Manual test suite for CapabilityCalculator

Run:
    python test_capability_calculator.py
"""

from pprint import pprint

from bindu.server.negotiation.capability_calculator import (
    CapabilityCalculator,
)


def print_section(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def build_calculator():
    # Fake skill definition
    skills = [
        {
            "id": "skill_text_summarizer",
            "name": "Text Summarizer",
            "tags": ["text", "nlp", "summary"],
            "input_modes": ["text/plain"],
            "output_modes": ["text/plain"],
            "allowed_tools": ["openai"],
            "performance": {"avg_processing_time_ms": 800},
            "capabilities_detail": {
                "summarize_text": {},
                "analyze_text": {},
            },
        }
    ]

    return CapabilityCalculator(skills=skills)


def test_normal_accept():
    print_section("TEST 1: Normal Acceptance")

    calculator = build_calculator()

    result = calculator.calculate(
        task_summary="Summarize this document",
        input_mime_types=["text/plain"],
        output_mime_types=["text/plain"],
        max_latency_ms=1000,
        queue_depth=2,
        debug=True,
    )

    print("Accepted:", result.accepted)
    print("Score:", result.score)
    print("Confidence:", result.confidence)
    print("Latency Estimate:", result.latency_estimate_ms)
    print("Subscores:")
    pprint(result.subscores)
    print("Debug Trace:")
    pprint(result.debug_trace)


def test_normal_accept():
    print_section("TEST 1: Normal Acceptance")

    calculator = build_calculator()

    result = calculator.calculate(
        task_summary="Summarize this document",
        input_mime_types=["text/plain"],
        output_mime_types=["text/plain"],
        max_latency_ms=1000,
        queue_depth=2,
        debug=False,
    )

    print("Accepted:", result.accepted)
    print("Score:", result.score)
    print("Confidence:", result.confidence)
    print("Latency Estimate:", result.latency_estimate_ms)
    print("Subscores:")
    pprint(result.subscores)
    print("Debug Trace:")
    # pprint(result.debug_trace)


def test_hard_constraint_rejection():
    print_section("TEST 2: Hard Constraint Rejection")

    calculator = build_calculator()

    result = calculator.calculate(
        task_summary="Summarize this document",
        input_mime_types=["image/png"],  # Unsupported
        debug=True,
    )

    print("Accepted:", result.accepted)
    print("Rejection Reason:", result.rejection_reason)
    print("Debug Trace:")
    pprint(result.debug_trace)


def test_latency_rejection():
    print_section("TEST 3: Latency Rejection")

    calculator = build_calculator()

    result = calculator.calculate(
        task_summary="Summarize this document",
        input_mime_types=["text/plain"],
        output_mime_types=["text/plain"],
        max_latency_ms=200,  # Too strict (800 > 200 * 2)
        debug=True,
    )

    print("Accepted:", result.accepted)
    print("Rejection Reason:", result.rejection_reason)
    print("Latency Estimate:", result.latency_estimate_ms)


def test_cost_rejection():
    print_section("TEST 4: Cost Rejection")

    skills = [
        {
            "id": "skill_text_summarizer",
            "name": "Text Summarizer",
            "tags": ["text", "nlp", "summary"],
            "input_modes": ["text/plain"],
            "output_modes": ["text/plain"],
            "allowed_tools": ["openai"],
            "performance": {"avg_processing_time_ms": 800},
            "capabilities_detail": {"summarize_text": {}},
        }
    ]

    x402_extension = {
        "amount": "10.0"  # Agent costs 10
    }

    calculator = CapabilityCalculator(
        skills=skills,
        x402_extension=x402_extension,
    )

    result = calculator.calculate(
        task_summary="Summarize this document",
        input_mime_types=["text/plain"],
        output_mime_types=["text/plain"],
        max_cost_amount="5.0",  # Budget too low
        debug=True,
    )

    print("Accepted:", result.accepted)
    print("Rejection Reason:", result.rejection_reason)


def test_no_skills():
    print_section("TEST 5: No Skills Advertised")

    calculator = CapabilityCalculator(skills=[])

    result = calculator.calculate(
        task_summary="Summarize this document",
        debug=True,
    )

    print("Accepted:", result.accepted)
    print("Rejection Reason:", result.rejection_reason)


if __name__ == "__main__":
    test_normal_accept()
    test_hard_constraint_rejection()
    test_latency_rejection()
    test_cost_rejection()
    test_no_skills()

    print("\nALL TESTS EXECUTED\n")
