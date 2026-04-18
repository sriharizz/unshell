import json
import logging
import re
from typing import Optional

import fitz  # PyMuPDF
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from rapidfuzz import fuzz
from dotenv import load_dotenv
import google.generativeai as genai
import os

load_dotenv()

logger = logging.getLogger(__name__)

# --- Pydantic Schemas ---

class ExtractedEntity(BaseModel):
    name: str
    entity_type: str        # "company" | "individual" | "trust" | "foundation"
    jurisdiction: Optional[str]
    incorporation_date: Optional[str]
    source_chunk_id: str    # REQUIRED — for cross-verification
    source_page: int        # REQUIRED
    confidence: float = Field(ge=0.0, le=1.0)

class ExtractedRelationship(BaseModel):
    owner: str              # must match an ExtractedEntity.name
    owned: str              # must match an ExtractedEntity.name
    ownership_pct: Optional[float]
    relationship_type: str  # "owns" | "directs" | "nominee_for" | "beneficiary_of"
    evidence_snippet: str   # verbatim quote from chunk, max 200 chars
    source_chunk_id: str    # REQUIRED
    source_page: int        # REQUIRED
    confidence: float = Field(ge=0.0, le=1.0)

class OwnershipExtractionV2(BaseModel):
    entities: list[ExtractedEntity]
    relationships: list[ExtractedRelationship]
    extraction_warnings: list[str]


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name.lower().strip())[:50]

# --- Global HuggingFace Embedding Model Singleton ---
_embeddings_v2 = None

def get_embedding_model():
    global _embeddings_v2
    if _embeddings_v2 is None:
        logger.info("Loading sentence-transformers/all-MiniLM-L6-v2 directly targeting CPU...")
        _embeddings_v2 = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
    return _embeddings_v2

# ═══════════════════════════════════════════════════
# STAGE R1: Ingestion
# ═══════════════════════════════════════════════════

def pdf_ingest(pdf_bytes: bytes) -> dict:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    raw_blocks = []
    rag_warnings = []
    total_chars = 0

    for page_num, page in enumerate(doc, start=1):
        # Extract text
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE).get("blocks", [])
        for chunk in blocks:
            if chunk.get("type") == 0:  # text block
                text = ""
                for line in chunk.get("lines", []):
                    for span in line.get("spans", []):
                        text += span.get("text", "")
                    text += "\n"
                text = text.strip()
                if len(text) >= 10:
                    total_chars += len(text)
                    raw_blocks.append({
                        "page": page_num,
                        "bbox": str(chunk.get("bbox")),
                        "text": text,
                        "type": "text"
                    })

        # Extract tables
        try:
            tables = page.find_tables()
            for table in tables:
                table_md = table.to_markdown()
                if len(table_md) >= 20:
                    total_chars += len(table_md)
                    raw_blocks.append({
                        "page": page_num,
                        "bbox": str(table.bbox),
                        "text": table_md,
                        "type": "table"
                    })
        except Exception:
            pass

    if total_chars < 200:
        rag_warnings.append("Scanned PDF detected. Triggering Gemini 2.5 Flash fallback...")
        logger.info("Falling back to Gemini 2.5 Flash for PDF extraction.")
        try:
            genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            # Write to temp file to upload to File API since it requires a file path usually, 
            # but we can just pass the inline data
            response = model.generate_content([
                {'mime_type': 'application/pdf', 'data': pdf_bytes},
                "Extract all readable text and tables from this document accurately. Do not summarize."
            ])
            
            gemini_text = response.text
            if gemini_text:
                raw_blocks = [{"page": 1, "bbox": "gemini_scan", "text": gemini_text, "type": "text"}]
                rag_warnings.append("Gemini fallback succeeded.")
            else:
                rag_warnings.append("Gemini fallback failed to return text.")
        except Exception as e:
            rag_warnings.append(f"Gemini fallback failed: {str(e)}")

    return {"raw_blocks": raw_blocks, "rag_warnings": rag_warnings, "total_pages": doc.page_count}

# ═══════════════════════════════════════════════════
# STAGE R2: Indexing
# ═══════════════════════════════════════════════════

def embed_and_index(raw_blocks: list) -> dict:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=80,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    chunks = []
    chunk_idx = 0
    
    # Process blocks
    for block in raw_blocks:
        if block["type"] == "table":
            chunks.append({
                "chunk_id": f"chunk_{chunk_idx:04d}",
                "page": block["page"],
                "bbox": block["bbox"],
                "text": block["text"],
                "type": "table"
            })
            chunk_idx += 1
        else:
            split_texts = text_splitter.split_text(block["text"])
            for split_t in split_texts:
                if len(split_t) >= 20:
                    chunks.append({
                        "chunk_id": f"chunk_{chunk_idx:04d}",
                        "page": block["page"],
                        "bbox": block["bbox"],
                        "text": split_t,
                        "type": "text"
                    })
                    chunk_idx += 1

    if not chunks:
        # Fallback if empty to avoid breaking FAISS
        return {"faiss_index": None, "chunks": [], "total_chunks": 0}

    docs = [c["text"] for c in chunks]
    metadatas = [{"chunk_id": c["chunk_id"], "page": c["page"]} for c in chunks]
    
    embeddings = get_embedding_model()
    faiss_index = FAISS.from_texts(docs, embeddings, metadatas=metadatas)

    return {"faiss_index": faiss_index, "chunks": chunks, "total_chunks": len(chunks)}


# ═══════════════════════════════════════════════════
# STAGE R3: Extraction
# ═══════════════════════════════════════════════════

def nvidia_mistral_extract(faiss_index: FAISS, chunks: list) -> dict:
    if not faiss_index or not chunks:
        empty_ext = OwnershipExtractionV2(entities=[], relationships=[], extraction_warnings=[])
        return {"raw_extraction": empty_ext, "retrieved_chunks_used": []}

    queries = [
        "beneficial owner percentage shares equity promoter significant control PSC",
        "director officer appointed nominee managing whole-time secretary DIN",
        "shareholder ownership allotted paid-up capital demat ordinary shares",
        "offshore jurisdiction BVI Cayman Mauritius Singapore Isle of Man foreign national NRI",
        "registered address incorporation date CIN CRN registered office ROC Companies House"
    ]

    retrieved_chunk_ids = set()
    retrieved_docs = []

    for query in queries:
        docs_and_scores = faiss_index.similarity_search_with_score(query, k=10)
        for doc, score in docs_and_scores:
            cid = doc.metadata.get("chunk_id")
            if cid not in retrieved_chunk_ids:
                retrieved_chunk_ids.add(cid)
                retrieved_docs.append((doc, score))

    # Sort by score ascending (lower FAISS L2 score means closer similarity)
    retrieved_docs.sort(key=lambda x: x[1])
    top_docs = retrieved_docs[:20]

    formatted_chunks = []
    retrieved_chunks_used = []
    
    for (doc, score) in top_docs:
        cid = doc.metadata.get("chunk_id")
        page = doc.metadata.get("page")
        formatted_chunks.append(f"--- [ID: {cid} | Page: {page}] ---\n{doc.page_content}")
        retrieved_chunks_used.append({"chunk_id": cid, "page": page, "text": doc.page_content})
        
    context_str = "\n\n".join(formatted_chunks)
    schema_json = json.dumps(OwnershipExtractionV2.model_json_schema(), indent=2)

    prompt = f"""
RETRIEVED DOCUMENT CHUNKS:
{context_str}

EXTRACTION RULES — ABSOLUTE:
1. Extract ONLY entities/relationships that appear VERBATIM or near-verbatim in the chunks above.
2. For every entity, record the exact chunk_id and page_number it came from.
3. If ownership_pct is not explicitly a NUMBER in the chunks, set it to null.
4. If uncertain whether two mentions are the same entity, treat as SEPARATE entities.
5. Do NOT infer, extrapolate, or use prior knowledge. Only use what is in the chunks.
6. Confidence: 1.0 = verbatim exact, 0.75–0.99 = clear paraphrase, below 0.75 = omit.
7. Legal boilerplate and standard clauses are NOT ownership claims. Ignore them.
8. CRITICAL RULE: DO NOT extract generic template definitions, boilerplate pronouns, or placeholder text. You must extract EXACT, SPECIFIC legal names. Explicitly IGNORE terms like "The person", "The relevant legal entity", "Subscriber", "Our Company", or "The Promoters".
9. OUTPUT: Valid JSON only. Do not add any conversational text like "Based on the document".
10. START YOUR RESPONSE WITH `{{` AND END WITH `}}`. NOTHING ELSE.
SCHEMA: {schema_json}
"""

    # Initialize Gemini natively for extraction
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.0,
        max_tokens=8192,
        google_api_key=os.environ.get("GEMINI_API_KEY")
    )

    try:
        response = llm.invoke([
            {"role": "system", "content": "You are a forensic corporate intelligence analyst extracting UBO data for AML compliance."},
            {"role": "user", "content": prompt}
        ])
        
        raw_text = response.content.strip()
        
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]

        # In case there's still conversational wrapped text
        json_match = re.search(r'(\{.*\})', raw_text, re.DOTALL)
        if json_match:
            raw_text = json_match.group(1)
        
        # Ensure we don't have trailing comma issues if truncated
        if not raw_text.endswith("}"):
            # It was truncated. We can't parse it easily with Pydantic without partial parsing,
            # so we just forcefully fallback to empty to avoid crashing the whole pipeline.
            raise ValueError("Truncated JSON output from LLM.")

        extracted = OwnershipExtractionV2.model_validate_json(raw_text)

        # Filter by confidence
        extracted.entities = [e for e in extracted.entities if e.confidence >= 0.75]
        extracted.relationships = [r for r in extracted.relationships if r.confidence >= 0.75]

    except Exception as e:
        logger.error(f"NVIDIA Mistral Extraction failed: {e}")
        extracted = OwnershipExtractionV2(entities=[], relationships=[], extraction_warnings=[str(e)])

    return {"raw_extraction": extracted, "retrieved_chunks_used": retrieved_chunks_used}

# ═══════════════════════════════════════════════════
# STAGE R4: Cross-Verification Firewall
# ═══════════════════════════════════════════════════

def cross_verify_firewall(raw_extraction: OwnershipExtractionV2, chunks: list) -> dict:
    chunks_by_id = {c["chunk_id"]: c for c in chunks}
    
    verified_nodes = []
    verified_edges = []
    unverified_count = 0
    total_claims = len(raw_extraction.entities) + len(raw_extraction.relationships)

    for entity in raw_extraction.entities:
        chunk = chunks_by_id.get(entity.source_chunk_id)
        if not chunk:
            unverified_count += 1
            continue

        match_score = fuzz.partial_ratio(entity.name.lower(), chunk["text"].lower())
        if match_score >= 90:
            trust_score = 1.0
        elif match_score >= 70:
            trust_score = 0.6
        else:
            unverified_count += 1
            continue

        node_id = _slugify(entity.name)
        verified_nodes.append({
            "id": node_id,
            "label": entity.name,
            "type": entity.entity_type,
            "jurisdiction": entity.jurisdiction or "",
            "risk_level": "UNVERIFIED_AI",
            "trust_score": trust_score,
            "incorporation_date": entity.incorporation_date,
            "sic_codes": [],
            "source_page": entity.source_page,
            "source_chunk_id": entity.source_chunk_id
        })

    for rel in raw_extraction.relationships:
        chunk = chunks_by_id.get(rel.source_chunk_id)
        if not chunk:
            unverified_count += 1
            continue

        snippet_score = fuzz.partial_ratio(rel.evidence_snippet.lower(), chunk["text"].lower())
        if snippet_score < 75:
            unverified_count += 1
            continue

        trust_score = 1.0 if snippet_score >= 95 else 0.6
        
        verified_edges.append({
            "id": f"edge_{len(verified_edges):03d}",
            "source": _slugify(rel.owner),
            "target": _slugify(rel.owned),
            "label": rel.relationship_type,
            "ownership_pct": rel.ownership_pct or 0.0,
            "trust_score": trust_score,
            "evidence_snippet": rel.evidence_snippet,
            "source_doc": "uploaded_document",
            "source_page": rel.source_page,
            "source_chunk_id": rel.source_chunk_id
        })

    verified_count = total_claims - unverified_count
    overall_confidence_score = round((verified_count / total_claims * 100), 1) if total_claims > 0 else 0.0

    offshore_dead_end = False
    hitl_reason = ""
    unverified_pct = (unverified_count / total_claims) if total_claims > 0 else 0.0

    if total_claims > 0 and unverified_pct > 0.30:
        offshore_dead_end = True
        hitl_reason = f"{unverified_count}/{total_claims} claims unverifiable (>30% threshold)"

    return {
        "discovered_nodes": verified_nodes,
        "discovered_edges": verified_edges,
        "overall_confidence_score": overall_confidence_score,
        "verification_stats": {
            "total_claims": total_claims,
            "verified": verified_count,
            "dropped": unverified_count,
            "unverified_pct": unverified_pct
        },
        "offshore_dead_end": offshore_dead_end,
        "hitl_reason": hitl_reason
    }

# ═══════════════════════════════════════════════════
# HELPER: Orchestrator
# ═══════════════════════════════════════════════════

def run_rag_pipeline(pdf_bytes: bytes) -> dict:
    ingest_result = pdf_ingest(pdf_bytes)
    raw_blocks = ingest_result["raw_blocks"]
    
    index_result =embed_and_index(raw_blocks)
    faiss_index = index_result["faiss_index"]
    chunks = index_result["chunks"]

    extracted_result = nvidia_mistral_extract(faiss_index, chunks)
    raw_extraction = extracted_result["raw_extraction"]

    final_result = cross_verify_firewall(raw_extraction, chunks)
    final_result["rag_warnings"] = ingest_result["rag_warnings"]
    final_result["total_chunks"] = index_result["total_chunks"]
    final_result["total_pages"] = ingest_result["total_pages"]
    
    return final_result
