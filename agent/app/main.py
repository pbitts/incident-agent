import logging
from contextlib import asynccontextmanager

from app.observability import configure_langsmith
from fastapi import Depends, FastAPI, Request, HTTPException

from app.agent import AgentService
from app.health import run_startup_checks, health_state

logging.basicConfig(
    format='%(asctime)s\t[%(name)s]\t[%(levelname)s]\t%message)s',
    datefmt="%Y-%m-%d %H:%M:%S%z",
    level=logging.INFO,
    encoding='utf-8'
    )

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info('Configuring Langsmith Tracing...')
    configure_langsmith()

    logger.info('Running Startup Checks...')
    await run_startup_checks()

    logger.info('Initializing Agent Service...')
    agent_service = AgentService()
    await agent_service.initialize()

    app.state.agent_service = agent_service

    yield

def get_agent_service(request: Request) -> AgentService:
    service = getattr(request.app.state, "agent_service", None)
    if not service:
        raise RuntimeError("AgentService not initialized")
    return service

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
async def webhook(payload: dict, service: AgentService = Depends(get_agent_service)):
    logger.info(f'Payload received: {payload}')
    return await service.process(payload)
"""
{"monitoring_platform":"zabbix",
"incident_id":"1",
"trigger":"cpu-load",
"severity":"medium",
"status":"PROBLEM"
}
"""
