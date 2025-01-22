from pydantic import BaseModel
from typing import List, Dict, Optional, Any


class Message(BaseModel):
    role: str
    content: str


class FlowNodeConfig(BaseModel):
    role_messages: Optional[List[Message]]
    task_messages: Optional[List[Message]]
    functions: Optional[List[Dict[str, Any]]]


class FlowConfig(BaseModel):
    initial_node: str
    nodes: Dict[str, FlowNodeConfig]


class BotConfig(BaseModel):
    type: str
    name: str
    system_messages: Optional[List[Message]]
    flow_config: Optional[FlowConfig]
