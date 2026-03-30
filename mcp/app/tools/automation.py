import time
from fastmcp import FastMCP
from pydantic import BaseModel



def register_automation_tools(mcp: FastMCP):

    @mcp.tool()
    def run_automation_script(script: str, host: str) -> str:
        """
        Runs an automation script on a specific host.

        :param script: The script name. Can be either (reboot_machine or restart_service).
        :param host: The host that will receive the automation. Can be a name or IP.
        :return: str
        """
        print(f'Running script "{script}" on host "{host}"!')
        time.sleep(3)
        return "Automation executed!"