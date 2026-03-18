"""
Router Agent

Routes incoming requests to the appropriate agent.
"""


class RouterAgent:

    def route(self, request: str):

        request = request.lower()

        if "summarize" in request:
            return "summarizer_agent"

        elif "translate" in request:
            return "translator_agent"

        return None