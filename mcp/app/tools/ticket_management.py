import time
import random
from typing import Dict, Any
from fastmcp import FastMCP




def register_ticket_management_tools(mcp: FastMCP):
    """
    Register ticket-management-related tools into MCP server.
    """
    @mcp.tool
    def create_ticket(title: str, comment: str, severity: str):
        """
        Creates a support ticket in the ticketing system.

        Args:
            title (str): Short title of the incident.
            comment (str): Detailed description or comment.
            severity (str): Severity level (e.g., low, medium, high, critical).

        Returns:
            -> TicketResult: Ticket metadata.
        """
        print(f"[TICKETING] Opening ticket | Title: {title} | Severity: {severity} | Comment: {comment}")
        time.sleep(2)  # Simulate network/API latency

        ticket_id = random.randint(100, 999)  # 3-digit integer ID

        print(f"[TICKETING] Ticket opened successfully | ID: {ticket_id}")

        return f"[TICKETING] Ticket opened successfully | ID: {ticket_id}"

    @mcp.tool
    def resolve_ticket(ticket_id: int, comment: str ):
        """
        Resolves an existing support ticket.

        Args:
            ticket_id (int): The unique identifier of the ticket.
            comment (str): Resolution comment or summary.

        Returns:
            ResolveResult: Resolution metadata.
        """
        print(f"[TICKETING] Resolving ticket | ID: {ticket_id} | Comment: {comment}")
        time.sleep(1)  # Simulate processing delay

        print(f"[TICKETING] Ticket resolved | ID: {ticket_id}")

        return f"[TICKETING] Ticket resolved | ID: {ticket_id}"