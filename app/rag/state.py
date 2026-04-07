from typing import TypedDict, List, Optional

class RAGState(TypedDict):
    question: str
    context: List[str]
    answer: str
    use_rag: bool
    scores: List[float]
    chat_history: str
    source_files: List[str]
    user_id: Optional[int]       # added for per-user filtering




class GraphState(TypedDict):
    question: str
    context: List[str]
    scores: List[float]
    use_rag: bool
    answer: str
    chat_history: str  # 🔹 added