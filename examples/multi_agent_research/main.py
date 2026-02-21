from examples.multi_agent_research.workflow.graph import run_pipeline


def main():
    query = input("Enter your query: ")

    search_result, summary, verification = run_pipeline(query)

    print("\n===== FINAL OUTPUT =====")

    print("\nSearch Result:\n")
    print(search_result)

    print("\nSummary:\n")
    print(summary)

    print("\nVerification:\n")
    print(verification)


if __name__ == "__main__":
    main()