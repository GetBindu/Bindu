import os
from groq import Groq

MODEL = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


class ResearchAgent:

    async def run(self, query: str):

        prompt = f"""
        Provide a clear explanation for the following topic.

        {query}
        """

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.choices[0].message.content