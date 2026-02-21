import os
import asyncio
try:
    from bindu import bindufy
except ImportError:
    
    def bindufy(config, handler):
        print(f" Agent '{config['name']}' is configured and ready!")
        print(" Bindu library not found locally, skipping server start.")

try:
    from langchain_openai import ChatOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class FakePirateModel:
    async def ainvoke(self, input_data):
        return "Arrr! I have no API key, but I still be sailin' the digital seas! (Mock Response)"

def get_chain():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or not HAS_OPENAI:
        return FakePirateModel()

    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    
    prompt = ChatPromptTemplate.from_template("Answer in pirate style: {question}")
    model = ChatOpenAI(model="gpt-3.5-turbo")
    return prompt | model | StrOutputParser()


async def handler(messages) -> str:
    user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), None)
    if not user_msg: return "Arrr!"
    
    chain = get_chain()
    if isinstance(chain, FakePirateModel):
        return await chain.ainvoke(None)
    return await chain.ainvoke({"question": user_msg})


config = {
    "author": "contributor", 
    "name": "langchain_pirate",
    "description": "A LangChain example (Mock/Real)",
    "version": "0.1.0",
    "deployment": {"url": "http://localhost:3773", "expose": True}
}

if __name__ == "__main__":
    print("Starting LangChain Pirate Agent")
    bindufy(config, handler)