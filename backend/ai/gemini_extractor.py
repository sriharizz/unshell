import os
import re
from typing import Literal, Optional
import fitz
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])


class ExtractedEntity(BaseModel):
    name: str
    type: Literal["individual", "company", "trust", "foundation"]
    jurisdiction: str
    ownership_pct: float
    role: str
    evidence_snippet: str
    page_num: Optional[int]


class ExtractedRelationship(BaseModel):
    owner: str
    owned: str
    ownership_pct: float
    evidence_snippet: str
    page_num: Optional[int]
    trust_score: float = 0.4


class OwnershipExtraction(BaseModel):
    entities: list[ExtractedEntity]
    relationships: list[ExtractedRelationship]
    document_type: str
    extraction_confidence: float
    warnings: list[str]


EXTRACTION_PROMPT = """You are a forensic document analyst specialising in corporate ownership structures.
Analyse this document and extract ALL ownership relationships.

For each entity: full legal name, entity type (individual/company/trust/foundation),
jurisdiction, ownership percentage, role (director/shareholder/beneficial_owner/trustee),
and the exact sentence proving the relationship (evidence_snippet).

For each relationship: owner, owned, ownership_pct, exact evidence quote.

Be conservative — add uncertainty to warnings[].
If a name appears multiple times treat as the same entity.

Respond in JSON matching this schema exactly:
{
  "entities": [{"name","type","jurisdiction","ownership_pct","role","evidence_snippet","page_num"}],
  "relationships": [{"owner","owned","ownership_pct","evidence_snippet","page_num","trust_score"}],
  "document_type": "incorporation_cert|trust_deed|ownership_chart|other",
  "extraction_confidence": 0.0,
  "warnings": []
}"""


def _pdf_to_images(pdf_bytes: bytes) -> list[bytes]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        images.append(pix.tobytes("png"))
    doc.close()
    return images


def extract_ownership_from_pdf(pdf_bytes: bytes) -> OwnershipExtraction:
    images = _pdf_to_images(pdf_bytes)
    model = genai.GenerativeModel("gemini-2.5-flash-preview-04-17")

    parts = [EXTRACTION_PROMPT]
    for img in images:
        parts.append({"mime_type": "image/png", "data": img})

    response = model.generate_content(
        parts,
        generation_config={"response_mime_type": "application/json"},
    )

    return OwnershipExtraction.model_validate_json(response.text)


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", name.lower()).strip("_")


def convert_extraction_to_graph_format(
    extraction: OwnershipExtraction,
    document_name: str = "uploaded_document",
) -> tuple[list[dict], list[dict]]:
    nodes: list[dict] = []
    edges: list[dict] = []
    id_map: dict[str, str] = {}

    for entity in extraction.entities:
        node_id = _slugify(entity.name)
        id_map[entity.name] = node_id
        nodes.append({
            "id": node_id,
            "label": entity.name,
            "type": entity.type,
            "jurisdiction": entity.jurisdiction,
            "risk_level": "UNVERIFIED_AI",
            "incorporation_date": None,
            "sic_codes": [],
        })

    for idx, rel in enumerate(extraction.relationships):
        src = id_map.get(rel.owner, _slugify(rel.owner))
        tgt = id_map.get(rel.owned, _slugify(rel.owned))
        edges.append({
            "id": f"edge_{idx:03d}",
            "source": src,
            "target": tgt,
            "label": "owns",
            "ownership_pct": rel.ownership_pct,
            "trust_score": 0.4,
            "evidence_snippet": rel.evidence_snippet,
            "source_doc": document_name,
            "source_page": rel.page_num,
        })

    return nodes, edges
