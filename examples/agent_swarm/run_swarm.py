from examples.agent_swarm.orchestrator import Orchestrator

if __name__ == "__main__":
    orchestrator = Orchestrator()

    query = "Explain Quantum Computing simply"

    final_answer = orchestrator.run(query)

    print("\n🔥 FINAL ANSWER 🔥\n")
    print(final_answer)
