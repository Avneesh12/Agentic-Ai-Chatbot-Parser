from groq import AsyncGroq          # 🔹 use AsyncGroq not Groq
from app.core.config import settings

client = AsyncGroq(api_key=settings.GROQ_API_KEY)  # 🔹 async client


class LLMService:

    @staticmethod
    async def generate_response(
        prompt: str,
        system: str = "You are a helpful AI assistant."
    ) -> str:

        response = await client.chat.completions.create(   # 🔹 await it
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            model=settings.MODEL,
            temperature=0.7,
            max_tokens=1024        # 🔹 250 is too low — answers get cut off
        )

        return response.choices[0].message.content