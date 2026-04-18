import logging
from typing import Dict, Any, List, TypedDict, Annotated, Optional
import operator

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage

from rag_engine import run_rag_pipeline
from graph_engine import build_graph, calculate_risk_vectors, compute_final_score, export_cytoscape

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════
# STATE SCHEMA
# ═══════════════════════════════════════════════════
class GraphState(TypedDict):
    # Inputs
    company_number: Optional[str]
    pdf_bytes: Optional[bytes]
    
    # Internal routing state
    routing_decision: str  # "api_path" or "document_path"
    
    # Standardized normalized Data
    raw_nodes: List[Dict[str, Any]]
    raw_edges: List[Dict[str, Any]]
    
    # Analytics
    confidence_score: float
    hitl_flag: bool
    hitl_reason: str
    
    # Output payload
    final_payload: Dict[str, Any]

# ═══════════════════════════════════════════════════
# NODES
# ═══════════════════════════════════════════════════

def input_router_node(state: GraphState) -> GraphState:
    """Decides which extraction pipeline to trigger."""
    logger.info("Routing input request...")
    if state.get("pdf_bytes"):
        return {"routing_decision": "document_path"}
    elif state.get("company_number"):
        return {"routing_decision": "api_path"}
    
    # Fallback to document if both empty for some reason
    return {"routing_decision": "document_path"}


def mcp_api_node(state: GraphState) -> GraphState:
    """
    (Your friend's logic plugs in here via MCP)
    Calls the external MCP server tool 'fetch_uk_api'.
    """
    logger.info(f"Triggering UK Companies House API for {state['company_number']}")
    
    # This is a stub where the LangChain MCP tool will be called.
    # We leave the implementation blank for your friend to plug his logic.
    raw_nodes = []
    raw_edges = []
    
    return {
        "raw_nodes": raw_nodes, 
        "raw_edges": raw_edges,
        "confidence_score": 100.0, # API data is 100% true
        "hitl_flag": False
    }


def rag_extractor_node(state: GraphState) -> GraphState:
    """
    (Our logic)
    Calls our Gemini+FAISS pipeline to extract entities from PDFs.
    """
    logger.info("Triggering RAG Document Extractor...")
    pdf_bytes = state.get("pdf_bytes")
    if not pdf_bytes:
         return {"raw_nodes": [], "raw_edges": [], "confidence_score": 0.0}

    result = run_rag_pipeline(pdf_bytes)
    
    return {
        "raw_nodes": result.get("discovered_nodes", []),
        "raw_edges": result.get("discovered_edges", []),
        "confidence_score": result.get("overall_confidence_score", 0.0),
        "hitl_flag": result.get("offshore_dead_end", False) or (result.get("overall_confidence_score", 100) < 60),
        "hitl_reason": result.get("hitl_reason", "")
    }


def ofac_sanctions_node(state: GraphState) -> GraphState:
    """
    Cross-checks all names in raw_nodes against the OFAC sanctions database.
    (This is the second MCP tool your friend will write).
    """
    logger.info("Ammending nodes with OFAC Sanction metadata...")
    nodes = state.get("raw_nodes", [])
    
    # Dummy logic to be replaced by MCP SQL Query:
    for node in nodes:
        name = node.get("label", "").lower()
        if "putin" in name or "terror" in name:  # simple stub
            node["risk_level"] = "SANCTIONED"
            logger.warning(f"SANCTION FLAG: {node['label']}")
            
    return {"raw_nodes": nodes}


def graph_math_node(state: GraphState) -> GraphState:
    """
    Feeds the clean, normalized data into NetworkX pure math logic.
    """
    logger.info("Processing Graph Topology Risk...")
    
    G = build_graph(state["raw_nodes"], state["raw_edges"])
    G_risk = calculate_risk_vectors(G)
    
    final_score = compute_final_score(G_risk)
    cyto_export = export_cytoscape(G_risk)
    
    final_payload = {
        "investigation_status": "PROCESSING",
        "risk_score": final_score,
        "confidence_score": state.get("confidence_score", 0.0),
        "hitl_flag": state.get("hitl_flag", False),
        "graph_data": cyto_export
    }
    
    return {"final_payload": final_payload}


def human_review_node(state: GraphState) -> GraphState:
    """
    Final node. Enforces the strict rule that we NEVER AUTO-APPROVE.
    If risk > 70, AUTO_REJECT.
    Else, HUMAN_REVIEW.
    """
    logger.info("Enforcing Zero-Trust Human Review Policy...")
    payload = state["final_payload"]
    
    if payload["risk_score"] >= 70.0:
        payload["investigation_status"] = "AUTO_REJECT"
    else:
        payload["investigation_status"] = "HUMAN_REVIEW"
        
    return {"final_payload": payload}

# ═══════════════════════════════════════════════════
# EDGES
# ═══════════════════════════════════════════════════

def route_from_router(state: GraphState) -> str:
    if state["routing_decision"] == "api_path":
        return "mcp_api"
    return "rag_extractor"

# ═══════════════════════════════════════════════════
# BUILD THE GRAPH
# ═══════════════════════════════════════════════════

workflow = StateGraph(GraphState)

workflow.add_node("router", input_router_node)
workflow.add_node("mcp_api", mcp_api_node)
workflow.add_node("rag_extractor", rag_extractor_node)
workflow.add_node("ofac_sanctions", ofac_sanctions_node)
workflow.add_node("graph_math", graph_math_node)
workflow.add_node("human_review", human_review_node)

workflow.add_edge(START, "router")
workflow.add_conditional_edges("router", route_from_router, {"mcp_api": "mcp_api", "rag_extractor": "rag_extractor"})

workflow.add_edge("mcp_api", "ofac_sanctions")
workflow.add_edge("rag_extractor", "ofac_sanctions")
workflow.add_edge("ofac_sanctions", "graph_math")
workflow.add_edge("graph_math", "human_review")
workflow.add_edge("human_review", END)

# Compile into an executable agent application
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
fusion_agent_app = workflow.compile(checkpointer=memory)

import uuid

async def run_investigation(
    mode: str,
    crn: str = None,
    pdf_bytes: bytes = None,
    thread_id: str = None
) -> dict:
    if not thread_id:
        thread_id = str(uuid.uuid4())
        
    initial_state = {
        "company_number": crn,
        "pdf_bytes": pdf_bytes,
        "routing_decision": "api_path" if mode == "api" else "document_path",
        "raw_nodes": [],
        "raw_edges": [],
        "confidence_score": 0.0,
        "hitl_flag": False,
        "hitl_reason": "",
        "final_payload": {
            # Basic defaults
            "investigation_status": "PROCESSING",
            "risk_score": 0.0,
            "confidence_score": 0.0,
            "hitl_flag": False,
            "graph_data": {"elements": []}
        }
    }
    
    config = {"configurable": {"thread_id": thread_id}}
    state = await fusion_agent_app.ainvoke(initial_state, config=config)
    
    payload = state.get("final_payload", {})
    payload["thread_id"] = thread_id
    return payload

async def resume_investigation(thread_id: str, pdf_bytes: bytes) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    
    state = await fusion_agent_app.ainvoke({"pdf_bytes": pdf_bytes}, config=config)
    
    payload = state.get("final_payload", {})
    payload["thread_id"] = thread_id
    return payload
