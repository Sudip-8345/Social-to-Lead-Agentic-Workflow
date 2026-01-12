from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage
from tools import intent_classifier, lead_capture_agent, generic_responder
from agents import AgentState, route_intent
from rag_engine import rag_responder

workflow = StateGraph(AgentState)
workflow.add_node('intent_clf', intent_classifier)
workflow.add_node("rag_agent", rag_responder)
workflow.add_node("lead_agent", lead_capture_agent)
workflow.add_node("greeter", generic_responder)

workflow.add_edge(START, 'intent_clf')
workflow.add_conditional_edges('intent_clf', route_intent)
workflow.add_edge('rag_agent', END)
workflow.add_edge('lead_agent', END)
workflow.add_edge('greeter', END)
app = workflow.compile()