# Importing Important Libraries

import os
os.environ["TF_ENABLE_ONEDNN_OPTS"]="0"
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

# Models We Are Going TO Use 

emb_model = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en") # Embedding Model
model = OllamaLLM(model="llama3.2:latest", num_ctx=1024) # Main LLM Model

# Function To Split The Input Text Into Chunks ( RecursiveCharacterTextSplitter )

def to_chunks(extracted_text):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 500,
        chunk_overlap = 50
    )
    chunks = splitter.split_text(extracted_text)
    return chunks

data = """
        LangChain is a framework for developing applications powered by language models. 
        It enables applications to connect a language model to sources of data, and 
        allows for interaction with that data via natural language.
        """
chunks = to_chunks(data)
docs = [Document(page_content=chunk) for chunk in chunks] # Converting The Chunks To Document So We Can Serve It To FAISS

# Convert The Chunks To Embeddings

vectorstore = FAISS.from_documents(documents=docs, embedding=emb_model)

# Implement Retriver That Takes User Query And Retrieve The Relavant Content From The Vector Store

query = "What is langchain?"
retriever = vectorstore.as_retriever(search_type="similarity", kwargs={"k":1})
retrieved_docs = retriever.invoke(query)

# Making Prompt Template So It Can Serve To LLM

template = PromptTemplate(
      input_variables=["docs", "query"],
    template="""
    You are a helpful assistant. Use the context below to answer the user's question.

    Context:
    {docs}

    Question:
    {query}
    """
)

# Formating The Prompt 

prompt = template.format(docs=retrieved_docs[0].page_content, query=query)

# Finale Response

response = model.invoke(prompt)
print(response)