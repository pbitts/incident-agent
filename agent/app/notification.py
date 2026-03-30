import os
import logging
import time
from app.config import settings

logger = logging.getLogger(__name__)



def notify(hitl_id: str):
    if not settings.NOTIFICATION:
        logger.info("Notifications disabled")
        return "Notification not enabled"

    if not settings.NOTIFICATION_WEBHOOK:
        logger.warning("NOTIFICATION enabled but no webhook provided")
        return "Notification was not possible due to missing env vars"

    notification_webhook = settings.NOTIFICATION_WEBHOOK
    
    print(f'Sending notification to resume hitl id "{hitl_id}" to "{notification_webhook}"!')
    time.sleep(1)
    return "Notification to approve HITL sent!"
    
