from typing import TypedDict, List, Dict, Any, Annotated, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "List of messages exchanged so far", add_messages]
    intents: str
    user_info: Dict[str, Any]
    lead_captured: bool

def route_intent(state: AgentState) -> Literal["rag_agent", "lead_agent", "greeter"]:
    intent = state["intents"].upper()
    if intent == "LEAD":
        return "lead_agent"
    elif intent == "INQUIRY":
        return "rag_agent"
    else:
        return "greeter"