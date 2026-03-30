import asyncio
import httpx
from typing import Dict, Any, Tuple

from app.config import settings
from langchain_groq import ChatGroq


health_state: Dict[str, Any] = {
    "mcp": {"ok": False, "message": "Not checked"},
    "groq": {"ok": False, "message": "Not checked"},
}


async def check_mcp() -> Tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(
                f"{settings.MCP_BASE_URL.rstrip('/')}/health"
            )
            return response.status_code == 200, "Connected"
    except Exception as e:
        return False, str(e)


async def check_groq() -> Tuple[bool, str]:
    try:
        client = ChatGroq(model=settings.MODEL_NAME)
        await client.ainvoke("ping")
        return True, "Connected"
    except Exception as e:
        return False, str(e)


async def run_startup_checks():
    results = await asyncio.gather(check_mcp(), check_groq())

    for name, result in zip(["mcp", "groq"], results):
        ok, message = result
        health_state[name] = {"ok": ok, "message": message}
