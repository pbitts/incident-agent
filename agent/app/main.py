import logging
from contextlib import asynccontextmanager
from typing import Literal

from app.observability import configure_langsmith
from fastapi import Depends, FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent import AgentService
from app.health import run_startup_checks, health_state

logging.basicConfig(
    format='%(asctime)s\t[%(name)s]\t[%(levelname)s]\t%(message)s',
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

class DecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]

app = FastAPI(
    title="Incident Agent API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # libera tudo (demo)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """
    Recebe eventos de plataformas de monitoramento (ex: Zabbix).
    Se o agente precisar de aprovação humana, retorna status 202 com os detalhes da ação pendente.

    Exemplo de payload:
    ```json
        {
            "monitoring_platform": "zabbix",
            "incident_id": "1",
            "trigger": "machine is down",
            "severity": "medium",
            "status": "PROBLEM",
            "host": "10.20.30.40"
        }
    ```
    """
    logger.info(f'Payload received: {payload}')
    return await service.process(payload)

@app.post(
    "/hitl/{thread_id}/decision",
    tags=["Human in the Loop"],
    summary="Aprovar ou rejeitar ação pendente do agente",
    )
async def hitl_decision(
    thread_id: str,
    body: DecisionRequest,
    service: AgentService = Depends(get_agent_service),
    ):
    """
    Retoma a execução do agente após intervenção humana.
    - **thread_id**: ID do incidente/thread interrompido (mesmo `incident_id` do webhook)
    - **decision**: `approve` para executar a ação, `reject` para cancelar
    """
    try:
        result = await service.resume(thread_id, body.decision)
        return {"status": "completed", "result": result}
    except Exception as e:
        logger.exception(f"HITL decision error for thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get(
    "/hitl/{thread_id}/status",
    tags=["Human in the Loop"],
    summary="Consultar estado atual de um thread",
    )
async def hitl_status(
    thread_id: str,
    service: AgentService = Depends(get_agent_service),
    ):
    """
    Verifica se o agente está pausado aguardando aprovação.
    Útil para polling ou para exibir detalhes da ação pendente no dashboard.
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = await service.agent.aget_state(config)
    
        is_pending = bool(state.next)

        pending_actions = []
        if is_pending and state.tasks:
            for task in state.tasks:
                if hasattr(task, "interrupts"):
                    for interrupt in task.interrupts:
                        iv = interrupt.value
                        if "action_requests" in iv:
                            for action in iv["action_requests"]:
                                pending_actions.append({
                                    "tool": action.get("name"),
                                    "args": action.get("args"),
                                })

        return {
            "thread_id": thread_id,
            "pending": is_pending,
            "next_steps": list(state.next),
            "pending_actions": pending_actions,
        }

    except Exception as e:
        logger.exception(f"HITL status error for thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))