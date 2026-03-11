"""
Skill Registry

Central marketplace where agents advertise their capabilities.
"""


class SkillRegistry:

    def __init__(self):
        self.skill_to_agent = {}

    def register_agent(self, agent_name: str, skills: list[str]):
        """
        Register an agent and the skills it provides.
        """
        for skill in skills:
            self.skill_to_agent[skill] = agent_name

    def find_agent(self, request: str):
        """
        Find best agent based on request.
        """

        request = request.lower()

        for skill, agent in self.skill_to_agent.items():
            if skill in request:
                return agent

        # fallback logic
        if "explain" in request or "what is" in request:
            return self.skill_to_agent.get("research")

        return None