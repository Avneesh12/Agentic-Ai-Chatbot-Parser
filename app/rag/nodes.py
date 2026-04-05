from app.rag.embedding import embed_text
from app.rag.qdrant_store import client, COLLECTION
from app.services.llm_service import LLMService

import re

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
    """Remove LLM preamble phrases from the start of the answer."""
    cleaned = text.strip()
    for pattern in PREAMBLE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    # Capitalize first letter
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned

async def retrieve(state):
    query = state["question"]
    vec = embed_text([query])[0]

    results = client.query_points(
        collection_name=COLLECTION,
        query=vec,
        limit=3,
        with_payload=True
    ).points

    return {
        **state,
        "context": [r.payload["text"] for r in results],
        "scores": [r.score for r in results],
    }


async def decide(state):
    scores = state.get("scores", [])

    # 🔹 lowered threshold + must have results
    use_rag = len(scores) > 0 and max(scores) > 0.30

    return {
        **state,
        "use_rag": use_rag
    }


async def rag(state):
    chat_history = state.get("chat_history", "")
    context_docs = state.get("context", [])

    # 🔹 honest fallback if no context
    if not context_docs:
        return {
            **state,
            "answer": "I don't have enough information in my knowledge base to answer this. Please upload relevant documents first."
        }

    context_text = "\n\n".join(
        f"[{i+1}] {doc}" for i, doc in enumerate(context_docs)
    )

    prompt = f"""You are a precise and professional assistant.

STRICT RULES:
- Answer ONLY using the context provided below
- Do NOT mention websites, links, or external resources
- Do NOT say "I recommend checking..." or "you can visit..."
- Do NOT make up anything not present in the context
- If the answer is not in the context, say exactly: "This information is not available in the provided documents."
- Be direct, factual, and well structured
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
        "answer": clean_preamble(ans)
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
- Be concise and well structured
- Use bullet points when listing multiple items

─────────────────────────────
CONVERSATION HISTORY:
{chat_history}
─────────────────────────────
QUESTION: {state['question']}

ANSWER:"""

    ans = await LLMService.generate_response(prompt)
    return {
        **state,
        "answer": clean_preamble(ans)
    }
    
    
    

    
    
    