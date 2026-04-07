"""
Real-world MCP tools.

Every function here is registered on the MCP server and also available
to the agentic router (TOOLS dict in registry.py).

Tools included:
  - get_weather          : current weather for any city (wttr.in, no API key)
  - get_exchange_rate    : live FX rates (Frankfurter ECB feed, no API key)
  - search_wikipedia     : article summary from Wikipedia REST API
  - get_news_headlines   : top headlines (NewsAPI.org — needs NEWS_API_KEY in .env)
  - get_time             : current UTC + local time for a city via worldtimeapi.io
  - ip_lookup            : geo-info for any public IP (ip-api.com, no API key)
  - get_github_repo      : public GitHub repo metadata
  - get_crypto_price     : live crypto price from CoinGecko (no API key)
  - calculate_expression : safe math expression evaluator (no LLM, no external API)
  - unit_convert         : length, weight, temperature conversions
"""

import os
import re
import math
import logging
from datetime import datetime, timezone

import httpx

from app.mcp.instance import mcp

logger = logging.getLogger(__name__)


# ── Shared HTTP client timeout ───────────────────────────────────────────────
TIMEOUT = httpx.Timeout(10.0)


# ── 1. Weather ───────────────────────────────────────────────────────────────

@mcp.tool()
async def get_weather(city: str) -> dict:
    """
    Get current weather conditions for any city.
    Uses wttr.in which is free and requires no API key.

    Args:
        city: City name e.g. "London", "Mumbai", "New York"
    """
    url = f"https://wttr.in/{httpx.URL(city)}?format=j1"
    async with httpx.AsyncClient(timeout=TIMEOUT) as http:
        r = await http.get(f"https://wttr.in/{city}?format=j1")
        r.raise_for_status()
        data = r.json()

    current = data["current_condition"][0]
    area = data["nearest_area"][0]
    area_name = area["areaName"][0]["value"]
    country = area["country"][0]["value"]

    return {
        "location": f"{area_name}, {country}",
        "temperature_c": int(current["temp_C"]),
        "temperature_f": int(current["temp_F"]),
        "feels_like_c": int(current["FeelsLikeC"]),
        "humidity_pct": int(current["humidity"]),
        "wind_kmph": int(current["windspeedKmph"]),
        "wind_direction": current["winddir16Point"],
        "visibility_km": int(current["visibility"]),
        "uv_index": int(current["uvIndex"]),
        "description": current["weatherDesc"][0]["value"],
        "observation_time": current["observation_time"],
    }


# ── 2. Exchange Rates ────────────────────────────────────────────────────────

@mcp.tool()
async def get_exchange_rate(base: str = "USD", target: str = "INR") -> dict:
    """
    Get live foreign exchange rates from the European Central Bank feed.
    No API key required.

    Args:
        base:   Base currency code  (e.g. "USD", "EUR", "GBP")
        target: Target currency code (e.g. "INR", "JPY", "AED")
    """
    base = base.upper()
    target = target.upper()

    async with httpx.AsyncClient(timeout=TIMEOUT) as http:
        r = await http.get(f"https://api.frankfurter.app/latest?from={base}&to={target}")
        r.raise_for_status()
        data = r.json()

    rate = data["rates"].get(target)
    if rate is None:
        return {"error": f"Currency '{target}' not supported."}

    return {
        "base": base,
        "target": target,
        "rate": rate,
        "date": data["date"],
        "note": f"1 {base} = {rate} {target}",
    }


# ── 3. Wikipedia ─────────────────────────────────────────────────────────────

@mcp.tool()
async def search_wikipedia(query: str) -> dict:
    """
    Get a concise Wikipedia summary for any topic.
    Uses the public Wikipedia REST API — no API key required.

    Args:
        query: Search term, e.g. "Turing machine", "Elon Musk", "Python programming language"
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as http:
        # Step 1: search for the best matching page title
        search_r = await http.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": 1,
            },
        )
        search_r.raise_for_status()
        results = search_r.json()["query"]["search"]

        if not results:
            return {"error": f"No Wikipedia article found for '{query}'."}

        title = results[0]["pageid"]

        # Step 2: fetch the summary
        summary_r = await http.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{results[0]['title'].replace(' ', '_')}",
        )
        summary_r.raise_for_status()
        s = summary_r.json()

    return {
        "title": s.get("title"),
        "summary": s.get("extract", "No summary available."),
        "url": s.get("content_urls", {}).get("desktop", {}).get("page", ""),
        "thumbnail": s.get("thumbnail", {}).get("source", None),
    }


# ── 4. News Headlines ────────────────────────────────────────────────────────

@mcp.tool()
async def get_news_headlines(topic: str = "technology", country: str = "us", count: int = 5) -> dict:
    """
    Fetch top news headlines for a topic using NewsAPI.org.
    Requires NEWS_API_KEY in environment variables.

    Args:
        topic:   Topic/keyword to search, e.g. "AI", "cricket", "finance"
        country: 2-letter country code for top headlines (default "us")
        count:   Number of results (1–10, default 5)
    """
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        return {
            "error": "NEWS_API_KEY not set. Add it to your .env file. Get a free key at newsapi.org."
        }

    count = max(1, min(10, count))

    async with httpx.AsyncClient(timeout=TIMEOUT) as http:
        r = await http.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": topic,
                "pageSize": count,
                "language": "en",
                "sortBy": "publishedAt",
                "apiKey": api_key,
            },
        )
        r.raise_for_status()
        data = r.json()

    articles = data.get("articles", [])
    return {
        "topic": topic,
        "total_results": data.get("totalResults", 0),
        "headlines": [
            {
                "title": a["title"],
                "source": a["source"]["name"],
                "published_at": a["publishedAt"],
                "url": a["url"],
                "description": a.get("description", ""),
            }
            for a in articles
        ],
    }


# ── 5. World Time ────────────────────────────────────────────────────────────

@mcp.tool()
async def get_time(timezone_area: str = "UTC") -> dict:
    """
    Get the current date and time for a timezone area.
    Uses worldtimeapi.io — no API key required.

    Args:
        timezone_area: IANA timezone string e.g. "Asia/Kolkata", "America/New_York", "UTC"
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as http:
        r = await http.get(f"http://worldtimeapi.org/api/timezone/{timezone_area}")
        if r.status_code == 404:
            return {"error": f"Unknown timezone '{timezone_area}'. Use IANA format e.g. 'Asia/Kolkata'."}
        r.raise_for_status()
        data = r.json()

    return {
        "timezone": data["timezone"],
        "datetime": data["datetime"],
        "utc_offset": data["utc_offset"],
        "day_of_week": data["day_of_week"],
        "day_of_year": data["day_of_year"],
        "week_number": data["week_number"],
        "dst": data["dst"],
    }


# ── 6. IP Lookup ─────────────────────────────────────────────────────────────

@mcp.tool()
async def ip_lookup(ip: str) -> dict:
    """
    Get geographic and network information for a public IP address.
    Uses ip-api.com — free tier, no API key required.

    Args:
        ip: Public IPv4 or IPv6 address, e.g. "8.8.8.8"
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as http:
        r = await http.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,message,country,regionName,city,zip,lat,lon,timezone,isp,org,as,query"},
        )
        r.raise_for_status()
        data = r.json()

    if data.get("status") == "fail":
        return {"error": data.get("message", "Lookup failed.")}

    return {
        "ip": data["query"],
        "country": data["country"],
        "region": data["regionName"],
        "city": data["city"],
        "zip": data["zip"],
        "latitude": data["lat"],
        "longitude": data["lon"],
        "timezone": data["timezone"],
        "isp": data["isp"],
        "organization": data["org"],
        "as_number": data["as"],
    }


# ── 7. GitHub Repo Info ──────────────────────────────────────────────────────

@mcp.tool()
async def get_github_repo(owner: str, repo: str) -> dict:
    """
    Fetch public metadata for any GitHub repository.
    No API key required for public repos (60 req/hr unauthenticated).

    Args:
        owner: GitHub username or organisation, e.g. "openai"
        repo:  Repository name, e.g. "whisper"
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as http:
        r = await http.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers={"Accept": "application/vnd.github+json"},
        )
        if r.status_code == 404:
            return {"error": f"Repository '{owner}/{repo}' not found."}
        r.raise_for_status()
        d = r.json()

    return {
        "full_name": d["full_name"],
        "description": d.get("description"),
        "language": d.get("language"),
        "stars": d["stargazers_count"],
        "forks": d["forks_count"],
        "open_issues": d["open_issues_count"],
        "watchers": d["watchers_count"],
        "license": (d.get("license") or {}).get("name"),
        "topics": d.get("topics", []),
        "created_at": d["created_at"],
        "updated_at": d["updated_at"],
        "default_branch": d["default_branch"],
        "url": d["html_url"],
        "homepage": d.get("homepage"),
    }


# ── 8. Crypto Price ──────────────────────────────────────────────────────────

@mcp.tool()
async def get_crypto_price(coin_id: str = "bitcoin", vs_currency: str = "usd") -> dict:
    """
    Get the live price and 24-hour stats for a cryptocurrency from CoinGecko.
    No API key required (free public tier).

    Args:
        coin_id:     CoinGecko ID e.g. "bitcoin", "ethereum", "solana"
        vs_currency: Quote currency e.g. "usd", "inr", "eur"
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as http:
        r = await http.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": coin_id,
                "vs_currencies": vs_currency,
                "include_24hr_change": "true",
                "include_24hr_vol": "true",
                "include_market_cap": "true",
            },
        )
        if r.status_code == 404 or coin_id not in r.json():
            return {"error": f"Coin '{coin_id}' not found on CoinGecko."}
        r.raise_for_status()
        data = r.json()[coin_id]

    return {
        "coin": coin_id,
        "currency": vs_currency.upper(),
        "price": data[vs_currency],
        "market_cap": data.get(f"{vs_currency}_market_cap"),
        "volume_24h": data.get(f"{vs_currency}_24h_vol"),
        "change_24h_pct": round(data.get(f"{vs_currency}_24h_change", 0), 2),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


# ── 9. Safe Expression Calculator ───────────────────────────────────────────

# Whitelist of safe names for eval
_SAFE_NAMES = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
_SAFE_NAMES.update({"abs": abs, "round": round, "min": min, "max": max, "sum": sum})

@mcp.tool()
async def calculate_expression(expression: str) -> dict:
    """
    Safely evaluate a mathematical expression without calling an external API.
    Supports standard operators, parentheses, and math functions (sin, cos, log, sqrt, etc.).

    Args:
        expression: Math expression string e.g. "sqrt(144)", "18% of 50000", "log(1000, 10)"
    """
    # Handle "X% of Y" shorthand
    expr = re.sub(
        r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)",
        r"(\1/100)*\2",
        expression,
        flags=re.IGNORECASE,
    )

    # Strip any characters that are not math-safe
    safe_expr = re.sub(r"[^0-9+\-*/().,%^ a-zA-Z_]", "", expr)

    try:
        result = eval(safe_expr, {"__builtins__": {}}, _SAFE_NAMES)  # noqa: S307
        return {
            "expression": expression,
            "result": round(float(result), 10),
            "formatted": f"{result:,}" if isinstance(result, int) else f"{result:.4f}",
        }
    except Exception as e:
        return {"error": f"Could not evaluate '{expression}': {e}"}


# ── 10. Unit Converter ───────────────────────────────────────────────────────

_CONVERSIONS = {
    # length → meters
    "km": 1000, "m": 1, "cm": 0.01, "mm": 0.001,
    "mile": 1609.344, "yard": 0.9144, "foot": 0.3048, "inch": 0.0254,
    # weight → grams
    "kg": 1000, "g": 1, "mg": 0.001, "lb": 453.592, "oz": 28.3495,
    # volume → litres
    "l": 1, "ml": 0.001, "gallon": 3.78541, "pint": 0.473176, "cup": 0.24,
}

_DIMENSION_GROUPS = [
    {"km", "m", "cm", "mm", "mile", "yard", "foot", "inch"},
    {"kg", "g", "mg", "lb", "oz"},
    {"l", "ml", "gallon", "pint", "cup"},
]


@mcp.tool()
async def unit_convert(value: float, from_unit: str, to_unit: str) -> dict:
    """
    Convert between common units of length, weight, volume, or temperature.
    No external API required.

    Args:
        value:     Numeric value to convert
        from_unit: Source unit (e.g. "km", "kg", "celsius", "fahrenheit")
        to_unit:   Target unit
    """
    fu = from_unit.lower().rstrip("s")   # normalise plural
    tu = to_unit.lower().rstrip("s")

    # Temperature is special-cased
    temp_map = {
        ("celsius", "fahrenheit"): lambda v: (v * 9/5) + 32,
        ("fahrenheit", "celsius"): lambda v: (v - 32) * 5/9,
        ("celsius", "kelvin"):     lambda v: v + 273.15,
        ("kelvin", "celsius"):     lambda v: v - 273.15,
        ("fahrenheit", "kelvin"):  lambda v: (v - 32) * 5/9 + 273.15,
        ("kelvin", "fahrenheit"):  lambda v: (v - 273.15) * 9/5 + 32,
    }
    if (fu, tu) in temp_map:
        result = temp_map[(fu, tu)](value)
        return {
            "input": f"{value} {from_unit}",
            "result": round(result, 4),
            "output": f"{round(result, 4)} {to_unit}",
        }

    # Generic SI conversion via base unit
    if fu not in _CONVERSIONS or tu not in _CONVERSIONS:
        return {"error": f"Unknown unit(s): '{from_unit}' or '{to_unit}'."}

    # Check same dimension group
    same_dim = any(fu in g and tu in g for g in _DIMENSION_GROUPS)
    if not same_dim:
        return {"error": f"Cannot convert '{from_unit}' to '{to_unit}' — different dimensions."}

    base_value = value * _CONVERSIONS[fu]
    result = base_value / _CONVERSIONS[tu]

    return {
        "input": f"{value} {from_unit}",
        "result": round(result, 6),
        "output": f"{round(result, 6)} {to_unit}",
    }
