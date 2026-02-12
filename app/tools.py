from datetime import datetime, timezone
from langchain.tools import tool
import random
from tavily import TavilyClient
import time
from typing import Dict, Any

from app import db


@tool('notify', description='send a notification message to a channel')
def notify(channel: str, message: str) -> bool:
    """
    Sends a notification message to a given channel.

    :param channel: Notification platform.
    :param message: Notification message.
    :return: True if message was sent successfully, False otherwise.
    """
    time.sleep(1)
    print(f"Sent {channel}:{message}!")
    return True

@tool('create_ticket', description='Create a ticket for a problem')
def create_ticket(title: str, comment: str, severity: str) -> Dict[str, Any]:
    """
    Creates a support ticket in the ticketing system.

    Args:
        title (str): Short title of the incident.
        comment (str): Detailed description or comment.
        severity (str): Severity level (e.g., low, medium, high, critical).

    Returns:
        Dict[str, Any]: Ticket metadata.
    """
    print(f"[TICKETING] Opening ticket | Title: {title} | Severity: {severity} | Comment: {comment}")
    time.sleep(2)  # Simulate network/API latency

    ticket_id = random.randint(100, 999)  # 3-digit integer ID

    print(f"[TICKETING] Ticket opened successfully | ID: {ticket_id}")

    return {
        "ticket_id": ticket_id,
        "title": title,
        "comment": comment,
        "severity": severity,
        "status": "opened",
    }

@tool('resolve_ticket', description='Resolve a ticket')
def resolve_ticket(ticket_id: int, comment: str) -> Dict[str, Any]:
    """
    Resolves an existing support ticket.

    Args:
        ticket_id (int): The unique identifier of the ticket.
        comment (str): Resolution comment or summary.

    Returns:
        Dict[str, Any]: Resolution metadata.
    """
    print(f"[TICKETING] Resolving ticket | ID: {ticket_id} | Comment: {comment}")
    time.sleep(1)  # Simulate processing delay

    print(f"[TICKETING] Ticket resolved | ID: {ticket_id}")

    return {
        "ticket_id": ticket_id,
        "comment": comment,
        "status": "resolved",
    }

@tool('persist_event', description='Persist info on MongoDB')
def persist_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Persist an incident event or action into MongoDB.

    This tool:
    - Creates a new incident document when receiving a payload.
    - Appends actions to an existing incident.
    - Updates status, ticket_id, and payload fields.
    """
    incident_id = event.get("incident_id")

    if not incident_id:
        return {"error": "incident_id is required", "data": None}

    now = datetime.now(timezone.utc).isoformat()

    existing = db.collection.find_one({"incident_id": incident_id})

    if not existing:
        # Create new document
        doc = {
            "incident_id": incident_id,
            "zabbix_payload": event.get("zabbix_payload"),
            "status": event.get("status"),
            "start_date": now,
            "updated_date": now,
            "ticket_id": event.get("ticket_id"),
            "actions": event.get("actions", []),
        }
        db.collection.insert_one(doc)
        return {"data": doc, "error": None}

    # Update existing document
    update_fields = {"updated_date": now}

    if "zabbix_payload" in event:
        update_fields["zabbix_payload"] = event["zabbix_payload"]

    if "status" in event:
        update_fields["status"] = event["status"]

    if "ticket_id" in event:
        update_fields["ticket_id"] = event["ticket_id"]

    if event.get("actions"):
        db.collection.update_one(
            {"incident_id": incident_id},
            {
                "$set": update_fields,
                "$push": {"actions": {"$each": event["actions"]}},
            },
        )
    else:
        if update_fields:
            db.collection.update_one(
                {"incident_id": incident_id},
                {"$set": update_fields},
            )

    updated = db.collection.find_one({"incident_id": incident_id})
    return {"data": updated, "error": None}

@tool('find_ticket_by_incident', description='Search a incident ticket on MongoDB')
def find_ticket_by_incident(incident_id: int) -> Dict[str, Any]:
    """
    Retrieve the ticket_id associated with an incident.
    """
    doc = db.collection.find_one({"incident_id": incident_id})

    if not doc:
        return {"data": None, "error": "Incident not found"}

    ticket_id = doc.get("ticket_id")

    if not ticket_id:
        return {"data": None, "error": "No ticket associated with this incident"}

    return {"data": {"ticket_id": ticket_id}, "error": None}

@tool('search_recommendations_on_web', description='Search recommendations on web')
def search_recommendations_on_web(query: str) -> Dict[str, Any]:
    """Search the web for recommendations"""
    tavily_client = TavilyClient()
    return tavily_client.search(query)