import os
import uuid
import logging
import httpx
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt

from agent.state import InvestigationState
from ai.gemini_extractor import extract_ownership_from_pdf, convert_extraction_to_graph_format
from ai.nvidia_normalizer import normalize_companies_house_data
from graph.engine import (
    build_graph,
    calculate_risk_score,
    detect_cycles,
    calculate_degree_centrality,
    get_risk_label,
    get_action_required,
)

logger = logging.getLogger("fusion.agent")
MCP_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8002")


async def _call_mcp(endpoint: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{MCP_URL}/tools/{endpoint}", json=payload)
        r.raise_for_status()
        return r.json()


async def _get_known_addresses() -> list[str]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{MCP_URL}/tools/known_addresses")
        r.raise_for_status()
        return r.json()


async def input_router_node(state: InvestigationState) -> Command:
    mode = state.get("mode", "")
    if mode == "api":
        return Command(goto="fetch_uk_api_node")
    if mode == "document":
        return Command(goto="extract_pdf_node")
    raise ValueError(f"Invalid mode: {mode}")


async def fetch_uk_api_node(state: InvestigationState) -> dict:
    raw = await _call_mcp("fetch_uk_api", {"crn": state["target_identifier"]})

    if "error" in raw:
        return {"status": "error", "final_payload": {"error": raw["error"]}}

    nodes, edges = normalize_companies_house_data(raw)

    pscs = raw.get("pscs", [])
    officers = raw.get("officers", [])
    known_addresses = await _get_known_addresses()

    resolved_ubo = ""
    for psc in pscs:
        if psc.get("type") == "individual":
            resolved_ubo = psc["name"]
            break
    if not resolved_ubo and officers:
        resolved_ubo = officers[0].get("name", "")

    offshore_dead_end = any(p.get("is_offshore") for p in pscs)

    return {
        "discovered_nodes": nodes,
        "discovered_edges": edges,
        "incorporation_date": raw.get("incorporation_date"),
        "sic_codes": raw.get("sic_codes", []),
        "registered_address": raw.get("registered_address", ""),
        "pscs": pscs,
        "filing_count": raw.get("filing_count", 0),
        "known_shell_addresses": known_addresses,
        "offshore_dead_end": offshore_dead_end,
        "resolved_ubo": resolved_ubo,
    }


async def extract_pdf_node(state: InvestigationState) -> dict:
    pdf_bytes = state.get("raw_pdf_bytes")
    if not pdf_bytes:
        return {}

    extraction = extract_ownership_from_pdf(pdf_bytes)
    new_nodes, new_edges = convert_extraction_to_graph_format(extraction, "uploaded_document")

    existing_nodes = state.get("discovered_nodes", [])
    existing_edges = state.get("discovered_edges", [])

    merged_nodes = {n["id"]: n for n in existing_nodes}
    for n in new_nodes:
        merged_nodes[n["id"]] = n

    merged_edges = existing_edges + new_edges

    resolved_ubo = state.get("resolved_ubo", "")
    for entity in extraction.entities:
        if entity.type == "individual":
            resolved_ubo = entity.name
            break

    return {
        "discovered_nodes": list(merged_nodes.values()),
        "discovered_edges": merged_edges,
        "resolved_ubo": resolved_ubo,
    }


async def calculate_risk_node(state: InvestigationState) -> dict:
    graph = build_graph(state["discovered_nodes"], state["discovered_edges"])

    score, fatal_flags, cumulative_vectors = calculate_risk_score(
        nodes=state["discovered_nodes"],
        edges=state["discovered_edges"],
        graph=graph,
        incorporation_date=state.get("incorporation_date"),
        sic_codes=state.get("sic_codes", []),
        address=state.get("registered_address", ""),
        pscs=state.get("pscs", []),
        known_shell_addresses=state.get("known_shell_addresses", []),
        filing_count=state.get("filing_count", 0),
    )

    return {
        "networkx_graph": graph,
        "current_risk_score": score,
        "fatal_flags": fatal_flags,
        "cumulative_vectors": cumulative_vectors,
    }


async def offshore_router_node(state: InvestigationState) -> Command:
    if state.get("fatal_flags"):
        return Command(goto="sanctions_check_node")
    if state.get("offshore_dead_end"):
        return Command(goto="human_in_the_loop_node")
    return Command(goto="sanctions_check_node")


async def human_in_the_loop_node(state: InvestigationState) -> dict:
    partial_payload = _build_payload(state, status="paused")
    partial_payload["pause_reason"] = (
        "Offshore entity detected with no public beneficial ownership data. "
        "Upload the offshore incorporation document to continue."
    )
    interrupt("Waiting for offshore PDF upload")
    return {"status": "paused", "final_payload": partial_payload}


async def sanctions_check_node(state: InvestigationState) -> dict:
    ubo = state.get("resolved_ubo", "")
    if not ubo:
        return {"sanctions_hit": False, "sanctions_detail": "No UBO identified for sanctions check"}

    result = await _call_mcp("query_ofac", {"name": ubo})

    updates: dict = {
        "sanctions_hit": result.get("match", False),
        "sanctions_detail": result.get("detail", ""),
    }

    if result.get("match"):
        updates["current_risk_score"] = 100
        flags = state.get("fatal_flags", []).copy()
        flags.append("OFAC_MATCH")
        updates["fatal_flags"] = flags

    return updates


async def compile_output_node(state: InvestigationState) -> dict:
    score = state.get("current_risk_score", 0)
    fatal_flags = state.get("fatal_flags", [])
    sanctions_hit = state.get("sanctions_hit", False)

    final_status = "auto_reject" if (score >= 95 or sanctions_hit) else "complete"
    payload = _build_payload(state, status=final_status)

    return {"status": final_status, "final_payload": payload}


def _build_payload(state: InvestigationState, status: str) -> dict:
    score = state.get("current_risk_score", 0)
    fatal_flags = state.get("fatal_flags", [])
    sanctions_hit = state.get("sanctions_hit", False)
    nodes = state.get("discovered_nodes", [])
    edges = state.get("discovered_edges", [])
    graph = state.get("networkx_graph")

    loops = len(detect_cycles(graph)) if graph else 0
    puppets = 1 if "NOMINEE_PUPPET" in fatal_flags else 0
    jurisdictions = len({n.get("jurisdiction", "") for n in nodes if n.get("jurisdiction")})

    return {
        "status": status,
        "thread_id": state.get("thread_id", ""),
        "risk_score": score,
        "risk_label": get_risk_label(score),
        "fatal_flags": fatal_flags,
        "cumulative_vectors": state.get("cumulative_vectors", []),
        "action_required": get_action_required(score, fatal_flags, sanctions_hit),
        "resolved_ubo": state.get("resolved_ubo", ""),
        "sanctions_hit": sanctions_hit,
        "sanctions_detail": state.get("sanctions_detail", ""),
        "graph": {
            "nodes": nodes,
            "edges": [
                {k: v for k, v in e.items() if k != "networkx_graph"} for e in edges
            ],
        },
        "stats": {
            "total_entities": len(nodes),
            "loops_detected": loops,
            "puppets_detected": puppets,
            "jurisdictions": jurisdictions,
            "investigation_depth": max(len(edges), 1),
        },
    }


def _build_graph() -> StateGraph:
    builder = StateGraph(InvestigationState)
    builder.add_node("input_router_node", input_router_node)
    builder.add_node("fetch_uk_api_node", fetch_uk_api_node)
    builder.add_node("extract_pdf_node", extract_pdf_node)
    builder.add_node("calculate_risk_node", calculate_risk_node)
    builder.add_node("offshore_router_node", offshore_router_node)
    builder.add_node("human_in_the_loop_node", human_in_the_loop_node)
    builder.add_node("sanctions_check_node", sanctions_check_node)
    builder.add_node("compile_output_node", compile_output_node)

    builder.add_edge(START, "input_router_node")
    builder.add_edge("fetch_uk_api_node", "calculate_risk_node")
    builder.add_edge("extract_pdf_node", "calculate_risk_node")
    builder.add_edge("calculate_risk_node", "offshore_router_node")
    builder.add_edge("sanctions_check_node", "compile_output_node")
    builder.add_edge("compile_output_node", END)

    return builder.compile(
        checkpointer=MemorySaver(),
        interrupt_before=["human_in_the_loop_node"],
    )


_graph = _build_graph()


async def run_investigation(
    mode: str,
    crn: str | None = None,
    pdf_bytes: bytes | None = None,
    thread_id: str | None = None,
) -> dict:
    tid = thread_id or str(uuid.uuid4())
    initial_state: InvestigationState = {
        "mode": mode,
        "target_identifier": crn or "DOCUMENT_UPLOAD",
        "raw_pdf_bytes": pdf_bytes,
        "discovered_nodes": [],
        "discovered_edges": [],
        "networkx_graph": None,
        "incorporation_date": None,
        "sic_codes": [],
        "registered_address": "",
        "pscs": [],
        "known_shell_addresses": [],
        "filing_count": 0,
        "current_risk_score": 0,
        "fatal_flags": [],
        "cumulative_vectors": [],
        "status": "running",
        "thread_id": tid,
        "offshore_dead_end": False,
        "resolved_ubo": "",
        "sanctions_hit": False,
        "sanctions_detail": "",
        "final_payload": None,
    }
    config = {"configurable": {"thread_id": tid}}
    result = await _graph.ainvoke(initial_state, config=config)
    return result.get("final_payload") or result


async def resume_investigation(thread_id: str, pdf_bytes: bytes) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    resume_state = {
        "raw_pdf_bytes": pdf_bytes,
        "mode": "document",
        "status": "running",
    }
    result = await _graph.ainvoke(resume_state, config=config)
    return result.get("final_payload") or result
