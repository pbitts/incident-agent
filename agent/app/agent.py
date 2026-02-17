import asyncio
import os

from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel, Field

from app.config import MODEL_NAME, MODEL_TEMPERATURE, MODEL_MAX_TOKENS
from app.prompts import SYSTEM_PROMPT, SUMMARIZATION_PROMPT


class EventResponse(BaseModel):
    event_type: str = Field(description="Type of the event done such as ticket_created or ticket_resolved")
    ticket_id: str = Field(description="The ticket id created or resolved")
    comment: str = Field(description="The comment added to the ticket")
    thought_process: str = Field(description="The entire process made")


parser = PydanticOutputParser(pydantic_object=EventResponse)


def build_models():
    summarization_model = ChatGroq(
        model=MODEL_NAME,
        temperature=MODEL_TEMPERATURE,
        max_tokens=MODEL_MAX_TOKENS,
    )

    model = ChatGroq(
        model=MODEL_NAME,
        temperature=MODEL_TEMPERATURE,
        max_tokens=MODEL_MAX_TOKENS,
    )

    return summarization_model, model

async def build_mcp_tools():
    mcp_base_url = os.getenv("MCP_BASE_URL")

    if not mcp_base_url:
        raise ValueError("MCP_BASE_URL environment variable not set")

    mcp_client = MultiServerMCPClient(
        {
            "incident-management-mcp" : {
                "url": mcp_base_url,
                "transport": "streamable_http"
            }
        }
    )

    # Automatically fetch all available tools from MCP server
    mcp_tools = await mcp_client.get_tools()
    return mcp_tools

async def build_chains():
    summarization_model, model = build_models()

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "{summarization_prompt}\n{format_instructions}\nText to parse: {text_to_parser}")
    ]).partial(
        format_instructions=parser.get_format_instructions(),
        summarization_prompt=SUMMARIZATION_PROMPT,
    )

    summarization_chain = prompt_template | summarization_model | parser

    mcp_tools = await build_mcp_tools()

    agent = create_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=mcp_tools,
    )

    return summarization_chain, agent


async def process_payload(payload: dict):
    summarization_chain, agent = await build_chains()

    response = await agent.ainvoke({"messages": [HumanMessage(content=f"{payload}")]})


    final_text = response["messages"][-1].content
    print(f"FINAL TEXT: {final_text}")

    output = await summarization_chain.ainvoke({"text_to_parser": final_text})
    print(f"OUTPUT STRUCTURED: {output}")
    return output
