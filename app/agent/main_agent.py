import json
from app.mcp.tools.registry import TOOLS
from app.rag.graph import rag_graph
from app.services.llm_service import LLMService
from app.agent.prompt import SYSTEM_PROMPT


async def run_agent(user_message: str, chat_history: str = "") -> dict:

    # Step 1 — LLM decides mode
    raw = await LLMService.generate_response(
        prompt=user_message,
        system=SYSTEM_PROMPT
        
    )

    # Step 2 — Parse decision
    try:
        clean = raw.strip().strip("```json").strip("```").strip()
        decision = json.loads(clean)
    except json.JSONDecodeError:
        return {"mode": "llm", "answer": raw, "source": "LLM"}

    mode = decision.get("mode")

    # Step 3 — Execute
    if mode == "tool":
        tool_name = decision.get("tool")
        tool_input = decision.get("input", {})

        if tool_name not in TOOLS:
            return {
                "mode": "error",
                "answer": f"Unknown tool: {tool_name}",
                "source": "ERROR"
            }

        try:
            tool_fn = TOOLS[tool_name]
            result = await tool_fn(**tool_input) if tool_input else await tool_fn()
            return {
                "mode": "tool",
                "tool": tool_name,
                "result": result,
                "answer": json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result),
                "source": f"TOOL:{tool_name}"
            }
        except Exception as e:
            return {
                "mode": "error",
                "answer": f"Tool execution failed: {str(e)}",
                "source": "ERROR"
            }

    elif mode == "rag":
        return {
            "mode": "rag",
            "answer": "",        # ws.py handles streaming
            "source": "RAG"
        }

    elif mode == "llm":
        return {
            "mode": "llm",
            "answer": decision.get("answer", ""),
            "source": "LLM"
        }

    return {"mode": "error", "answer": "Could not determine mode.", "source": "ERROR"}

