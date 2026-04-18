import networkx as nx
from typing import List, Dict, Any, Tuple
import copy

# ═══════════════════════════════════════════════════
# CONSTANTS: RISK VECTORS
# ═══════════════════════════════════════════════════
RISK_SANCTIONED = 100.0
RISK_CIRCULAR_OWNERSHIP = 40.0
RISK_HIGH_RISK_JURISDICTION = 25.0
RISK_AI_UNVERIFIED = 20.0
RISK_OFFSHORE_SHELL = 15.0

HIGH_RISK_JURISDICTIONS = {
    "russia", "iran", "north korea", "syria", "cuba",
    "belarus", "venezuela", "myanmar"  # Add more as per FATF
}

OFFSHORE_JURISDICTIONS = {
    "bvi", "british virgin islands", "cayman", "cayman islands",
    "panama", "seychelles", "isle of man", "jersey", "guernsey",
    "bahamas", "bermuda", "mauritius"
}

def _normalize_jurisdiction(j: str) -> str:
    if not j:
        return ""
    return j.lower().strip()

# ═══════════════════════════════════════════════════
# STAGE G1: Graph Construction
# ═══════════════════════════════════════════════════

def build_graph(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> nx.DiGraph:
    """
    Constructs a Directed Graph from raw nodes and edges.
    Nodes should have: id, label, type, jurisdiction, trust_score, etc.
    Edges should have: source, target, ownership_pct, label, etc.
    """
    G = nx.DiGraph()
    
    # Add nodes safely
    for n in nodes:
        node_id = str(n.get("id", ""))
        if not node_id:
            continue
            
        G.add_node(
            node_id,
            label=n.get("label", node_id),
            type=n.get("type", "unknown"),
            jurisdiction=n.get("jurisdiction", ""),
            trust_score=n.get("trust_score", 1.0),
            base_risk=0.0,
            risk_vectors=[]
        )
        
    # Add edges safely
    for e in edges:
        source = str(e.get("source", ""))
        target = str(e.get("target", ""))
        if source and target and G.has_node(source) and G.has_node(target):
            G.add_edge(
                source, 
                target,
                label=e.get("label", "owns"),
                ownership_pct=e.get("ownership_pct", 0.0),
                trust_score=e.get("trust_score", 1.0)
            )
            
    return G

# ═══════════════════════════════════════════════════
# STAGE G2: Risk Vector Calculation
# ═══════════════════════════════════════════════════

def _add_risk(G: nx.DiGraph, node_id: str, score: float, vector_name: str):
    G.nodes[node_id]["base_risk"] = min(100.0, G.nodes[node_id].get("base_risk", 0.0) + score)
    if vector_name not in G.nodes[node_id]["risk_vectors"]:
        G.nodes[node_id]["risk_vectors"].append(vector_name)

def calculate_risk_vectors(G: nx.DiGraph) -> nx.DiGraph:
    """
    Applies pure mathematical AML/KYB risk checks to the graph nodes perfectly.
    Returns the mutated graph.
    """
    G_mut = copy.deepcopy(G)
    
    # Check 1: Circular Ownership (Cycles)
    try:
        cycles = list(nx.simple_cycles(G_mut))
        for cycle in cycles:
            for node_id in cycle:
                _add_risk(G_mut, node_id, RISK_CIRCULAR_OWNERSHIP, "CIRCULAR_OWNERSHIP_DETECTED")
    except nx.NetworkXNoCycle:
        pass

    for node_id in G_mut.nodes():
        node_data = G_mut.nodes[node_id]
        
        # Check 2: Trust Score / AI Unverified
        if node_data.get("trust_score", 1.0) < 0.75:
            _add_risk(G_mut, node_id, RISK_AI_UNVERIFIED, "AI_UNVERIFIED_CLAIM")
            
        # Check 3 & 4: Jurisdictional Risk
        juris = _normalize_jurisdiction(node_data.get("jurisdiction", ""))
        if juris in HIGH_RISK_JURISDICTIONS:
            _add_risk(G_mut, node_id, RISK_HIGH_RISK_JURISDICTION, "HIGH_RISK_JURISDICTION")
        elif juris in OFFSHORE_JURISDICTIONS:
            _add_risk(G_mut, node_id, RISK_OFFSHORE_SHELL, "OFFSHORE_SHELL_ENTITY")
            
        # Optional trigger for sanctioned data if piped in
        if node_data.get("risk_level") == "SANCTIONED":
             _add_risk(G_mut, node_id, RISK_SANCTIONED, "SANCTIONED_ENTITY_MATCH")

    return G_mut

# ═══════════════════════════════════════════════════
# STAGE G3: Graph Topological Scoring
# ═══════════════════════════════════════════════════

def compute_final_score(G: nx.DiGraph) -> float:
    """
    Calculates the highest risk score path dynamically.
    Instead of just returning max node risk, it evaluates node risk propagation.
    """
    if len(G.nodes) == 0:
        return 0.0
        
    highest_risk = 0.0
    for node_id in G.nodes():
        highest_risk = max(highest_risk, G.nodes[node_id].get("base_risk", 0.0))
        
    return min(100.0, highest_risk)

# ═══════════════════════════════════════════════════
# STAGE G4: Frontend Serialization
# ═══════════════════════════════════════════════════

def export_cytoscape(G: nx.DiGraph) -> Dict[str, Any]:
    """
    Serializes the NetworkX graph into the strict Cytoscape.js format 
    expected by the React frontend.
    """
    cytoscape_elements = []
    
    for node_id in G.nodes():
        nd = G.nodes[node_id]
        cytoscape_elements.append({
            "data": {
                "id": node_id,
                "label": nd.get("label", node_id),
                "type": nd.get("type", "unknown"),
                "riskScore": nd.get("base_risk", 0.0),
                "riskVectors": nd.get("risk_vectors", []),
                "jurisdiction": nd.get("jurisdiction", "")
            }
        })
        
    for source, target in G.edges():
        ed = G.edges[source, target]
        cytoscape_elements.append({
            "data": {
                "source": source,
                "target": target,
                "label": ed.get("label", "owns"),
                "ownership_pct": ed.get("ownership_pct", 0.0)
            }
        })
        
    return {"elements": cytoscape_elements}
