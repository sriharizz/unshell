# PROJECT FUSION 2.0 — BACKEND MASTER BUILD PROMPT
**For AI IDE (Cursor / Windsurf / Copilot Workspace)**  
**Version: 2.0 — Hyper-RAG Edition (NVIDIA NIM + FAISS)**  
**Execute ONE phase at a time. Verify output. Then continue.**

---

## HOW TO USE THIS DOCUMENT

Each phase is a **standalone prompt** you paste into your AI IDE.
- Complete Phase N fully before starting Phase N+1
- Each phase ends with a **VERIFICATION CHECKLIST** — run every check before moving on
- Do NOT skip verifications. One broken file breaks everything downstream.
- The AI IDE has **full creative freedom** within the constraints marked `[NON-NEGOTIABLE]`

---

## FINAL FILE STRUCTURE (Target)

```
backend/
├── main.py                  # FastAPI app — CORS + route registration
├── agent.py                 # LangGraph orchestrator — all 7 nodes + RAG sub-graph
├── mcp_server.py            # Standalone MCP data broker (port 8002)
├── graph_engine.py          # Pure NetworkX math — zero I/O
├── rag_engine.py            # Hyper-RAG pipeline — PyMuPDF + FAISS + NVIDIA NIM
├── load_ofac.py             # One-time script: OFAC XML → sanctions.db
├── data/
│   ├── sanctions.db         # SQLite — OFAC SDN list (pre-loaded)
│   ├── known_addresses.db   # SQLite — boiler room addresses
│   └── ofac_sdn.xml         # Raw OFAC XML download (input for load_ofac.py)
├── tests/
│   ├── test_graph_engine.py
│   ├── test_rag_engine.py
│   ├── test_mcp_server.py
│   └── test_agent.py
├── requirements.txt
├── .env.example             # Template — NEVER commit real .env
└── README.md
```

---

## PHASE 1 OF 6 — PROJECT SCAFFOLD + DEPENDENCIES

### YOUR ROLE FOR THIS PHASE
You are a **Python infrastructure engineer** setting up a production-grade FastAPI project. Your priority is clean dependency management, correct virtual environment isolation, and a working health check endpoint.

### PROMPT (Paste this into your AI IDE)

```
You are building the backend for Project Fusion 2.0 — an AML/KYB intelligence system.

TASK: Set up the project scaffold only. Do NOT write agent logic yet.

CREATE these files:

1. requirements.txt — include EXACT versions for:
   - fastapi==0.115.0
   - uvicorn[standard]==0.30.6
   - python-multipart==0.0.9        (for PDF file uploads)
   - langgraph==0.2.28
   - langchain-core==0.3.15
   - langchain-community==0.3.1     (FAISS LangChain wrapper)
   - langchain-huggingface==0.1.0   (local HuggingFace embeddings)
   - langchain-nvidia-ai-endpoints==0.3.5  (NVIDIA NIM — Mistral)
   - sentence-transformers==3.1.1   (all-MiniLM-L6-v2 local model)
   - faiss-cpu==1.8.0               (in-memory vector store, no server needed)
   - PyMuPDF==1.24.5                (fitz — PDF text + table extraction)
   - rapidfuzz==3.9.1               (fuzzy string matching for cross-verification)
   - networkx==3.3
   - httpx==0.27.0                  (async HTTP for Companies House API)
   - pydantic==2.8.0
   - python-dotenv==1.0.1
   - mcp==1.0.0                     (Model Context Protocol SDK)
   - aiosqlite==0.20.0              (async SQLite)
   - lxml==5.3.0                    (for OFAC XML parsing)
   - pytest==8.3.2
   - pytest-asyncio==0.23.8

   NOTE: Do NOT include langchain-google-genai or chromadb — these are removed in this version.

2. .env.example — template with these keys (no real values):
   COMPANIES_HOUSE_API_KEY=your_key_here
   NVIDIA_API_KEY=your_nvidia_build_api_key_here
   MCP_SERVER_URL=http://localhost:8002

3. main.py — FastAPI app with:
   - CORS middleware configured for http://localhost:5173 [NON-NEGOTIABLE]
   - GET /health endpoint returning {"status": "ok", "service": "fusion-backend", "version": "2.0"}
   - Placeholder comments for /investigate and /approve/{thread_id} routes (implement in Phase 6)
   - Lifespan event that logs "Project Fusion 2.0 — Hyper-RAG Edition starting on port 8001"

4. README.md — setup instructions:
   - python -m venv venv
   - source venv/bin/activate
   - pip install -r requirements.txt
   - cp .env.example .env (then fill in NVIDIA_API_KEY from api.build.nvidia.com)
   - How to run: uvicorn main:app --port 8001 --reload
   - Note about first run: HuggingFace will download all-MiniLM-L6-v2 (~80MB) on first use

5. Create empty __init__.py files where needed for proper Python packaging.

You have creative freedom on: logging format, README styling, helper utilities.
You do NOT have freedom to change: the CORS origin, the port numbers, the endpoint names.
```

### VERIFICATION CHECKLIST — Phase 1
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

uvicorn main:app --port 8001 --reload &

curl http://localhost:8001/health
# Expected: {"status":"ok","service":"fusion-backend","version":"2.0"}

curl -H "Origin: http://localhost:5173" -I http://localhost:8001/health
# Expected: access-control-allow-origin: http://localhost:5173 in response headers

pkill -f uvicorn
```
**✅ Phase 1 complete only when ALL curl commands return expected output.**

---

## PHASE 2 OF 6 — MCP SERVER (Data Broker)

### YOUR ROLE FOR THIS PHASE
You are a **security-focused backend engineer** building a zero-trust data broker. This MCP server is the ONLY component that touches external APIs and databases. LangGraph calls this — it must be bulletproof.

### PROMPT (Paste this into your AI IDE)

```
You are building mcp_server.py for Project Fusion 2.0.

CONTEXT: This is an MCP (Model Context Protocol) server running on port 8002.
It is the ONLY component that holds API keys. It exposes exactly 2 tools.
LangGraph will call these tools — it sends in a name/CRN and gets back structured JSON.

TASK: Build mcp_server.py with these two tools:

TOOL 1: fetch_uk_api(crn: str) → dict
  - Calls UK Companies House API: https://api.company-information.service.gov.uk
  - Endpoints to call (all with Basic Auth using COMPANIES_HOUSE_API_KEY):
      GET /company/{crn}                               → company profile
      GET /company/{crn}/persons-with-significant-control → PSC register
      GET /company/{crn}/officers                      → directors list
      GET /company/{crn}/filing-history               → filing count
  - Return this EXACT schema (do NOT remove any field):
    {
      "company_name": str,
      "crn": str,
      "incorporation_date": "YYYY-MM-DD",
      "sic_codes": [str],
      "registered_address": str,
      "officers": [
        {
          "name": str,
          "role": str,
          "appointment_date": "YYYY-MM-DD",
          "resignation_date": "YYYY-MM-DD | null",
          "is_corporate": bool
        }
      ],
      "pscs": [
        {
          "name": str,
          "type": "individual | corporate | legal_person",
          "ownership_band": str,
          "ownership_pct": float,
          "jurisdiction": str,
          "natures_of_control": [str],
          "is_offshore": bool
        }
      ],
      "filing_count": int,
      "raw_address_string": str
    }
  - Set is_offshore = True if jurisdiction is NOT in ["GB", "UK", "United Kingdom", "England", "Wales", "Scotland"]
  - Parse ownership_band ("25% to 50%") into ownership_pct float midpoint (37.5)
  - Handle API errors gracefully — return {"error": str, "crn": crn} if Companies House is unreachable

TOOL 2: query_ofac(name: str) → dict
  - Query the local SQLite file at data/sanctions.db
  - SQL: SELECT * FROM sdn_list WHERE UPPER(name) LIKE UPPER('%{name}%')
  - Also check aliases table if it exists
  - Return:
    {
      "match": bool,
      "detail": str,
      "program": str,
      "matched_name": str
    }
  - Use fuzzy matching: also check each word in name separately if exact fails
  - If no match: return {"match": false, "detail": "No OFAC match found", "program": "", "matched_name": ""}

ALSO BUILD: load_ofac.py
  - One-time script to parse OFAC SDN XML → sanctions.db
  - Download URL: https://www.treasury.gov/ofac/downloads/sdn.xml
  - Parse: SDN_ENTRY → {uid, last_name, first_name, sdn_type, programs, aka_list}
  - Create table sdn_list with columns: id, name, type, program, aliases
  - Print progress every 1000 records
  - Print "✅ Loaded {count} SDN entries to sanctions.db" when done

ALSO CREATE: data/known_addresses.db
  - SQLite with table: shell_addresses(id, address_text, confidence_score, source)
  - Pre-populate with 10 known UK boiler room addresses
  - Include: "1 Victoria Street, London", "27 Old Gloucester Street, London" and others
```

### VERIFICATION CHECKLIST — Phase 2
```bash
python load_ofac.py
# Expected: "✅ Loaded XXXX SDN entries to sanctions.db"

python mcp_server.py &

curl -X POST http://localhost:8002/tools/fetch_uk_api \
  -H "Content-Type: application/json" \
  -d '{"crn": "09446231"}'
# Expected: JSON with company_name "MONZO BANK LIMITED"

curl -X POST http://localhost:8002/tools/query_ofac \
  -H "Content-Type: application/json" \
  -d '{"name": "Deripaska"}'
# Expected: JSON with match: true

pkill -f mcp_server
```
**✅ Phase 2 complete only when all curl tests return expected output.**

---

## PHASE 3 OF 6 — GRAPH ENGINE (Pure Math)

### YOUR ROLE FOR THIS PHASE
You are a **computational graph theorist and risk modeling engineer**. This module is the mathematical heart of the system. It must be purely functional — no API calls, no file I/O, no side effects. Every function takes data in, returns results out. 100% testable in isolation.

### PROMPT (Paste this into your AI IDE)

```
You are building graph_engine.py for Project Fusion 2.0.

ABSOLUTE RULE: This file has ZERO external calls. No HTTP, no database, no file I/O.
Pure functions only. Input data structures in, output data structures out.

TASK: Build graph_engine.py with these functions:

FUNCTION 1: build_graph(nodes: list[dict], edges: list[dict]) → nx.DiGraph
  - Creates a directed NetworkX graph
  - Node attributes: id, label, type, jurisdiction, risk_level, incorporation_date, sic_codes
  - Edge attributes: source, target, ownership_pct, trust_score, evidence_snippet
  - Handle: empty nodes list, duplicate edges (keep higher trust_score), self-loops (log and skip)
  - Add a "source_doc" attribute per edge if present (PDF path vs API)

FUNCTION 2: detect_cycles(graph: nx.DiGraph) → list[list[str]]
  - Uses nx.simple_cycles()
  - Returns list of cycles (each cycle = list of node IDs)
  - Returns [] if no cycles or empty graph

FUNCTION 3: calculate_degree_centrality(graph: nx.DiGraph) → dict[str, float]
  - Uses nx.degree_centrality()
  - Returns {node_id: centrality_score}
  - Returns {} if empty graph

FUNCTION 4: calculate_risk_score(
    nodes: list[dict],
    edges: list[dict],
    graph: nx.DiGraph,
    incorporation_date: str,         # "YYYY-MM-DD" or None
    filing_count: int,               # from Companies House filing_count field
    sic_codes: list[str],
    address: str,
    pscs: list[dict],
    known_shell_addresses: list[str]
) → tuple[int, list[str], list[str]]
  Returns: (score: int capped at 100, fatal_flags: list, cumulative_vectors: list)

  IMPLEMENT THESE EXACT VECTORS:

  CUMULATIVE (additive):
  - AGED_SHELL: incorporation_date > 5 years old AND filing_count < 3 → score += 15
      Date parsing: handle None gracefully (skip vector if date missing)
  - VAGUE_SIC: any sic_code in ["74990","99999","74100","82990","70100","74200"] → score += 15
  - BOILER_ROOM: normalize address (lowercase, strip punctuation) and check against
      known_shell_addresses (also normalized) → score += 20
  - SMURF_NETWORK: 3 or more PSC ownership_pct values all between 15.0 and 24.9 → score += 25

  FATAL (can stack, capped at 100):
  - CIRCULAR_LOOP: detect_cycles() returns any cycle → score += 100, fatal_flags.append("CIRCULAR_LOOP")
  - NOMINEE_PUPPET: any node centrality score > 0.15 → score += 75, fatal_flags.append("NOMINEE_PUPPET")

  RULES:
  - Calculate cumulative vectors first, then fatal vectors
  - Final score = min(total, 100)
  - Return fatal_flags (FATAL triggers) and cumulative_vectors (CUMULATIVE triggers) as separate lists

FUNCTION 5: get_risk_label(score: int) → str
  - 0–64   → "MEDIUM_RISK"   (no auto-approve band — any score can go to HUMAN_REVIEW)
  - 65–94  → "HIGH_RISK"
  - 95–100 → "CRITICAL"
  NOTE: LOW_RISK label is intentionally removed. 0–64 = HUMAN REVIEW, not auto-approval.

FUNCTION 6: get_action_required(score: int, fatal_flags: list, sanctions_hit: bool) → str
  - sanctions_hit = True  → "File SAR immediately. Block account opening."
  - score >= 95           → "File SAR immediately. Block account opening."
  - score >= 65           → "Escalate to senior compliance officer. Do not open account."
  - score >= 0            → "Manual review required. Send to analyst queue."
  NOTE: There is NO auto-approval action. All cases require human review or escalation.

ALSO BUILD: tests/test_graph_engine.py
  Write pytest tests for ALL 6 functions. Include:
  - Test with clean company data (score 0–30, no fatal flags, action = "Manual review")
  - Test with circular ownership (A owns B, B owns A) — must detect CIRCULAR_LOOP
  - Test with 3 PSCs at 20% each — must detect SMURF_NETWORK
  - Test with vague SIC code 74990 — must trigger AGED_SHELL + VAGUE_SIC
  - Test with empty graph — all functions must return gracefully
  - Test score capping at 100 (CIRCULAR_LOOP + NOMINEE_PUPPET should not exceed 100)
  - Test BOILER_ROOM detection with fuzzy address normalization

You have creative freedom on: helper functions, additional graph metrics (betweenness centrality,
community detection for bonus UI features), date parsing edge cases.
You do NOT have freedom to change: function signatures, vector names, score values (+15/+15/+20/+25/+75/+100).
```

### VERIFICATION CHECKLIST — Phase 3
```bash
pytest tests/test_graph_engine.py -v
# All tests must PASS. Zero failures allowed before Phase 4.
```
**✅ Phase 3 complete only when pytest shows 0 failures.**

---

## PHASE 4 OF 6 — RAG ENGINE (Hyper-RAG: PyMuPDF + FAISS + NVIDIA NIM)

### YOUR ROLE FOR THIS PHASE
You are an **AI document intelligence engineer** building a zero-hallucination PDF extraction pipeline. You are replacing the old single-shot Gemini Vision approach with a grounded, 4-stage Hyper-RAG pipeline. Every extracted claim must be verified against a retrievable source chunk before it reaches the NetworkX graph engine. The pipeline must handle messy real-world corporate PDFs from both India (MCA21, ROC filings, MOA/AOA) and the UK (Companies House extracts, BVI certs, trust deeds).

**Latency Budget: under 10 seconds end-to-end for a 20-page PDF.**

### PROMPT (Paste this into your AI IDE)

```
You are building rag_engine.py for Project Fusion 2.0.

CONTEXT: When a user uploads a PDF (offshore incorporation document, trust deed, share transfer
agreement, ROC filing, etc.), we must extract ownership entities and relationships from it using
a 4-stage Hyper-RAG pipeline. The output must be in the EXACT same node/edge format as
fetch_uk_api — so graph_engine.py never knows the difference.

CRITICAL RULE: The NVIDIA NIM LLM (Mistral) must NEVER see the full PDF.
It sees ONLY the FAISS-retrieved chunks relevant to each query. This is non-negotiable.

═══════════════════════════════════════════════════
STAGE R1: pdf_ingest(pdf_bytes: bytes) → dict
═══════════════════════════════════════════════════

Library: fitz (PyMuPDF) — NOT PyPDF2 or pdfplumber.
Why: PyMuPDF returns bounding box coordinates per block, needed for cross-verification.

IMPLEMENT:
  - Open PDF from bytes: fitz.open(stream=pdf_bytes, filetype="pdf")
  - For each page, call page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
  - Extract text blocks: type==0 blocks only, skip blocks with < 10 chars (noise)
  - For each text block, build: {"page": int, "bbox": tuple, "text": str, "type": "text"}
  - For tables: call page.find_tables() wrapped in try/except (not all PDFs have tables)
    - Each table: call table.to_markdown(), build {"page": int, "bbox": table.bbox, "text": md, "type": "table"}
    - Skip tables with < 20 chars of markdown
  - Scanned PDF detection: if total_chars < 200 across all pages, add warning to rag_warnings list
  - Return: {"raw_blocks": list, "rag_warnings": list, "total_pages": int}

═══════════════════════════════════════════════════
STAGE R2: embed_and_index(raw_blocks: list) → dict
═══════════════════════════════════════════════════

Embedding model: sentence-transformers/all-MiniLM-L6-v2 (local, no API key, ~80MB)
  - Use HuggingFaceEmbeddings from langchain_huggingface
  - model_kwargs={"device": "cpu"}, encode_kwargs={"normalize_embeddings": True}
  - NOTE: For Indian PDFs with mixed Hindi/English, a comment should note the swap to
    "paraphrase-multilingual-mpnet-base-v2" (one line change)

Vector Store: FAISS in-memory via langchain_community.vectorstores.FAISS
  - Use FAISS.from_texts(texts, embeddings, metadatas=metadatas)
  - This is a flat index — perfect for < 500 chunks, sub-ms retrieval

CHUNKING STRATEGY (Medium complexity, high effectiveness — optimised for 10s latency budget):
  - Use RecursiveCharacterTextSplitter from langchain.text_splitter
  - chunk_size=400, chunk_overlap=80
  - separators=["\n\n", "\n", ". ", " ", ""]
  - Tables: ALWAYS treated as one atomic chunk — never split
    (preserves "Premier Directors Ltd | 100%" table rows intact)
  - Prose: split with the splitter, skip sub-chunks < 20 chars

METADATA per chunk: {"chunk_id": "chunk_NNNN", "page": int, "bbox": str, "type": "text|table"}
  - chunk_id format: f"chunk_{i:04d}" where i is sequential across all chunks

Return: {"faiss_index": FAISS, "chunks": list[dict], "total_chunks": int}
  - chunks list is stored separately for cross-verification lookup by chunk_id

═══════════════════════════════════════════════════
STAGE R3: nvidia_mistral_extract(faiss_index, chunks) → dict
═══════════════════════════════════════════════════

LLM: ChatNVIDIA from langchain_nvidia_ai_endpoints
  - model="mistralai/mixtral-8x7b-instruct-v0.1"
  - temperature=0.0  (deterministic JSON output — non-negotiable)
  - max_tokens=2048
  - API key loaded from environment: os.getenv("NVIDIA_API_KEY")

PYDANTIC SCHEMAS (define at module top level):

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

RETRIEVAL — 5 TARGETED QUERIES, TOP-10 EACH, DEDUPLICATED:
  Use faiss_index.similarity_search_with_score(query, k=10) for each query.
  Deduplicate results by chunk_id (keep first occurrence = highest similarity).
  After dedup, rank by score and take top 20 chunks for the prompt window.

  QUERIES (these are calibrated for India + UK corporate PDF vocabulary):
  1. "beneficial owner percentage shares equity promoter significant control PSC"
  2. "director officer appointed nominee managing whole-time secretary DIN"
  3. "shareholder ownership allotted paid-up capital demat ordinary shares"
  4. "offshore jurisdiction BVI Cayman Mauritius Singapore Isle of Man foreign national NRI"
  5. "registered address incorporation date CIN CRN registered office ROC Companies House"

PROMPT — implement this EXACTLY (it is the anti-hallucination contract):

  SYSTEM: You are a forensic corporate intelligence analyst extracting UBO data for AML compliance.

  USER:
  RETRIEVED DOCUMENT CHUNKS:
  {formatted_chunks}

  EXTRACTION RULES — ABSOLUTE:
  1. Extract ONLY entities/relationships that appear VERBATIM or near-verbatim in the chunks above.
  2. For every entity, record the exact chunk_id and page_number it came from.
  3. If ownership_pct is not explicitly a NUMBER in the chunks, set it to null.
  4. If uncertain whether two mentions are the same entity, treat as SEPARATE entities.
  5. Do NOT infer, extrapolate, or use prior knowledge. Only use what is in the chunks.
  6. Confidence: 1.0 = verbatim exact, 0.75–0.99 = clear paraphrase, below 0.75 = omit.
  7. Legal boilerplate and standard clauses are NOT ownership claims. Ignore them.
  8. OUTPUT: Valid JSON only. No markdown. No prose. No backticks. No explanation.
  SCHEMA: {schema_json}

JSON PARSING: Wrap model_validate_json in try/except.
  - Strip ```json fences if present before parsing
  - On parse error: return OwnershipExtractionV2 with empty lists + warning message
  - After parse: filter out entities with confidence < 0.75 and relationships with confidence < 0.75

Return: {"raw_extraction": OwnershipExtractionV2, "retrieved_chunks_used": list}

═══════════════════════════════════════════════════
STAGE R4: cross_verify_firewall(raw_extraction, chunks) → dict
═══════════════════════════════════════════════════

This is the hallucination firewall. Every Mistral claim is challenged here.
Library: rapidfuzz.fuzz.partial_ratio for fuzzy name/snippet matching.

FOR EACH ENTITY:
  1. Look up source_chunk_id in chunks_by_id dict
  2. If chunk not found → unverified_count += 1, skip
  3. Run: match_score = fuzz.partial_ratio(entity.name.lower(), chunk["text"].lower())
  4. If match_score >= 90 → trust_score = 1.0 (verbatim, solid edge in UI)
  5. If match_score >= 70 → trust_score = 0.6 (name variant, e.g., "Ltd" vs "Limited" — dashed edge)
  6. If match_score < 70 → unverified_count += 1, skip (hallucinated name — DROP)
  7. Append to verified_nodes with all fields + trust_score + source_page + source_chunk_id
     Set risk_level = "UNVERIFIED_AI" on all nodes (UI renders dashed border)

FOR EACH RELATIONSHIP:
  1. Look up source_chunk_id
  2. If not found → unverified_count += 1, skip
  3. Run: snippet_score = fuzz.partial_ratio(rel.evidence_snippet.lower(), chunk["text"].lower())
  4. If snippet_score < 75 → unverified_count += 1, skip
  5. trust_score = 1.0 if snippet_score >= 95, else 0.6
  6. Append to verified_edges

CALCULATE overall_confidence_score:
  total_claims = len(extracted.entities) + len(extracted.relationships)
  verified_count = total_claims - unverified_count
  overall_confidence_score = round((verified_count / total_claims * 100), 1) if total_claims > 0 else 0.0

HITL ESCALATION:
  If total_claims > 0 and (unverified_count / total_claims) > 0.30:
    Set offshore_dead_end = True
    Set hitl_reason = f"{unverified_count}/{total_claims} claims unverifiable (>30% threshold)"

Return:
  {
    "discovered_nodes": verified_nodes,
    "discovered_edges": verified_edges,
    "overall_confidence_score": float,
    "verification_stats": {"total_claims": int, "verified": int, "dropped": int, "unverified_pct": float},
    "offshore_dead_end": bool,
    "hitl_reason": str
  }

═══════════════════════════════════════════════════
HELPER FUNCTION: run_rag_pipeline(pdf_bytes: bytes) → dict
═══════════════════════════════════════════════════

Orchestrates all 4 stages in sequence. Returns the cross_verify_firewall result dict
plus rag_warnings and total_pages from the ingest stage.
This is the single function called by agent.py.

ALSO BUILD: tests/test_rag_engine.py
  Test R1 (ingest) with a synthetic PDF created by fpdf2 or reportlab:
    - Create a simple PDF with known text: "Premier Directors Limited owns 100% of Shell Corp BVI"
    - Verify raw_blocks is not empty, page == 1
  Test R2 (chunking + FAISS):
    - Verify total_chunks > 0
    - Verify FAISS similarity search returns the created chunk
  Test R4 (cross_verify_firewall) with synthetic data:
    - Mock raw_extraction with a claim that DOES exist in chunks → should verify
    - Mock raw_extraction with a fabricated name not in chunks → should drop
    - Verify overall_confidence_score is correct
    - Verify unverified > 30% triggers offshore_dead_end = True

NAMING HELPER (module-level):
  def _slugify(name: str) -> str:
      import re
      return re.sub(r"[^a-z0-9_]", "_", name.lower().strip())[:50]

You have creative freedom on: async vs sync, progress logging, additional chunking heuristics,
caching the HuggingFace model load across requests (use a module-level singleton).
You do NOT have freedom to change: the 5 retrieval queries, the confidence threshold (0.75),
the HITL trigger threshold (30%), the trust_score values (1.0 / 0.6 / 0.0), the output schema.
```

### VERIFICATION CHECKLIST — Phase 4
```bash
# Install fpdf2 temporarily for test PDF creation
pip install fpdf2

# Run RAG engine tests
pytest tests/test_rag_engine.py -v

# Quick smoke test with a sample PDF
python -c "
from rag_engine import run_rag_pipeline

# Create minimal test PDF bytes
from fpdf import FPDF
pdf = FPDF()
pdf.add_page()
pdf.set_font('Helvetica', size=12)
pdf.cell(200, 10, txt='Premier Directors Limited owns 100% of Atlantic Shell Corp BVI.', ln=True)
pdf.cell(200, 10, txt='John Smith is appointed as beneficial owner with 75% shareholding.', ln=True)
pdf_bytes = bytes(pdf.output())

result = run_rag_pipeline(pdf_bytes)
print('Nodes found:', len(result['discovered_nodes']))
print('Edges found:', len(result['discovered_edges']))
print('Confidence score:', result['overall_confidence_score'])
print('Verification stats:', result['verification_stats'])
assert result['overall_confidence_score'] >= 0, 'Score must be numeric'
print('✅ RAG pipeline smoke test PASSED')
"

# Expected output:
# Nodes found: > 0
# Edges found: > 0
# Confidence score: a float 0.0–100.0
# ✅ RAG pipeline smoke test PASSED
```
**✅ Phase 4 complete only when pytest shows 0 failures and smoke test prints PASSED.**

---

## PHASE 5 OF 6 — LANGGRAPH AGENT

### YOUR ROLE FOR THIS PHASE
You are a **senior AI systems architect** building the orchestration brain. You are wiring together Phases 2, 3, and 4 into a stateful LangGraph workflow. The RAG engine (Phase 4) replaces the old `extract_pdf_node`. The state object now carries `overall_confidence_score`. The score thresholds enforce NO AUTO-APPROVE — every case goes to HUMAN REVIEW at minimum.

### PROMPT (Paste this into your AI IDE)

```
You are building agent.py for Project Fusion 2.0.

CONTEXT: You have these modules ready:
- mcp_server.py: exposes fetch_uk_api(crn) and query_ofac(name) as MCP tools
- graph_engine.py: pure math functions (no I/O)
- rag_engine.py: run_rag_pipeline(pdf_bytes) → verified nodes + edges + confidence score

TASK: Build agent.py — the LangGraph workflow with exactly 7 nodes.

═══════════════════════════════════════════════
STATE OBJECT — implement this exactly as a TypedDict:
═══════════════════════════════════════════════

class InvestigationState(TypedDict):
    # INPUT
    mode: str                          # "api" or "document"
    target_identifier: str             # CRN string or "DOCUMENT_UPLOAD"
    raw_pdf_bytes: Optional[bytes]

    # GRAPH DATA
    discovered_nodes: list
    discovered_edges: list
    networkx_graph: Optional[object]

    # COMPANY METADATA (for risk scoring)
    incorporation_date: Optional[str]
    filing_count: int                  # NEW: passed directly to calculate_risk_score
    sic_codes: list
    registered_address: str
    pscs: list
    known_shell_addresses: list

    # RISK ENGINE
    current_risk_score: int
    fatal_flags: list
    cumulative_vectors: list

    # INVESTIGATION STATUS
    status: str
    thread_id: str
    offshore_dead_end: bool
    resolved_ubo: str
    hitl_reason: str                   # NEW: why HITL was triggered

    # SANCTIONS
    sanctions_hit: bool
    sanctions_detail: str

    # RAG / CONFIDENCE (NEW FIELDS)
    overall_confidence_score: float    # 0.0–100.0 — % of Mistral claims that verified
    verification_stats: dict           # {total_claims, verified, dropped, unverified_pct}
    rag_warnings: list                 # e.g., ["scanned PDF detected"]
    total_chunks: int                  # for UI extraction_meta stats
    total_pages: int                   # for UI extraction_meta stats

    # OUTPUT
    final_payload: Optional[dict]

═══════════════════════════════════════════════
THE 7 NODES — implement each as an async function:
═══════════════════════════════════════════════

NODE 1: input_router_node(state) → Command
  - Reads state["mode"]
  - Returns Command(goto="fetch_uk_api_node") if mode == "api"
  - Returns Command(goto="rag_ingest_node") if mode == "document"
  - Returns error state update with status="error" if mode is invalid

NODE 2A: fetch_uk_api_node(state) → dict (state update)
  - Call MCP tool fetch_uk_api with state["target_identifier"]
  - Update state: discovered_nodes, discovered_edges, incorporation_date, sic_codes,
    registered_address, pscs, filing_count
  - Set offshore_dead_end = True if ANY psc has is_offshore == True
  - Set resolved_ubo = first individual PSC name, fallback to first officer name
  - Load known_shell_addresses from data/known_addresses.db (aiosqlite)
  - Set overall_confidence_score = 100.0 (API data is verified — no RAG needed)
  - Set verification_stats = {"source": "companies_house_api", "verified": True}

NODE 2B: rag_ingest_node(state) → dict (state update)
  - Call rag_engine.run_rag_pipeline(state["raw_pdf_bytes"])
  - The function returns: discovered_nodes, discovered_edges, overall_confidence_score,
    verification_stats, offshore_dead_end, hitl_reason, rag_warnings, total_chunks, total_pages
  - Merge all returned fields into state (do not overwrite if value is already set from a resume)
  - Extract resolved_ubo from discovered_nodes: first node with type == "individual"
  - Load known_shell_addresses from data/known_addresses.db (aiosqlite)
  - If rag_pipeline returns discovered_nodes as empty list: set status = "error", 
    final_payload = {"error": "No entities could be extracted from the uploaded PDF"}

NODE 3: calculate_risk_node(state) → dict (state update)
  - Call graph_engine.build_graph(state["discovered_nodes"], state["discovered_edges"])
  - Call graph_engine.calculate_risk_score(
        nodes=state["discovered_nodes"],
        edges=state["discovered_edges"],
        graph=networkx_graph,
        incorporation_date=state["incorporation_date"],
        filing_count=state["filing_count"],
        sic_codes=state["sic_codes"],
        address=state["registered_address"],
        pscs=state["pscs"],
        known_shell_addresses=state["known_shell_addresses"]
    )
  - Update: current_risk_score, fatal_flags, cumulative_vectors, networkx_graph
  - Do NOT modify offshore_dead_end here — it is set by Node 2A/2B only

NODE 4: offshore_router_node(state) → Command
  - if state["fatal_flags"] is not empty → Command(goto="sanctions_check_node") — skip HITL
  - elif state["offshore_dead_end"] == True → Command(goto="human_in_the_loop_node")
  - else → Command(goto="sanctions_check_node")

NODE 5: human_in_the_loop_node(state) → dict (state update)
  - Set state["status"] = "paused"
  - Build partial_payload with status="paused":
    {
      "status": "paused",
      "thread_id": state["thread_id"],
      "risk_score": state["current_risk_score"],
      "risk_label": graph_engine.get_risk_label(state["current_risk_score"]),
      "fatal_flags": state["fatal_flags"],
      "overall_confidence_score": state["overall_confidence_score"],
      "pause_reason": state.get("hitl_reason", "Offshore entity detected — manual review required"),
      "partial_graph": {"nodes": state["discovered_nodes"], "edges": state["discovered_edges"]}
    }
  - Set state["final_payload"] = partial_payload
  - Use LangGraph interrupt() to pause execution at this node
  - The /approve/{thread_id} FastAPI endpoint injects new PDF bytes and resumes the graph

NODE 6: sanctions_check_node(state) → dict (state update)
  - Call MCP tool query_ofac with state["resolved_ubo"]
  - If resolved_ubo is empty or None: skip and set sanctions_hit = False
  - Update: sanctions_hit, sanctions_detail
  - If match: current_risk_score = 100, append "OFAC_MATCH" to fatal_flags

NODE 7: compile_output_node(state) → dict (state update)
  - Determine final status:
      if current_risk_score >= 65 OR sanctions_hit: status = "auto_reject"
      else: status = "human_review"    ← NOTE: "complete" is NEVER used — no auto-approve
  - Build final_payload matching this EXACT schema:
    {
      "status": str,                       # "human_review" | "auto_reject" | "paused" | "error"
      "thread_id": str,
      "risk_score": int,
      "risk_label": str,                   # from graph_engine.get_risk_label()
      "fatal_flags": list,
      "cumulative_vectors": list,
      "action_required": str,              # from graph_engine.get_action_required()
      "resolved_ubo": str,
      "sanctions_hit": bool,
      "sanctions_detail": str,
      "overall_confidence_score": float,   # NEW: 0.0–100.0
      "graph": {
        "nodes": [
          {
            "id": str, "label": str, "type": str, "jurisdiction": str,
            "risk_level": str, "trust_score": float
          }
        ],
        "edges": [
          {
            "id": str, "source": str, "target": str, "ownership_pct": float,
            "trust_score": float, "evidence_snippet": str,
            "source_doc": str, "source_page": int, "source_chunk_id": str
          }
        ]
      },
      "stats": {
        "total_entities": int,
        "loops_detected": int,
        "puppets_detected": int,
        "jurisdictions": list[str],
        "investigation_depth": int         # number of nodes in graph
      },
      "extraction_meta": {                 # PDF path only — omit or null for API path
        "total_pages": int,
        "total_chunks": int,
        "total_claims_extracted": int,
        "verified_claims": int,
        "dropped_claims": int,
        "unverified_pct": float,
        "extraction_warnings": list[str]
      }
    }

═══════════════════════════════════════════════
GRAPH WIRING:
═══════════════════════════════════════════════

  builder = StateGraph(InvestigationState)
  Add all 7 nodes with these names: "input_router", "fetch_uk_api", "rag_ingest",
    "calculate_risk", "offshore_router", "human_in_the_loop", "sanctions_check", "compile_output"

  Edges:
    START → input_router (input_router_node routes via Command pattern)
    fetch_uk_api → calculate_risk
    rag_ingest → calculate_risk
    calculate_risk → offshore_router (routes via Command pattern)
    human_in_the_loop → (interrupt — resumed externally via /approve endpoint)
    sanctions_check → compile_output
    compile_output → END

  Checkpointer:
    Use MemorySaver() for pause/resume
    graph = builder.compile(checkpointer=MemorySaver(), interrupt_before=["human_in_the_loop"])

═══════════════════════════════════════════════
EXPOSE THESE TWO FUNCTIONS:
═══════════════════════════════════════════════

async def run_investigation(
    mode: str,
    crn: str = None,
    pdf_bytes: bytes = None,
    thread_id: str = None
) → dict:
  - Generate thread_id with uuid4() if not provided
  - Build initial InvestigationState with defaults (empty lists, 0 scores, etc.)
  - Invoke: await graph.ainvoke(state, config={"configurable": {"thread_id": thread_id}})
  - Return state["final_payload"]

async def resume_investigation(thread_id: str, pdf_bytes: bytes) → dict:
  - Load checkpoint by thread_id from MemorySaver
  - Update state: raw_pdf_bytes = pdf_bytes, mode = "document"
  - Resume: await graph.ainvoke(None, config={"configurable": {"thread_id": thread_id}})
  - Return state["final_payload"]
  - Raise ValueError("Thread not found") if thread_id does not exist

You have creative freedom on: async implementation details, additional logging/tracing,
helper functions, retry logic for MCP calls, error recovery between nodes.
You do NOT have freedom to change: node names, the State TypedDict field names,
the graph edge wiring, the final_payload schema, the NO-AUTO-APPROVE rule (status
must never be "complete" — always "human_review" or "auto_reject").
```

### VERIFICATION CHECKLIST — Phase 5

**Update score threshold assertions — no auto-approve:**

```bash
python mcp_server.py &
sleep 2

# Test Scenario 1: Monzo (clean company — should be HUMAN_REVIEW, not auto-approve)
python -c "
import asyncio
from agent import run_investigation
result = asyncio.run(run_investigation(mode='api', crn='09446231'))
print('Status:', result['status'])
print('Score:', result['risk_score'])
print('Label:', result['risk_label'])
print('Confidence:', result['overall_confidence_score'])
assert result['status'] == 'human_review', f'Expected human_review, got {result[\"status\"]}'
assert result['risk_score'] < 65, 'Monzo should score < 65'
print('✅ Scenario 1 PASSED — Monzo correctly sent to human review')
"

# Test Scenario 2: Seabon (should be AUTO-REJECT with fatal flags)
python -c "
import asyncio
from agent import run_investigation
result = asyncio.run(run_investigation(mode='api', crn='06026625'))
print('Status:', result['status'])
print('Score:', result['risk_score'])
print('Fatal flags:', result['fatal_flags'])
assert result['status'] == 'auto_reject', f'Expected auto_reject, got {result[\"status\"]}'
assert result['risk_score'] >= 65, 'Seabon should score >= 65'
assert len(result['fatal_flags']) > 0, 'Seabon must have fatal flags'
print('✅ Scenario 2 PASSED — Seabon correctly auto-rejected')
"

pkill -f mcp_server
```
**✅ Phase 5 complete only when both assertions pass.**

---

## PHASE 6 OF 6 — FASTAPI ROUTES + INTEGRATION TEST

### YOUR ROLE FOR THIS PHASE
You are a **full-stack API engineer** doing final integration. Wire the agent into FastAPI routes. Every edge case must have a proper HTTP response. Run the complete end-to-end demo.

### PROMPT (Paste this into your AI IDE)

```
You are completing main.py for Project Fusion 2.0.

CONTEXT: agent.py is built with run_investigation() and resume_investigation().
You already have the FastAPI app with CORS and /health. Now add the real routes.

TASK: Add these 2 routes to main.py:

ROUTE 1: POST /investigate
  Request body — can be either:
    - JSON: {"mode": "api", "crn": "09446231"}
    - Multipart form: mode="document" + file=<pdf>
  Use Form() + File() with Optional for both types

  Logic:
    if mode == "api":
        result = await run_investigation(mode="api", crn=crn)
    if mode == "document":
        pdf_bytes = await file.read()
        result = await run_investigation(mode="document", pdf_bytes=pdf_bytes)

  Response: the final_payload dict from agent
  Status codes: 200 OK, 422 if validation fails, 500 with detail on agent error

ROUTE 2: POST /approve/{thread_id}
  Path param: thread_id (str)
  Body: multipart form with file=<pdf>
  Logic:
    pdf_bytes = await file.read()
    result = await resume_investigation(thread_id=thread_id, pdf_bytes=pdf_bytes)
  Response: the final_payload dict
  Status codes: 200 OK, 404 if thread_id not found, 500 on error

ADD global exception handler:
  @app.exception_handler(Exception)
  Returns: {"error": str(e), "type": type(e).__name__} with status 500

You have creative freedom on: Pydantic request/response models, background tasks,
SSE streaming for progress updates (bonus), input validation.
You do NOT have freedom to change: endpoint paths, CORS config, response schema.
```

### FINAL INTEGRATION VERIFICATION — Phase 6
```bash
python mcp_server.py &
sleep 2
uvicorn main:app --port 8001 --reload &
sleep 3

# SCENARIO 1: Monzo (should be human_review, not auto-approve)
curl -X POST http://localhost:8001/investigate \
  -H "Content-Type: application/json" \
  -d '{"mode": "api", "crn": "09446231"}' | python -m json.tool
# ✅ status == "human_review"
# ✅ risk_score < 65
# ✅ overall_confidence_score == 100.0 (API path)

# SCENARIO 2: IBS Management (offshore — should pause)
curl -X POST http://localhost:8001/investigate \
  -H "Content-Type: application/json" \
  -d '{"mode": "api", "crn": "01683457"}' | python -m json.tool
# ✅ status == "paused"
# ✅ thread_id is a UUID string
# ✅ pause_reason contains "offshore" or "Offshore"

# SCENARIO 2 RESUME
export THREAD_ID="<paste thread_id from above>"
curl -X POST http://localhost:8001/approve/$THREAD_ID \
  -F "file=@tests/sample_bvi.pdf" | python -m json.tool
# ✅ status == "human_review" or "auto_reject"
# ✅ overall_confidence_score present and > 0

# SCENARIO 3: Seabon (should be auto_reject with fatal flags)
curl -X POST http://localhost:8001/investigate \
  -H "Content-Type: application/json" \
  -d '{"mode": "api", "crn": "06026625"}' | python -m json.tool
# ✅ status == "auto_reject"
# ✅ risk_score >= 65
# ✅ fatal_flags not empty

# HEALTH + CORS
curl http://localhost:8001/health
curl -X POST http://localhost:8001/investigate \
  -H "Origin: http://localhost:5173" \
  -H "Content-Type: application/json" \
  -d '{"mode": "api", "crn": "09446231"}' -I
# ✅ access-control-allow-origin: http://localhost:5173

echo "🎉 ALL INTEGRATION TESTS PASSED — Backend ready for frontend handoff"

pkill -f mcp_server
pkill -f uvicorn
```

---

## HANDOFF CHECKLIST TO FRONTEND TEAM

```
[ ] GET  /health                → 200 {"status":"ok"}
[ ] POST /investigate (api)     → 200 with full payload, status == "human_review" or "auto_reject"
[ ] POST /investigate (doc)     → 200 with full payload + extraction_meta + overall_confidence_score
[ ] POST /approve/{thread_id}   → 200 with resumed graph payload
[ ] CORS header present for origin http://localhost:5173
[ ] Monzo (09446231)    → status "human_review", risk_score < 65
[ ] IBS   (01683457)    → status "paused", thread_id present
[ ] Seabon (06026625)   → status "auto_reject", fatal_flags not empty
[ ] overall_confidence_score present in all responses (100.0 for API path, 0–100 for doc path)
[ ] extraction_meta present in document-mode responses
[ ] All graph.edges have: id, source, target, trust_score, evidence_snippet, source_page
[ ] All graph.nodes have: id, label, type, jurisdiction, risk_level, trust_score
[ ] sanctions.db loaded — query_ofac returns correct results
[ ] No API keys in any committed file (only .env, gitignored)
[ ] rag_engine.py: NVIDIA_API_KEY loaded from .env — never hardcoded
```

---

## GLOBAL AI IDE RULES (Apply to ALL Phases)

**You ALWAYS have freedom to:**
- Choose sync vs async implementations
- Add helper functions and utilities
- Improve error messages and logging
- Add type hints and docstrings
- Add caching (e.g., module-level HuggingFace model singleton to avoid reload per request)
- Restructure code within a file for clarity
- Add extra Pydantic validators
- Write more tests than asked

**You NEVER have freedom to:**
- Change CORS origin or port numbers
- Change endpoint paths (/investigate, /approve/{thread_id}, /health)
- Change the final_payload JSON schema
- Change State TypedDict field names
- Change risk vector names (AGED_SHELL, VAGUE_SIC, BOILER_ROOM, SMURF_NETWORK, CIRCULAR_LOOP, NOMINEE_PUPPET)
- Change score thresholds (0–64 HUMAN_REVIEW, 65–94 AUTO_REJECT, 95–100 CRITICAL)
- Change vector score values (+15, +15, +20, +25, +75, +100)
- Put API keys in any file other than .env
- Make graph_engine.py do any I/O or API calls
- Set status = "complete" or "auto_approve" — there is NO auto-approve in this system
- Let NVIDIA NIM see the full PDF — it must only see FAISS-retrieved chunks

---

*Project Fusion 2.0 | Backend Master Build Prompt v2.0 | Hyper-RAG Edition | Hackfest 2026 | Team: technorev | NMAMIT*
