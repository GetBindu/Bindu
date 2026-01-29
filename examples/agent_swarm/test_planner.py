from examples.agent_swarm.planner_agent import build_planner_agent

planner = build_planner_agent()

out = planner.run("Research about AI agents in healthcare")

print(out.to_dict()["content"])
