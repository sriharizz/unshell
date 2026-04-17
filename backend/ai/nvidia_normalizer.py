import os
import re
from pydantic import BaseModel
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from dotenv import load_dotenv

load_dotenv()


class NormalizedNode(BaseModel):
    id: str
    label: str
    type: str
    jurisdiction: str
    risk_level: str
    incorporation_date: str | None
    sic_codes: list[str]


class NormalizedEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    ownership_pct: float
    trust_score: float
    evidence_snippet: str
    source_doc: str
    source_page: int | None


class NormalizedGraph(BaseModel):
    nodes: list[NormalizedNode]
    edges: list[NormalizedEdge]


_llm = ChatNVIDIA(
    model="meta/llama-3.1-70b-instruct",
    nvidia_api_key=os.environ["NVIDIA_API_KEY"],
    temperature=0,
).with_structured_output(NormalizedGraph)

_SYSTEM = """You are a data normalisation engine for an AML compliance system.
You receive raw JSON from the UK Companies House API and must map it to a strict graph schema.

Rules:
- Each company, PSC, and active officer becomes a node.
- Each PSC relationship becomes a directed edge (PSC → company, ownership_pct from band midpoint).
- Each officer relationship becomes a directed edge (officer → company, ownership_pct = 0, trust_score = 1.0).
- node id: slugified lowercase name (spaces → underscores, special chars removed).
- risk_level for all nodes: "UNVERIFIED" until graph engine scores them.
- trust_score for API-sourced edges: 1.0 always.
- evidence_snippet: the exact Companies House field/value that proves this relationship.
- source_doc: "Companies House API".
- If ownership_band is a range like "25% to 50%", use midpoint (37.5).

Return ONLY the structured JSON — no explanation."""


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", name.lower()).strip("_")


def normalize_companies_house_data(raw_data: dict) -> tuple[list[dict], list[dict]]:
    prompt = f"Normalise this Companies House data into the graph schema:\n\n{raw_data}"
    result: NormalizedGraph = _llm.invoke([
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": prompt},
    ])
    nodes = [n.model_dump() for n in result.nodes]
    edges = [e.model_dump() for e in result.edges]
    return nodes, edges
