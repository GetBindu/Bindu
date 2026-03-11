"""
Router Agent

Routes incoming requests to the appropriate agent.
"""


class RouterAgent:

    def __init__(self, registry):
        self.registry = registry

    def route(self, request: str):

        agent = self.registry.find_agent(request)

        return agent