
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastmcp import FastMCP
from db import db


def register_persistence_tools(mcp: FastMCP):
    """
    Register persistence-related tools into MCP server.
    """
    @mcp.tool
    def persist_event(
            incident_id: int,
            status: str,
            ticket_id: int,
            zabbix_payload: dict = {},
            actions : dict = {}
        ):
        """
        Persist an incident event or action into MongoDB.

        This tool:
        - Creates a new incident document when receiving a payload.
        - Appends actions to an existing incident.
        - Updates status, ticket_id, and payload fields.

        Args:
            incident_id: Unique incident identifier
            status: Current incident status (PROBLEM, RESOLVED, etc)
            ticket_id: Optional ticket ID to link to the incident
            zabbix_payload: Optional dictionary with Zabbix monitoring data
            actions: Optional dictionary representing an action to append to the actions array
        """
        now = datetime.now(timezone.utc).isoformat()

        try:
            existing = db.collection.find_one({"incident_id": incident_id})

            if not existing:
                # Create new document
                doc = {
                    "incident_id": incident_id,
                    "zabbix_payload": zabbix_payload or {},
                    "status": status,
                    "created_date": now,
                    "updated_date": now,
                    "ticket_id": ticket_id,
                    "actions": [actions] if actions else [],
                }
                db.collection.insert_one(doc)
                return f"Incident {incident_id} created with status {status}"

            # Update existing document
            update_fields = {"updated_date": now}

            if status:
                update_fields["status"] = status

            if ticket_id:
                update_fields["ticket_id"] = ticket_id

            if zabbix_payload:
                update_fields["zabbix_payload"] = zabbix_payload

            # Add action if provided
            if actions:
                db.collection.update_one(
                    {"incident_id": incident_id},
                    {
                        "$set": update_fields,
                        "$push": {"actions": actions}
                    }
                )
                return f"Incident {incident_id} updated. Action added to history."
            else:
                # Just update fields without adding actions
                db.collection.update_one(
                    {"incident_id": incident_id},
                    {"$set": update_fields}
                )
                return f"Incident {incident_id} updated with status {status}"

        except Exception as e:
            return f"Database error: {str(e)}"

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
