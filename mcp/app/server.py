from pathlib import Path
from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.responses import JSONResponse

from db.db import init_db
from tools.notification import register_notification_tools
from tools.persistence import register_persistence_tools
from tools.ticket_management import register_ticket_management_tools


env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# Initialize database
try:
    init_db()
except Exception as e:
    print(f"[ERROR] Failed to initialize database: {e}")
    import sys
    sys.exit(1)

# Cria servidor
mcp = FastMCP("incident-management-mcp")

# Registra tools por domínio
register_notification_tools(mcp)
register_persistence_tools(mcp)
register_ticket_management_tools(mcp)



@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "healthy", "service": "mcp-server"})

if __name__ == "__main__":
    mcp.run(transport="http", port=9000)