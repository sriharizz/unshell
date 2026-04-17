from datetime import date, datetime
from typing import Optional
import networkx as nx


VAGUE_SIC_CODES = {"74990", "99999", "74100", "82990", "70100", "74200"}


def build_graph(nodes: list[dict], edges: list[dict]) -> nx.DiGraph:
    G = nx.DiGraph()
    for node in nodes:
        G.add_node(node["id"], **node)
    seen_edges: dict[tuple, float] = {}
    for edge in edges:
        key = (edge["source"], edge["target"])
        trust = edge.get("trust_score", 0.0)
        if key not in seen_edges or trust > seen_edges[key]:
            seen_edges[key] = trust
            G.add_edge(edge["source"], edge["target"], **edge)
    return G


def detect_cycles(graph: nx.DiGraph) -> list[list[str]]:
    if graph.number_of_nodes() == 0:
        return []
    return list(nx.simple_cycles(graph))


def calculate_degree_centrality(graph: nx.DiGraph) -> dict[str, float]:
    if graph.number_of_nodes() == 0:
        return {}
    return nx.degree_centrality(graph)


def calculate_risk_score(
    nodes: list[dict],
    edges: list[dict],
    graph: nx.DiGraph,
    incorporation_date: Optional[str],
    sic_codes: list[str],
    address: str,
    pscs: list[dict],
    known_shell_addresses: list[str],
    filing_count: int = 0,
) -> tuple[int, list[str], list[str]]:
    score = 0
    fatal_flags: list[str] = []
    cumulative_vectors: list[str] = []

    if incorporation_date:
        try:
            inc = datetime.strptime(incorporation_date, "%Y-%m-%d").date()
            years_old = (date.today() - inc).days / 365.25
            if years_old > 5 and filing_count < 3:
                score += 15
                cumulative_vectors.append("AGED_SHELL")
        except ValueError:
            pass

    if any(s in VAGUE_SIC_CODES for s in sic_codes):
        score += 15
        cumulative_vectors.append("VAGUE_SIC")

    normalized_address = address.lower().strip()
    if any(normalized_address in ka.lower() for ka in known_shell_addresses):
        score += 20
        cumulative_vectors.append("BOILER_ROOM")

    smurf_count = sum(
        1 for p in pscs if 15.0 <= float(p.get("ownership_pct", 0)) <= 24.9
    )
    if smurf_count >= 3:
        score += 25
        cumulative_vectors.append("SMURF_NETWORK")

    cycles = detect_cycles(graph)
    if cycles:
        score += 100
        fatal_flags.append("CIRCULAR_LOOP")

    centrality = calculate_degree_centrality(graph)
    for cent_score in centrality.values():
        if cent_score > 0.15:
            score += 75
            fatal_flags.append("NOMINEE_PUPPET")
            break

    return min(score, 100), fatal_flags, cumulative_vectors


def get_risk_label(score: int) -> str:
    if score <= 29:
        return "LOW_RISK"
    if score <= 64:
        return "MEDIUM_RISK"
    if score <= 94:
        return "HIGH_RISK"
    return "CRITICAL"


def get_action_required(score: int, fatal_flags: list[str], sanctions_hit: bool) -> str:
    if sanctions_hit or score >= 95:
        return "File SAR immediately. Block account opening."
    if score >= 65:
        return "Escalate to senior compliance officer. Do not open account."
    if score >= 30:
        return "Manual review required. Request additional KYB documents."
    return "Auto-approved. Standard onboarding may proceed."
