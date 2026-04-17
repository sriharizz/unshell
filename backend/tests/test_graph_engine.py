import networkx as nx
import pytest
from graph.engine import (
    build_graph,
    detect_cycles,
    calculate_degree_centrality,
    calculate_risk_score,
    get_risk_label,
    get_action_required,
)

MONZO_NODES = [
    {"id": "monzo", "label": "Monzo Bank Limited", "type": "company", "jurisdiction": "UK", "risk_level": "UNVERIFIED", "incorporation_date": "2015-01-01", "sic_codes": ["64191"]},
    {"id": "tom_b", "label": "Tom Blomfield", "type": "individual", "jurisdiction": "UK", "risk_level": "UNVERIFIED", "incorporation_date": None, "sic_codes": []},
]
MONZO_EDGES = [
    {"id": "e1", "source": "tom_b", "target": "monzo", "label": "owns", "ownership_pct": 25.0, "trust_score": 1.0, "evidence_snippet": "PSC register", "source_doc": "Companies House API", "source_page": None},
]


def test_build_graph_basic():
    G = build_graph(MONZO_NODES, MONZO_EDGES)
    assert isinstance(G, nx.DiGraph)
    assert G.number_of_nodes() == 2
    assert G.number_of_edges() == 1


def test_build_graph_empty():
    G = build_graph([], [])
    assert G.number_of_nodes() == 0


def test_build_graph_duplicate_edges_keeps_higher_trust():
    edges = [
        {"id": "e1", "source": "a", "target": "b", "ownership_pct": 50, "trust_score": 0.4, "evidence_snippet": "", "label": "owns", "source_doc": "", "source_page": None},
        {"id": "e2", "source": "a", "target": "b", "ownership_pct": 50, "trust_score": 1.0, "evidence_snippet": "", "label": "owns", "source_doc": "", "source_page": None},
    ]
    nodes = [
        {"id": "a", "label": "A", "type": "company", "jurisdiction": "UK", "risk_level": "UNVERIFIED", "incorporation_date": None, "sic_codes": []},
        {"id": "b", "label": "B", "type": "company", "jurisdiction": "UK", "risk_level": "UNVERIFIED", "incorporation_date": None, "sic_codes": []},
    ]
    G = build_graph(nodes, edges)
    assert G["a"]["b"]["trust_score"] == 1.0


def test_detect_cycles_none():
    G = build_graph(MONZO_NODES, MONZO_EDGES)
    assert detect_cycles(G) == []


def test_detect_cycles_found():
    nodes = [
        {"id": "a", "label": "A", "type": "company", "jurisdiction": "UK", "risk_level": "UNVERIFIED", "incorporation_date": None, "sic_codes": []},
        {"id": "b", "label": "B", "type": "company", "jurisdiction": "UK", "risk_level": "UNVERIFIED", "incorporation_date": None, "sic_codes": []},
    ]
    edges = [
        {"id": "e1", "source": "a", "target": "b", "ownership_pct": 50, "trust_score": 1.0, "evidence_snippet": "", "label": "owns", "source_doc": "", "source_page": None},
        {"id": "e2", "source": "b", "target": "a", "ownership_pct": 50, "trust_score": 1.0, "evidence_snippet": "", "label": "owns", "source_doc": "", "source_page": None},
    ]
    G = build_graph(nodes, edges)
    cycles = detect_cycles(G)
    assert len(cycles) > 0


def test_degree_centrality_empty():
    G = build_graph([], [])
    assert calculate_degree_centrality(G) == {}


def test_clean_company_score():
    G = build_graph(MONZO_NODES, MONZO_EDGES)
    score, fatal, cumulative = calculate_risk_score(
        nodes=MONZO_NODES, edges=MONZO_EDGES, graph=G,
        incorporation_date="2015-01-01", sic_codes=["64191"],
        address="Broadwalk House, 5 Appold Street, London",
        pscs=[{"ownership_pct": 25.0}],
        known_shell_addresses=[], filing_count=10,
    )
    assert score < 30
    assert fatal == []


def test_circular_loop_flag():
    nodes = [
        {"id": "a", "label": "A", "type": "company", "jurisdiction": "BVI", "risk_level": "UNVERIFIED", "incorporation_date": None, "sic_codes": []},
        {"id": "b", "label": "B", "type": "company", "jurisdiction": "BVI", "risk_level": "UNVERIFIED", "incorporation_date": None, "sic_codes": []},
    ]
    edges = [
        {"id": "e1", "source": "a", "target": "b", "ownership_pct": 100, "trust_score": 1.0, "evidence_snippet": "", "label": "owns", "source_doc": "", "source_page": None},
        {"id": "e2", "source": "b", "target": "a", "ownership_pct": 100, "trust_score": 1.0, "evidence_snippet": "", "label": "owns", "source_doc": "", "source_page": None},
    ]
    G = build_graph(nodes, edges)
    score, fatal, _ = calculate_risk_score(
        nodes=nodes, edges=edges, graph=G,
        incorporation_date=None, sic_codes=[], address="",
        pscs=[], known_shell_addresses=[], filing_count=0,
    )
    assert "CIRCULAR_LOOP" in fatal
    assert score == 100


def test_smurf_network_flag():
    pscs = [
        {"ownership_pct": 20.0}, {"ownership_pct": 18.0}, {"ownership_pct": 22.0},
    ]
    G = build_graph([], [])
    score, _, cumulative = calculate_risk_score(
        nodes=[], edges=[], graph=G,
        incorporation_date=None, sic_codes=[], address="",
        pscs=pscs, known_shell_addresses=[], filing_count=0,
    )
    assert "SMURF_NETWORK" in cumulative


def test_score_capped_at_100():
    nodes = [
        {"id": "a", "label": "A", "type": "company", "jurisdiction": "BVI", "risk_level": "UNVERIFIED", "incorporation_date": None, "sic_codes": []},
        {"id": "b", "label": "B", "type": "company", "jurisdiction": "BVI", "risk_level": "UNVERIFIED", "incorporation_date": None, "sic_codes": []},
    ]
    edges = [
        {"id": "e1", "source": "a", "target": "b", "ownership_pct": 100, "trust_score": 1.0, "evidence_snippet": "", "label": "owns", "source_doc": "", "source_page": None},
        {"id": "e2", "source": "b", "target": "a", "ownership_pct": 100, "trust_score": 1.0, "evidence_snippet": "", "label": "owns", "source_doc": "", "source_page": None},
    ]
    G = build_graph(nodes, edges)
    pscs = [{"ownership_pct": 20.0}, {"ownership_pct": 18.0}, {"ownership_pct": 22.0}]
    score, _, _ = calculate_risk_score(
        nodes=nodes, edges=edges, graph=G,
        incorporation_date="1980-01-01", sic_codes=["74990"],
        address="27 Old Gloucester Street, London",
        pscs=pscs, known_shell_addresses=["27 old gloucester street, london"],
        filing_count=0,
    )
    assert score == 100


def test_risk_labels():
    assert get_risk_label(10) == "LOW_RISK"
    assert get_risk_label(29) == "LOW_RISK"
    assert get_risk_label(30) == "MEDIUM_RISK"
    assert get_risk_label(64) == "MEDIUM_RISK"
    assert get_risk_label(65) == "HIGH_RISK"
    assert get_risk_label(94) == "HIGH_RISK"
    assert get_risk_label(95) == "CRITICAL"
    assert get_risk_label(100) == "CRITICAL"


def test_action_required_sanctions():
    action = get_action_required(10, [], True)
    assert "SAR" in action


def test_action_required_critical():
    action = get_action_required(100, ["CIRCULAR_LOOP"], False)
    assert "SAR" in action


def test_empty_graph_score():
    G = build_graph([], [])
    score, fatal, cumulative = calculate_risk_score(
        nodes=[], edges=[], graph=G,
        incorporation_date=None, sic_codes=[], address="",
        pscs=[], known_shell_addresses=[], filing_count=0,
    )
    assert score == 0
    assert fatal == []
    assert cumulative == []
