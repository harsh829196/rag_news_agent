from langgraph.graph.message import add_messages
from  typing_extensions import TypedDict
from typing import Annotated,Optional
class State(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    retrieved_docs: list[dict]           # chunks from retrieval
    route_decision: Optional[str]        # "single_search" or "compare_outlets"
    outlet_results: Optional[dict]       # for cross-outlet comparison
    answer: Optional[str]