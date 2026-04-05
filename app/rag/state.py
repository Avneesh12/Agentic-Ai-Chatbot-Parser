from typing import TypedDict, List

class RAGState(TypedDict):
    question: str
    context: List[str]
    answer: str
    use_rag: bool
    scores: List[float]


class GraphState(TypedDict):
    question: str
    context: List[str]
    scores: List[float]
    use_rag: bool
    answer: str
    chat_history: str  # 🔹 added