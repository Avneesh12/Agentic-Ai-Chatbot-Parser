from fastapi import APIRouter, WebSocket, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from app.db.deps import get_db
from app.models.chat import Chat
from app.models.user import User
from app.agent.main_agent import run_agent
from app.rag.graph import rag_graph
from app.core.security import decode_token
from app.core.cache import cache_get, cache_set, cache_delete_pattern, make_key
from app.core.config import settings
import hashlib

router = APIRouter()

HALLUCINATION_SIGNALS = [
    "can be inferred", "likely", "probably",
    "i would recommend", "you can visit",
    "their website", "official website",
    "contact page", "reach out to",
    "check the following", "youtube channel",
]

def is_hallucinated(answer: str) -> bool:
    return any(s in answer.lower() for s in HALLUCINATION_SIGNALS)


@router.websocket("/ws/chat/")
async def websocket_chat(
    ws: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    # ─── Auth check BEFORE accept ──────────────────────────────────────────
    payload = decode_token(token)
    if not payload:
        await ws.close(code=4001)
        return

    user_id = payload.get("sub")
    if not user_id:
        await ws.close(code=4001)
        return

    # 🔹 Fetch real user from DB to get email
    result = await db.execute(select(User).where(User.id == int(user_id)))
    current_user = result.scalar_one_or_none()
    if not current_user or not current_user.is_active:
        await ws.close(code=4001)
        return

    # 🔹 Use email as the user identifier for chat history
    user_email = current_user.email

    await ws.accept()

    try:
        while True:
            message = await ws.receive_text()

            # ─── Chat history — check cache first ──────────────────────────
            history_key = make_key("chat_history", user_email)
            chat_history = await cache_get(history_key)

            if chat_history is None:
                print(f"[CACHE] MISS chat_history for {user_email}")
                result = await db.execute(
                    select(Chat)
                    .where(Chat.user == user_email)
                    .order_by(Chat.created_at.desc())
                    .limit(5)
                )
                chats = list(reversed(result.scalars().all()))
                chat_history = "\n".join([
                    f"User: {c.question}\nAI: {c.answer}"
                    for c in chats
                ])
                await cache_set(history_key, chat_history, settings.CACHE_TTL_CHAT_HISTORY)
            else:
                print(f"[CACHE] HIT chat_history for {user_email}")

            await ws.send_json({"type": "status", "message": "processing"})

            full_answer = ""
            source = "LLM"
            tool_name = None
            tool_result = None

            # ─── Agent answer — check cache first ──────────────────────────
            answer_key = make_key("agent_answer", user_email, message)
            cached_answer = await cache_get(answer_key)

            if cached_answer:
                print(f"[CACHE] HIT agent_answer")
                full_answer = cached_answer["answer"]
                source = cached_answer["source"]
                tool_name = cached_answer.get("tool")
                tool_result = cached_answer.get("tool_result")
                # Stream cached answer word by word
                for word in full_answer.split(" "):
                    await ws.send_json({"type": "stream", "chunk": word + " "})
            else:
                print(f"[CACHE] MISS agent_answer")

                agent_result = await run_agent(message, chat_history)
                mode = agent_result.get("mode", "llm")

                if mode == "tool":
                    tool_name = agent_result.get("tool")
                    tool_result = agent_result.get("result")
                    full_answer = (
                        json.dumps(tool_result, indent=2)
                        if isinstance(tool_result, (dict, list))
                        else str(tool_result)
                    )
                    source = f"TOOL:{tool_name}"
                    await ws.send_json({"type": "stream", "chunk": full_answer})

                elif mode == "rag":
                    async for chunk in rag_graph.astream({
                        "question": message,
                        "context": [],
                        "chat_history": chat_history,
                        "answer": "",
                        "use_rag": False,
                        "scores": []
                    }):
                        for node_name, state in chunk.items():
                            if node_name in ("rag", "llm") and "answer" in state:
                                token = state["answer"]
                                delta = token[len(full_answer):]
                                if delta:
                                    full_answer = token
                                    source = "RAG" if node_name == "rag" else "LLM"
                                    await ws.send_json({"type": "stream", "chunk": delta})

                    if is_hallucinated(full_answer):
                        full_answer = "This information is not available in the provided documents."
                        await ws.send_json({"type": "stream", "chunk": full_answer})

                elif mode == "llm":
                    full_answer = agent_result.get("answer", "")
                    source = "LLM"
                    if not full_answer:
                        async for chunk in rag_graph.astream({
                            "question": message,
                            "context": [],
                            "chat_history": chat_history,
                            "answer": "",
                            "use_rag": False,
                            "scores": []
                        }):
                            for node_name, state in chunk.items():
                                if node_name == "llm" and "answer" in state:
                                    token = state["answer"]
                                    delta = token[len(full_answer):]
                                    if delta:
                                        full_answer = token
                                        await ws.send_json({"type": "stream", "chunk": delta})
                    else:
                        for word in full_answer.split(" "):
                            await ws.send_json({"type": "stream", "chunk": word + " "})

                elif mode == "error":
                    full_answer = agent_result.get("answer", "Something went wrong.")
                    source = "ERROR"
                    await ws.send_json({"type": "stream", "chunk": full_answer})

                # 🔹 Cache the answer (skip errors and hallucinations)
                if full_answer and source != "ERROR":
                    await cache_set(answer_key, {
                        "answer": full_answer,
                        "source": source,
                        "tool": tool_name,
                        "tool_result": tool_result,
                    }, settings.CACHE_TTL_RAG_ANSWER)

            # ─── Save to DB ────────────────────────────────────────────────
            if full_answer:
                chat_data = Chat(
                    user=user_email,
                    question=message,
                    answer=full_answer,
                    source=source
                )
                db.add(chat_data)
                await db.commit()
                await db.refresh(chat_data)

                # 🔹 Invalidate chat history cache so next message gets fresh history
                await cache_delete_pattern(f"chat_history:*{hashlib.md5(user_email.encode()).hexdigest()[:8]}*")

            await ws.send_json({
                "type": "done",
                "message": full_answer,
                "source": source,
                "tool": tool_name,
                "tool_result": tool_result
            })

    except Exception as e:
        print(f"WS Error: {e}")
        import traceback
        traceback.print_exc()
        await ws.close()