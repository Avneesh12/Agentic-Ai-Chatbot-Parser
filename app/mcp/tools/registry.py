"""
Central tool registry.

The agent router imports TOOLS to resolve tool_name → callable.
All entries here must match the tool names used in the system prompt.
"""

from app.mcp.tools.real_world import (
    get_weather,
    get_exchange_rate,
    search_wikipedia,
    get_news_headlines,
    get_time,
    ip_lookup,
    get_github_repo,
    get_crypto_price,
    calculate_expression,
    unit_convert,
)
from app.mcp.tools.health import health_check

TOOLS: dict = {
    # ── System ───────────────────────────────────────
    "health_check":         health_check,

    # ── Real-world tools ─────────────────────────────
    "get_weather":          get_weather,
    "get_exchange_rate":    get_exchange_rate,
    "search_wikipedia":     search_wikipedia,
    "get_news_headlines":   get_news_headlines,
    "get_time":             get_time,
    "ip_lookup":            ip_lookup,
    "get_github_repo":      get_github_repo,
    "get_crypto_price":     get_crypto_price,
    "calculate_expression": calculate_expression,
    "unit_convert":         unit_convert,
}
