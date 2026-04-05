import json
from app.agent.tool_registry import TOOLS
from app.agent.prompt import SYSTEM_PROMPT
from app.llm.grok import call_grok_llm   # tu already bana chuka hoga

def run_agent(question: str):

    prompt = SYSTEM_PROMPT + f"\nUser: {question}"

    response = call_grok_llm(prompt)

    # 🔥 Try parsing tool call
    try:
        data = json.loads(response)

        tool_name = data.get("tool")
        tool_input = data.get("input", {})

        if tool_name in TOOLS:
            result = TOOLS[tool_name](**tool_input)

            return f"Tool Result: {result}"

    except Exception as e:
        print("❌ Tool parsing failed:", e)
        print("LLM Response:", response)

    # normal answer
    return response