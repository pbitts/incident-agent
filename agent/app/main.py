import logging
from contextlib import asynccontextmanager

from app.observability import configure_langsmith
from fastapi import FastAPI, Request, HTTPException

from app.agent import AgentService
from app.health import run_startup_checks, health_state

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):

    configure_langsmith()

    await run_startup_checks()

    agent_service = AgentService()
    await agent_service.initialize()

    app.state.agent_service = agent_service

    yield


app = FastAPI(
    title="Incident Agent API",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    if not all(service["ok"] for service in health_state.values()):
        raise HTTPException(status_code=503, detail=health_state)

    return {"status": "ok"}


@app.get("/live")
async def live():
    return {"status": "alive"}


@app.post("/webhook")
async def webhook(request: Request, payload: dict):
    service: AgentService = request.app.state.agent_service
    return await service.process(payload)
