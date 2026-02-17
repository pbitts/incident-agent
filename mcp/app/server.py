from pathlib import Path
from dotenv import load_dotenv
from fastmcp import FastMCP

from db.db import init_db
from tools.notification import register_notification_tools
from tools.persistence import register_persistence_tools
from tools.ticket_management import register_ticket_management_tools

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

init_db()

# Cria servidor
mcp = FastMCP("incident-management-mcp")

# Registra tools por domínio
register_notification_tools(mcp)
register_persistence_tools(mcp)
register_ticket_management_tools(mcp)


if __name__ == "__main__":
    mcp.run(transport="http", port=9000)