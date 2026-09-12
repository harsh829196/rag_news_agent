from langchain_tavily import TavilySearch
from llm.llm import model
from state import State
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
from embedding import EmbeddingManager
from database.chromadb import collection

embedding_model = EmbeddingManager()

def retrieve_node(state: State):
    query = state["query"]
    query_embedding = embedding_model.Get_embadding(query)
    results = collection.query(query_embeddings=[query_embedding], n_results=5)
    
    docs = []
    for text, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        docs.append({"text": text, "metadata": meta, "distance": dist})
    
    return {"retrieved_docs": docs}

def is_retrieval_sufficient(state: State) -> str:
    if not state["retrieved_docs"]:
        return "fallback"
    best_distance = state["retrieved_docs"][0]["distance"]
    return "fallback" if best_distance > 0.35 else "generate"

def generate_node(state: State):
    query = state["query"]
    docs = state["retrieved_docs"]
    
    context = "\n\n".join(
        f"[{d['metadata'].get('source', 'unknown')}] {d['text']}" 
        for d in docs
    )
    
    prompt = f"""Answer the question using only the context below. 
    If the context doesn't contain enough information, say so.

    Context:
    {context}

    Question: {query}

    Answer:"""
    
    response = model.invoke(prompt)
    
    return {
        "answer": response.content,
        "messages": [response]
    }


def fallback_node(state: State):
    query = state["query"]
    docs = list(state.get("retrieved_docs", []))
    
    tavily = TavilySearch(max_results=3)
    results = tavily.invoke({"query": query})
    
    for r in results.get("results", []):
        docs.append({
            "text": r.get("content", ""),
            "metadata": {
                "source": r.get("url", "web"),
                "title": r.get("title", "")
            },
            "distance": None  # not applicable for web search results
        })
    
    return {"retrieved_docs": docs}

# def tool_calling (query):
#     return {"messages" :model.invoke(query)}

