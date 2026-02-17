import time
from fastmcp import FastMCP
from pydantic import BaseModel



def register_notification_tools(mcp: FastMCP):

    @mcp.tool()
    def notify(channel: str, message: str) -> str:
        """
        Sends a notification message to a given channel.

        :param channel: Notification platform.
        :param message: Notification message.
        :return: NotificationResult
        """
        time.sleep(1)
        print(f"Sent {channel}:{message}!")
        return "Notificação enviada!"