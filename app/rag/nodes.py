"""
RAG graph nodes.

retrieve() now filters by user_id so users only get answers
grounded in their own uploaded documents.
"""

import re
import logging
from app.rag.embedding import embed_text
from app.rag.qdrant_store import client, COLLECTION
from app.services.llm_service import LLMService
from qdrant_client.models import Filter, FieldCondition, MatchValue

logger = logging.getLogger(__name__)

PREAMBLE_PATTERNS = [
    r"^based on the provided context[,.]?\s*",
    r"^based on the context provided[,.]?\s*",
    r"^according to the (provided |given )?context[,.]?\s*",
    r"^from the (provided |given )?context[,.]?\s*",
    r"^the (provided |given )?context (indicates?|suggests?|mentions?|states?)[,.]?\s*",
    r"^it appears that\s*",
    r"^it seems that\s*",
    r"^here are some points about [a-z\s]+:\s*",
    r"^here is (some |the )?information about [a-z\s]+:\s*",
    r"^based on (my |the )?knowledge[,.]?\s*",
    r"^i (can see|found|notice) that\s*",
    r"^the following (information )?(is |was )?found[,.]?\s*",
]


def clean_preamble(text: str) -> str:
    cleaned = text.strip()
    for pattern in PREAMBLE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


async def retrieve(state):
    """
    Embed the question and query Qdrant.
    If user_id is present in state, filter to that user's documents only.
    """
    query = state["question"]
    user_id = state.get("user_id")

    vec = embed_text([query])[0]

    # Build optional user-scoped filter
    query_filter = None
    if user_id is not None:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id),
                )
            ]
        )

    results = client.query_points(
        collection_name=COLLECTION,
        query=vec,
        query_filter=query_filter,
        limit=5,              # top-5 gives more context without blowing the prompt
        with_payload=True,
    ).points

    # Attach source metadata for transparency
    context_docs = []
    source_files = set()
    for r in results:
        context_docs.append(r.payload["text"])
        source_files.add(r.payload.get("filename", "unknown"))

    return {
        **state,
        "context": context_docs,
        "scores": [r.score for r in results],
        "source_files": list(source_files),
    }


async def decide(state):
    scores = state.get("scores", [])
    # Require at least one result with score > 0.30
    use_rag = bool(scores) and max(scores) > 0.30
    return {**state, "use_rag": use_rag}


async def rag(state):
    chat_history = state.get("chat_history", "")
    context_docs = state.get("context", [])
    source_files = state.get("source_files", [])

    if not context_docs:
        return {
            **state,
            "answer": (
                "I don't have enough information in your knowledge base to answer this. "
                "Please upload relevant documents first."
            ),
        }

    context_text = "\n\n".join(
        f"[Chunk {i+1} | Source: {state.get('source_files', ['?'])[0] if i == 0 else '...'}]\n{doc}"
        for i, doc in enumerate(context_docs)
    )

    source_hint = (
        f"\n\nSources used: {', '.join(source_files)}" if source_files else ""
    )

    prompt = f"""You are a precise and professional assistant.

STRICT RULES:
- Answer ONLY using the context provided below
- Do NOT mention websites, links, or external resources
- Do NOT say "I recommend checking..." or "you can visit..."
- Do NOT make up anything not present in the context
- If the answer is not in the context, say exactly: "This information is not available in the provided documents."
- Be direct, factual, and well-structured
- Use bullet points when listing multiple items

─────────────────────────────
CONTEXT:
{context_text}
─────────────────────────────
CONVERSATION HISTORY:
{chat_history}
─────────────────────────────
QUESTION: {state['question']}

ANSWER:"""

    ans = await LLMService.generate_response(prompt)
    return {
        **state,
        "answer": clean_preamble(ans) + source_hint,
    }


async def llm(state):
    chat_history = state.get("chat_history", "")

    prompt = f"""You are a helpful and precise assistant.

STRICT RULES:
- Answer directly and confidently from your knowledge
- Do NOT suggest visiting websites or external links unless explicitly asked
- Do NOT say "I recommend checking..." or "you can visit..."
- Do NOT say "as an AI I cannot..." — just answer
- If you truly don't know, say: "I don't have information about this."
- Be concise and well-structured
- Use bullet points when listing multiple items

─────────────────────────────
CONVERSATION HISTORY:
{chat_history}
─────────────────────────────
QUESTION: {state['question']}

ANSWER:"""

    ans = await LLMService.generate_response(prompt)
    return {**state, "answer": clean_preamble(ans)}
