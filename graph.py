from langgraph.graph import StateGraph, START, END
from state import State
from node import retrieve_node, generate_node, fallback_node, is_retrieval_sufficient
grapghbuilder = StateGraph(State) 


grapghbuilder.add_node("retreiver",retrieve_node)
grapghbuilder.add_node("generate_answer",generate_node)
grapghbuilder.add_node("web_search",fallback_node)




grapghbuilder.add_edge(START,"retreiver")
grapghbuilder.add_conditional_edges(
    "retreiver",
    is_retrieval_sufficient,
    {
        "generate": "generate_answer",
        "fallback": "web_search"
    }
)

grapghbuilder.add_edge("web_search", "generate_answer")
grapghbuilder.add_edge("generate_answer", END)

app = grapghbuilder.compile()


