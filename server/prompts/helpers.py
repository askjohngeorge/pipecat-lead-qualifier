from datetime import datetime
import pytz
from .types import NodeMessage


def get_system_prompt(content: str, message_type: str = "role_messages") -> NodeMessage:
    """Return a dictionary with a system prompt."""
    return {
        message_type: [
            {
                "role": "system",
                "content": content,
            }
        ]
    }


def get_task_prompt(content: str) -> NodeMessage:
    """Return a dictionary with a list of task messages."""
    return get_system_prompt(content, "task_messages")


def get_current_date_uk() -> str:
    """Return the current day and date formatted for the UK timezone."""
    current_date = datetime.now(pytz.timezone("Europe/London"))
    return current_date.strftime("%A, %d %B %Y")
