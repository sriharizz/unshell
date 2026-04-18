import os
import uuid
import requests
import networkx as nx
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agent.state import InvestigationState
from ai.gemini_normalizer import normalize_companies_house_data
from ai.gemini_extractor import extract_ownership_from_pdf, convert_extraction_to_graph_format
from graph.engine import build_graph, calculate_risk_score

def fetch_uk_api(crn: str) -> dict:
    url = f"{os.getenv('MCP_SERVER_URL', 'http://localhost:8002')}/tools/fetch_uk_api"
    print(f"\n[INVESTIGATE] Fetching Companies House data for CRN: {crn}\n")
    resp = requests.post(url, json={"crn": crn})
    if resp.status_code == 404:
        raise ValueError(f"Company '{crn}' not found in Companies House. Please check the CRN and try again.")
    resp.raise_for_status()
    return resp.json()

def query_ofac(name: str) -> dict:
    url = f"{os.getenv('MCP_SERVER_URL', 'http://localhost:8002')}/tools/query_ofac"
    resp = requests.post(url, json={"name": name})
    resp.raise_for_status()
    return resp.json()

def get_known_addresses() -> dict:
    url = f"{os.getenv('MCP_SERVER_URL', 'http://localhost:8002')}/tools/known_addresses"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

def input_router_node(state: InvestigationState) -> InvestigationState:
    state["status"] = "in_progress"
    state["thread_id"] = str(uuid.uuid4())
    return state

def fetch_uk_api_node(state: InvestigationState) -> InvestigationState:
    crn = state["target_identifier"]
    
    # Call MCP server
    raw_data = fetch_uk_api(crn)
    
    # Normalize with Llama/Gemma - catch rate limit errors
    try:
        nodes, edges = normalize_companies_house_data(raw_data)
    except Exception as e:
        err_str = str(e).lower()
        if ("429" in err_str or "quota" in err_str or "resource_exhausted" in err_str
                or "rate limit" in err_str or "too many requests" in err_str or "ratelimit" in err_str):
            raise ValueError("AI rate limit reached. Please wait 30–60 seconds and try again.")
        raise
    
    # Update state
    state["discovered_nodes"] = nodes
    state["discovered_edges"] = edges
    state["incorporation_date"] = raw_data.get("incorporation_date", "")
    state["sic_codes"] = raw_data.get("sic_codes", [])
    state["registered_address"] = raw_data.get("registered_address", "")
    state["filing_count"] = raw_data.get("filing_count", 0)
    state["pscs"] = raw_data.get("pscs", [])
    
    offshore_count = sum(1 for psc in state["pscs"] if psc.get("is_offshore", False))
    state["offshore_dead_end"] = offshore_count > 0
    
    # UBO Extraction Logic
    if state["offshore_dead_end"]:
        state["resolved_ubo"] = "UNKNOWN (OFFSHORE)"
    else:
        # 1. Try to find an individual PSC
        for psc in state["pscs"]:
            if not psc.get("is_offshore", False) and psc.get("type", "").lower() in ["individual", "person"]:
                state["resolved_ubo"] = psc["name"]
                break
        else:
            # 2. Try to find any other PSC
            for psc in state["pscs"]:
                if not psc.get("is_offshore", False):
                    state["resolved_ubo"] = psc["name"]
                    break
            else:
                # 3. Fallback to active officers
                if raw_data.get("officers", []):
                    state["resolved_ubo"] = raw_data["officers"][0]["name"]
                else:
                    state["resolved_ubo"] = "UNKNOWN"
            
    return state

def calculate_risk_node(state: InvestigationState) -> InvestigationState:
    shell_data = get_known_addresses()
    state["known_shell_addresses"] = shell_data.get("addresses", [])
    
    graph = build_graph(
        state["discovered_nodes"],
        state["discovered_edges"]
    )
    state["networkx_graph"] = None
    
    risk_result = calculate_risk_score(
        graph=graph,
        incorporation_date=state["incorporation_date"],
        sic_codes=state["sic_codes"],
        registered_address=state["registered_address"],
        known_shell_addresses=state["known_shell_addresses"],
        filing_count=state["filing_count"]
    )
    
    state["current_risk_score"] = risk_result["score"]
    state["fatal_flags"] = risk_result["fatal_flags"]
    state["cumulative_vectors"] = risk_result["cumulative_vectors"]
    
    for node in state["discovered_nodes"]:
        if "tags" not in node:
            node["tags"] = []
        if node["id"] in risk_result.get("loop_nodes", []):
            if "LOOP" not in node["tags"]: node["tags"].append("LOOP")
        if node["id"] in risk_result.get("puppet_nodes", []):
            if "PUPPET" not in node["tags"]: node["tags"].append("PUPPET")
        
        jurisdiction = node.get("jurisdiction", "")
        if jurisdiction and jurisdiction.lower() not in ["england", "wales", "scotland", "northern ireland", "united kingdom"]:
            if "OFFSHORE" not in node["tags"]: node["tags"].append("OFFSHORE")

    return state

def sanctions_check_node(state: InvestigationState) -> InvestigationState:
    ubo_name = state["resolved_ubo"]
    
    ofac_result = query_ofac(ubo_name)
    
    if ofac_result["match"]:
        state["sanctions_hit"] = True
        state["sanctions_detail"] = f"{ofac_result['matched_name']} - {ofac_result['program']}"
        state["current_risk_score"] = 100
        if "OFAC_MATCH" not in state["fatal_flags"]:
            state["fatal_flags"].append("OFAC_MATCH")
            
        for node in state["discovered_nodes"]:
            if node.get("label", "").lower() == ubo_name.lower() or node.get("label", "").lower() == ofac_result['matched_name'].lower():
                if "tags" not in node:
                    node["tags"] = []
                if "OFAC" not in node["tags"]: node["tags"].append("OFAC")
    else:
        state["sanctions_hit"] = False
        state["sanctions_detail"] = ""
    
    return state

def compile_output_node(state: InvestigationState) -> InvestigationState:
    score = state["current_risk_score"]
    
    if score >= 95 or state["sanctions_hit"]:
        status = "auto_reject"
        action_required = "SAR Filing Required" if state["sanctions_hit"] else "Immediate Rejection"
    else:
        status = "complete"
        action_required = "Human Review" if score >= 30 else "Auto-Approve"
    
    if score <= 29:
        risk_label = "LOW_RISK"
    elif score <= 64:
        risk_label = "MEDIUM_RISK"
    elif score <= 94:
        risk_label = "HIGH_RISK"
    else:
        risk_label = "CRITICAL"
    
    graph = build_graph(state["discovered_nodes"], state["discovered_edges"])
    jurisdictions = set(node.get("jurisdiction", "Unknown") for node in state["discovered_nodes"])
    
    # Fix dict representation for Networkx
    try:
        cycles_len = len(list(nx.simple_cycles(graph))) if graph else 0
    except: cycles_len = 0

    # Inject spring_layout positions so React Flow draws a cluster web, not a flat line
    positioned_nodes = list(state["discovered_nodes"])
    try:
        if graph and len(graph.nodes) > 1:
            pos = nx.spring_layout(graph, k=2.5, iterations=80, seed=42)
            scale = 900
            node_id_set = set(graph.nodes)
            for node in positioned_nodes:
                nid = node.get("id")
                if nid and nid in node_id_set:
                    node["position"] = {
                        "x": round(float(pos[nid][0]) * scale, 2),
                        "y": round(float(pos[nid][1]) * scale, 2),
                    }
    except Exception:
        pass  # positions optional — Dagre fallback still works

    final_payload = {
        "status": status,
        "thread_id": state["thread_id"],
        "risk_score": score,
        "risk_label": risk_label,
        "fatal_flags": state["fatal_flags"],
        "cumulative_vectors": state["cumulative_vectors"],
        "action_required": action_required,
        "resolved_ubo": state["resolved_ubo"],
        "sanctions_hit": state["sanctions_hit"],
        "sanctions_detail": state["sanctions_detail"],
        "graph": {
            "nodes": positioned_nodes,
            "edges": state["discovered_edges"]
        },
        "stats": {
            "total_entities": len(state["discovered_nodes"]),
            "loops_detected": cycles_len,
            "puppets_detected": sum(1 for f in state["fatal_flags"] if f == "NOMINEE_PUPPET"),
            "jurisdictions": list(jurisdictions),
            "investigation_depth": 1
        }
    }
    
    state["final_payload"] = final_payload
    state["status"] = status
    
    return state

def build_investigation_graph() -> StateGraph:
    workflow = StateGraph(InvestigationState)
    
    workflow.add_node("input_router", input_router_node)
    workflow.add_node("fetch_uk_api", fetch_uk_api_node)
    workflow.add_node("calculate_risk", calculate_risk_node)
    workflow.add_node("sanctions_check", sanctions_check_node)
    workflow.add_node("compile_output", compile_output_node)
    
    workflow.set_entry_point("input_router")
    workflow.add_edge("input_router", "fetch_uk_api")
    workflow.add_edge("fetch_uk_api", "calculate_risk")
    workflow.add_edge("calculate_risk", "sanctions_check")
    workflow.add_edge("sanctions_check", "compile_output")
    workflow.add_edge("compile_output", END)
    
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    
    return app

def run_investigation(crn: str) -> dict:
    app = build_investigation_graph()
    
    initial_state = {
        "mode": "api",
        "target_identifier": crn,
        "discovered_nodes": [],
        "discovered_edges": [],
        "networkx_graph": None,
        "incorporation_date": "",
        "sic_codes": [],
        "registered_address": "",
        "filing_count": 0,
        "pscs": [],
        "offshore_dead_end": False,
        "resolved_ubo": "",
        "known_shell_addresses": [],
        "current_risk_score": 0,
        "fatal_flags": [],
        "cumulative_vectors": [],
        "sanctions_hit": False,
        "sanctions_detail": "",
        "status": "in_progress",
        "thread_id": "",
        "final_payload": {}
    }
    
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = app.invoke(initial_state, config)
    
    return result["final_payload"]


def run_investigation_document(pdf_bytes: bytes, filename: str = "document.pdf") -> dict:
    """
    Document path: PDF → Gemini extraction → same risk/sanctions pipeline.
    Drop-in point for friend's rag_engine.py logic.
    """
    print(f"\n[DOCUMENT] Extracting ownership from: {filename}\n")

    # ── Step 1: Extract entities/relationships from PDF via Gemini ────────────
    extraction = extract_ownership_from_pdf(pdf_bytes)
    nodes, edges = convert_extraction_to_graph_format(extraction, document_name=filename)

    # ── Step 2: Run shared risk + sanctions pipeline ──────────────────────────
    shell_data = get_known_addresses()
    known_shells = shell_data.get("addresses", [])

    graph = build_graph(nodes, edges)
    risk_result = calculate_risk_score(
        graph=graph,
        incorporation_date="",
        sic_codes=[],
        registered_address="",
        known_shell_addresses=known_shells,
        filing_count=0
    )

    # ── Step 3: Determine UBO from extracted individuals ──────────────────────
    resolved_ubo = "UNKNOWN"
    for entity in extraction.entities:
        if entity.type == "individual":
            resolved_ubo = entity.name
            break

    # ── Step 4: Sanctions check ───────────────────────────────────────────────
    sanctions_hit = False
    sanctions_detail = ""
    fatal_flags = list(risk_result["fatal_flags"])
    if resolved_ubo != "UNKNOWN":
        ofac = query_ofac(resolved_ubo)
        if ofac.get("match"):
            sanctions_hit = True
            sanctions_detail = f"{ofac['matched_name']} - {ofac['program']}"
            fatal_flags.append("OFAC_MATCH")

    score = 100 if sanctions_hit else risk_result["score"]

    if score <= 29:    risk_label = "LOW_RISK"
    elif score <= 64:  risk_label = "MEDIUM_RISK"
    elif score <= 94:  risk_label = "HIGH_RISK"
    else:              risk_label = "CRITICAL"

    status = "auto_reject" if (score >= 95 or sanctions_hit) else "complete"
    action = "SAR Filing Required" if sanctions_hit else ("Human Review" if score >= 30 else "Auto-Approve")

    jurisdictions = list(set(n.get("jurisdiction", "Unknown") for n in nodes))
    try:
        cycles_len = len(list(nx.simple_cycles(graph))) if graph else 0
    except: cycles_len = 0

    return {
        "status": status,
        "thread_id": str(uuid.uuid4()),
        "risk_score": score,
        "risk_label": risk_label,
        "fatal_flags": fatal_flags,
        "cumulative_vectors": risk_result.get("cumulative_vectors", []),
        "action_required": action,
        "resolved_ubo": resolved_ubo,
        "sanctions_hit": sanctions_hit,
        "sanctions_detail": sanctions_detail,
        "document_type": extraction.document_type,
        "extraction_confidence": extraction.extraction_confidence,
        "warnings": extraction.warnings,
        "graph": {"nodes": nodes, "edges": edges},
        "stats": {
            "total_entities": len(nodes),
            "loops_detected": cycles_len,
            "puppets_detected": sum(1 for f in fatal_flags if f == "NOMINEE_PUPPET"),
            "jurisdictions": jurisdictions,
            "investigation_depth": 1
        }
    }
