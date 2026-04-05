import requests
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def call_grok_llm(prompt: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.1-8b-instant",   # 🔥 tera model
        "messages": [
            {"role": "system", "content": "You are an AI agent."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0
    }

    response = requests.post(url, headers=headers, json=payload)

    # Debug
    if response.status_code != 200:
        raise Exception(f"Groq API Error: {response.text}")

    data = response.json()

    # Safe parsing
    if "choices" not in data:
        raise Exception(f"Invalid response: {data}")

    return data["choices"][0]["message"]["content"]