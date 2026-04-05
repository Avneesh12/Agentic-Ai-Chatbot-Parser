from langgraph.graph import StateGraph
from app.rag.nodes import retrieve, decide, rag, llm
from app.rag.state import GraphState  # 🔹 import from state.py, not defined inline


builder = StateGraph(GraphState)

builder.add_node("retrieve", retrieve)
builder.add_node("decide", decide)
builder.add_node("rag", rag)
builder.add_node("llm", llm)

builder.set_entry_point("retrieve")
builder.add_edge("retrieve", "decide")


def route(state):
    return "rag" if state["use_rag"] else "llm"


builder.add_conditional_edges("decide", route)

builder.set_finish_point("rag")
builder.set_finish_point("llm")

rag_graph = builder.compile()