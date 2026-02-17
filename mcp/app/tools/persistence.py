
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastmcp import FastMCP
from db import db


def register_persistence_tools(mcp: FastMCP):
    """
    Register persistence-related tools into MCP server.
    """
    @mcp.tool
    def persist_event(event: Dict[str, Any]):
        """
        Persist an incident event or action into MongoDB.

        This tool:
        - Creates a new incident document when receiving a payload.
        - Appends actions to an existing incident.
        - Updates status, ticket_id, and payload fields.
        """
        incident_id = event.get("incident_id")

        if not incident_id:
            return "incident_id is required"

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
            return "documento inserido"

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
        return "documento atualizado"

    @mcp.tool
    def find_ticket_by_incident(incident_id: int):
        """
        Retrieve the ticket_id associated with an incident.
        """
        doc = db.collection.find_one({"incident_id": incident_id})

        if not doc:
            return "Incident not found"

        ticket_id = doc.get("ticket_id")

        if not ticket_id:
            return "No ticket associated with this incident"

        return ticket_id
