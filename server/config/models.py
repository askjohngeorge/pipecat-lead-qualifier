from pydantic import BaseModel
from typing import List


class Message(BaseModel):
    role: str
    content: str


class BotConfig(BaseModel):
    type: str
    name: str
    system_messages: List[Message]
