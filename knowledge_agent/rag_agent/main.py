from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_groq import ChatGroq
import os

from dotenv import load_dotenv

load_dotenv()

emb_model = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en") # Embedding Model
# ollama_model = OllamaLLM(model="llama3.2:latest", num_ctx=1024) # Main LLM Model

groq_model = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.1-8b-instant",
    temperature=0
)

parser = StrOutputParser()

app = FastAPI()

class RAGrequest(BaseModel):
    text : str
    query : str

@app.post("/chat")
def get_answer(payload: RAGrequest):

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(payload.text)
    docs = [Document(page_content=chunk) for chunk in chunks]

    vectorstore = FAISS.from_documents(documents=docs, embedding=emb_model)

    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
    relevant_docs = retriever.invoke(payload.query)

    context = "\n\n".join([doc.page_content for doc in relevant_docs])
    template = PromptTemplate(
        template="""
            You are an assistant. Answer the user's question based only on the below document.
            Document: {docs}
            User's question: {query}
            """,
        input_variables=["docs", "query"]
    )
    final_prompt = template.format(docs=context, query=payload.query)

    # try:
    #     # Try local Ollama first
    #     response = ollama_model.invoke(final_prompt)
    #     used_model = "ollama"

    # except Exception as e:
    #     print("Ollama failed, switching to Groq:", e)

    #     # Fallback to Groq
    response = groq_model.invoke(final_prompt)
    response = response.content  # Groq returns AIMessage
    #     used_model = "groq"


    return JSONResponse(content={"answer": response})