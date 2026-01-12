from agents import AgentState
from langchain_core.messages import SystemMessage, AIMessage
from langchain_community.vectorstores import Chroma
from load_base import load_knowledge_base
from config import llm, embeddings

_docs = load_knowledge_base()
_vectorstore = Chroma.from_documents(documents=_docs, embedding=embeddings)
_retriever = _vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})

def rag_responder(state: AgentState) -> dict:
    '''This function retrieves relevant documents from knowledge base and generates a response.'''
    last_user_message = state['messages'][-1].content
    relevant_docs = _retriever.invoke(last_user_message)
    context = "\n\n".join([doc.page_content for doc in relevant_docs])
    system_prompt = f'''
    You are a helpful sales assistant for Inflx by ServiceHive. Use the following context to answer the user's question.
    If the answer is not found in the context, politely say you don't know.
    Question: {last_user_message}
    Context:
    {context}
    '''
    message = [SystemMessage(content=system_prompt)] + state['messages']
    response = llm.invoke(message)
    return {'messages': [AIMessage(content=response.content)]}