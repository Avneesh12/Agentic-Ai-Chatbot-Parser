from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.chat import Chat


async def get_last_5_memory(db: AsyncSession, user: str):

    result = await db.execute(
        select(Chat)
        .where(Chat.user == user)
        .order_by(Chat.created_at.desc())
        .limit(5)
    )

    chats = result.scalars().all()
    chats = list(reversed(chats))

    context = ""
    for chat in chats:
        context += f"User: {chat.question}\nAI: {chat.answer}\n"

    return context