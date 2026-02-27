import json
import asyncio
import logging
from typing import Optional

from pydantic import BaseModel, Field
from pymongo import MongoClient
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.types import Command
from langgraph.checkpoint.mongodb import MongoDBSaver

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

    async def process(self, payload: dict) -> EventResponse:
        if not self.agent:
            raise RuntimeError("AgentService not initialized")

        try:
            payload_str = json.dumps(payload, ensure_ascii=False)

            thread_id = payload.get("incident_id", "default-thread")
            config = {"configurable": {"thread_id": thread_id}}
            print(f"Thread id: {thread_id}")

            response = await asyncio.wait_for(
                self.agent.ainvoke(
                    {"messages": [HumanMessage(content=payload_str)]},
                    config=config
                ),
                timeout=settings.AGENT_TIMEOUT,
            )

            if "__interrupt__" in response:
                interrupts = response["__interrupt__"]
                print("Interruption: Agent needs approval")
                print(f'Interrupts: {interrupts}')
                for interrupt in interrupts:
                    print(f'interrupt: {interrupt}')
                    interrupt_value = interrupt.value
                    print(f'interrupt_value: {interrupt_value}')
                    if "action_requests" in interrupt_value:
                        for action in interrupt_value["action_requests"]:
                            print(f'action: {action}')
                            print(f"Tool: {action.get("name")}")
                            print(f"Args: {action.get("args")}")

                            response = await asyncio.wait_for(
                                    self.agent.ainvoke(
                                    Command(resume={"decisions": [{"type": "approve"}]}),
                                    config=config
                                ),
                                timeout=settings.AGENT_TIMEOUT,
                            )

                            print('Resuming with approval...')

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
