from typing import Optional, TypedDict


class InvestigationState(TypedDict):
    mode: str
    target_identifier: str
    raw_pdf_bytes: Optional[bytes]

    discovered_nodes: list
    discovered_edges: list
    networkx_graph: Optional[object]

    incorporation_date: Optional[str]
    sic_codes: list
    registered_address: str
    pscs: list
    known_shell_addresses: list
    filing_count: int

    current_risk_score: int
    fatal_flags: list
    cumulative_vectors: list

    status: str
    thread_id: str
    offshore_dead_end: bool
    resolved_ubo: str

    sanctions_hit: bool
    sanctions_detail: str

    final_payload: Optional[dict]
