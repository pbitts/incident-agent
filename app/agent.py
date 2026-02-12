from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.config import MODEL_NAME, MODEL_TEMPERATURE, MODEL_MAX_TOKENS
from app.tools import notify, create_ticket, resolve_ticket, persist_event, find_ticket_by_incident
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


def build_chains():
    summarization_model, model = build_models()

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "{summarization_prompt}\n{format_instructions}\nText to parse: {text_to_parser}")
    ]).partial(
        format_instructions=parser.get_format_instructions(),
        summarization_prompt=SUMMARIZATION_PROMPT,
    )

    summarization_chain = prompt_template | summarization_model | parser

    agent = create_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[create_ticket, resolve_ticket, persist_event, find_ticket_by_incident, notify],
    )

    return summarization_chain, agent


def process_payload(payload: dict):
    summarization_chain, agent = build_chains()

    response = agent.invoke({"messages": [HumanMessage(content=f"{payload}")]})


    final_text = response["messages"][-1].content
    print(f"FINAL TEXT: {final_text}")

    output = summarization_chain.invoke({"text_to_parser": final_text})
    print(f"OUTPUT STRUCTURED: {output}")
    return output
