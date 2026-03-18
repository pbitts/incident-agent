import json
import asyncio
import logging
from typing import Optional

import httpx
from pydantic import BaseModel, Field
from pymongo import MongoClient
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.messages import HumanMessage
from langchain_core.messages import RemoveMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.types import Command
from langgraph.checkpoint.mongodb import MongoDBSaver

from app.exceptions import PendingApprovalException
from app.config import settings
from app.prompts import SYSTEM_PROMPT, SUMMARIZATION_PROMPT

logger = logging.getLogger(__name__)


# ============================================================
# Output Schema
# ============================================================

class EventResponse(BaseModel):
    event_type: str = Field(...)
    ticket_id: str = Field(...)
    comment: str = Field(...)


parser = PydanticOutputParser(pydantic_object=EventResponse)


# ============================================================
# Agent Service
# ============================================================

class AgentService:
    def __init__(self):
        self.agent = None
        self.summarization_chain = None
        self.mcp_client: Optional[MultiServerMCPClient] = None

    async def initialize(self) -> None:
        logger.info("Initializing AgentService")

        # -------- Models
        agent_model = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model=settings.MODEL_NAME,
            temperature=settings.MODEL_TEMPERATURE,
            max_tokens=settings.MODEL_MAX_TOKENS,
        )

        summarization_model = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model=settings.MODEL_NAME,
            temperature=0,
            max_tokens=512,
        )

        # -------- MCP
        logger.info("Getting tools from MCP...")

        self.mcp_client = MultiServerMCPClient(
            {
                "incident-management-mcp": {
                    "url": f"{settings.MCP_BASE_URL.rstrip('/')}/mcp",
                    "transport": "http",
                }
            }
        )

        tools = await self.mcp_client.get_tools()

        checkpointer = MongoDBSaver( 
            MongoClient(settings.MONGODB_CHECKPOINTER)
        )
        
        self.agent = create_agent(
            model=agent_model,
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            checkpointer=checkpointer,
            middleware=[
                HumanInTheLoopMiddleware(
                    interrupt_on={
                        "run_automation_script": {
                            "allowed_decisions" : ["approve", "reject"],
                        }
                    }
                )
            ]
        )

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "{summarization_prompt}\n"
                "{format_instructions}\n"
                "Text:\n{text}"
            )
        ]).partial(
            summarization_prompt=SUMMARIZATION_PROMPT,
            format_instructions=parser.get_format_instructions(),
        )

        self.summarization_chain = prompt | summarization_model | parser

        logger.info("AgentService initialized successfully")

    async def _summarize_if_needed(self, thread_id: str, threshold: int = 10) -> None:
        """Summarizes old messages if history exceeds `threshold` messages."""
        config = {"configurable": {"thread_id": thread_id}}
        state = await self.agent.aget_state(config)
        messages = state.values.get("messages", [])

        if len(messages) <= threshold:
            return

        # Old messages (all except the last 4)
        messages_to_summarize = messages[:-4]
        recent_messages = messages[-4:]

        summary_prompt = (
            "Concisely summarize the messages below, preserving "
            "important facts, actions taken, and decisions made:\n\n"
            + "\n".join(f"{m.type}: {m.content}" for m in messages_to_summarize)
        )

        summary = await self.summarization_chain.ainvoke({"text": summary_prompt})

        # Remove old messages and inject the summary
        deletes = [RemoveMessage(id=m.id) for m in messages_to_summarize]
        summary_message = SystemMessage(
            content=f"[Previous history summary]: {summary}",
        )

        await self.agent.aupdate_state(
            config,
            {"messages": deletes + [summary_message] + recent_messages},
        )

        logger.info(
            f"[{thread_id}] History summarized: {len(messages_to_summarize)} messages → 1 summary"
        )

    async def process(self, payload: dict) -> EventResponse:
        if not self.agent:
            raise RuntimeError("AgentService not initialized")

        try:
            payload_str = json.dumps(payload, ensure_ascii=False)

            thread_id = payload.get("incident_id", "default-thread")
            
            await self._summarize_if_needed(thread_id, threshold=10)

            config = {"configurable": {"thread_id": thread_id}}
            print(f"Thread id: {thread_id}")

            response = await asyncio.wait_for(
                self.agent.ainvoke(
                    {"messages": [HumanMessage(content=payload_str)]},
                    config=config
                ),
                timeout=settings.AGENT_TIMEOUT,
            )

            # HITL Interrupt -> Send Webhook
            if "__interrupt__" in response:
                interrupts = response["__interrupt__"]
                pending_actions = []

                for interrupt in interrupts:
                    interrupt_value = interrupt.value
                    if "action_requests" in interrupt_value:
                        for action in interrupt_value["action_requests"]:
                            pending_actions.append({
                                "name": action.get("name"),
                                "args": action.get("args"),
                            })

                # Notify external Webhook
                await self._notify_webhook(thread_id, pending_actions)
                pending_approval_msg = f'[PENDING APPROVAL] Thread id: {thread_id}, Pending Actions: {pending_actions}'
                logger.info(pending_approval_msg)
                return pending_approval_msg
            
            final_text = response["messages"][-1].content

            structured = await asyncio.wait_for(
                self.summarization_chain.ainvoke(
                    {"text": final_text}
                ),
                timeout=settings.SUMMARY_TIMEOUT,
            )

            return structured

        except asyncio.TimeoutError:
            logger.error("Agent timeout")
            raise RuntimeError("Agent timeout")

        except Exception as e:
            logger.exception(f"Processing error: {str(e)}")
            raise RuntimeError("Processing error")
    
    async def _notify_webhook(self, thread_id: str, pending_actions: list) -> None:
        payload = {
            "thread_id": thread_id,
            "status": "pending_approval",
            "pending_actions": pending_actions,
            "approve_url": f"{settings.API_BASE_URL}/hitl/{thread_id}/decision",
        }
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    settings.HITL_WEBHOOK_URL,
                    json=payload,
                    timeout=5.0,
                )
            logger.info(f"Webhook HITL notified for thread {thread_id}")
        except Exception as e:
            logger.warning(f"Failed to notify webhook HITL: {e}")

    async def resume(self, thread_id: str, decision: str) -> EventResponse:
        """Resume agent after HITL decision (approve/reject)."""
        if not self.agent:
            raise RuntimeError("AgentService not initialized")

        config = {"configurable": {"thread_id": thread_id}}

        response = await asyncio.wait_for(
            self.agent.ainvoke(
                Command(resume={"decisions": [{"type": decision}]}),
                config=config,
            ),
            timeout=settings.AGENT_TIMEOUT,
        )

        final_text = response["messages"][-1].content
        return await asyncio.wait_for(
            self.summarization_chain.ainvoke({"text": final_text}),
            timeout=settings.SUMMARY_TIMEOUT,
        )