from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.rag.graph import rag_graph
from app.db.deps import get_db
from app.models.chat import Chat

from sqlalchemy import select
from typing import List
from app.agent.main_agent import run_agent
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    user: str | None = None


@router.post("/chat")
async def chat(request: ChatRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):

    # 🔹 Get last 5 chats for memory
    result = await db.execute(
        select(Chat)
        .where(Chat.user == request.user)
        .order_by(Chat.created_at.desc())
        .limit(5)
    )
    chats = list(reversed(result.scalars().all()))
    chat_history = "\n".join([
        f"User: {c.question}\nAI: {c.answer}"
        for c in chats
    ])

    # 🔥 Run agent — handles tool / rag / llm routing
    result = await run_agent(request.message, chat_history)

    # 🔹 Save to DB
    chat_data = Chat(
        user=request.user,
        question=request.message,
        answer=result["answer"],
        source=result["source"]
    )
    db.add(chat_data)
    await db.commit()
    await db.refresh(chat_data)

    return {
        "id": chat_data.id,
        "question": request.message,
        "answer": result["answer"],
        "source": result["source"],
        "tool": result.get("tool"),        # present if tool was called
        "tool_result": result.get("result"), # raw tool data if any
        "created_at": chat_data.created_at
    }
    


@router.get("/chat/history")
async def get_chat_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Chat)
        .where(Chat.user == current_user.email)
        .order_by(Chat.created_at.desc())
    )

    chats = result.scalars().all()

    response = []
    for chat in chats:
        response.append({
            "type": "query",
            "message": chat.question,
            "created_at": chat.created_at
        })
        response.append({
            "type": "ai",
            "message": chat.answer,
            "ai_source": chat.source,  # RAG / LLM
            "created_at": chat.created_at
        })

    return {
        "user": current_user.email,
        "total_messages": len(response),
        "chats": response
    }