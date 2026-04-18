import os
import re
import json
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
if os.environ.get("GEMINI_API_KEY"):
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

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

_SYSTEM = """You are a data normalisation engine for an AML compliance system.
You receive raw JSON from the UK Companies House API and must map it to a strict graph schema.

Rules:
- DO NOT hallucinate. ONLY create nodes and edges for entities that explicitly exist in the provided JSON data.
- Each company, PSC, and active officer explicitly found in the JSON becomes a node.
- Each PSC relationship becomes a directed edge (PSC → company, ownership_pct from band midpoint).
- Each officer relationship becomes a directed edge (officer → company, ownership_pct = 0, trust_score = 1.0).
- node id: slugified lowercase name (spaces → underscores, special chars removed).
- risk_level for all nodes: "UNVERIFIED" until graph engine scores them.
- trust_score for API-sourced edges: 1.0 always.
- evidence_snippet: the exact Companies House field/value that proves this relationship.
- source_doc: "Companies House API".
- If ownership_band is a range like "25% to 50%", use midpoint (37.5).
- NEVER guess URLs, IDs, or extra entities not found in the source text.
"""

def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", name.lower()).strip("_")

def normalize_companies_house_data(raw_data: dict) -> tuple[list[dict], list[dict]]:
    primary_model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=_SYSTEM)
    fallback_model = genai.GenerativeModel("gemini-2.5-flash-lite", system_instruction=_SYSTEM)
    
    prompt = f"Normalise this Companies House data into the graph schema:\n\n{json.dumps(raw_data)}"
    config = {
        "response_mime_type": "application/json",
        "response_schema": NormalizedGraph,
        "temperature": 0.0
    }
    
    try:
        response = primary_model.generate_content(prompt, generation_config=config)
    except Exception as e:
        print(f"Gemini 2.5 Flash failed ({e}), falling back to 2.5 Flash Lite...")
        response = fallback_model.generate_content(prompt, generation_config=config)
    
    graph = NormalizedGraph.model_validate_json(response.text)
    
    nodes = [n.model_dump() for n in graph.nodes]
    edges = [e.model_dump() for e in graph.edges]
    return nodes, edges
