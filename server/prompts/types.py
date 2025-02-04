from typing import TypedDict, List, Dict, TypeAlias


class NodeContent(TypedDict):
    role: str
    content: str


NodeMessage: TypeAlias = Dict[str, List[NodeContent]]
