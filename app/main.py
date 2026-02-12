from fastapi import FastAPI
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

from app import db
from app import agent


app = FastAPI()

@app.on_event("startup")
def startup():
    db.init_db()

@app.post("/webhook")
def receive_incident(payload: dict):
    result = agent.process_payload(payload)
    return result


