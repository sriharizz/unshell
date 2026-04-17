# PROJECT FUSION 2.0 — MASTER BUILD DOCUMENT
**Enterprise AML & KYB Intelligence Graph**
**Hackfest 2026 | Team: technorev | NMAMIT**

> Backend reads Sections 1–5. Frontend reads Sections 6–7. Both read Section 8.

---

## TABLE OF CONTENTS
1. System Philosophy & Non-Negotiables
2. Four-Pillar Architecture
3. LangGraph Workflow — Full Node Map
4. Data Flow — All Three Scenarios
5. Backend Build Spec (As Built)
6. Frontend Build Spec
7. UI/UX Screen Map
8. Integration Contract (API Schema)
9. Demo Script
10. Honest Boundaries

---

## 1. SYSTEM PHILOSOPHY & NON-NEGOTIABLES

**Core Problem:** Banks cannot manually trace who truly owns a company when criminals hide behind layers of shell companies, nominee directors, and offshore jurisdictions.

**Our Solution:** An autonomous agentic system that ingests any corporate document (API or PDF), mathematically maps the ownership graph, detects fraud typologies, and checks against real sanctions data — all with evidence provenance on every finding.

### Non-Negotiables
- Every graph edge must link to its source document/snippet.
- The MCP server holds ALL credentials. LangGraph holds NONE.
- NetworkX does ALL math. LangGraph does NO math.
- The frontend must work for any company from any country.
- CORS must be configured from day one.

---

## 2. FOUR-PILLAR ARCHITECTURE

**PILLAR 1 — REACT FRONTEND** | Port 5173 (Vite)
Dual-Entry Gateway | Graph Visualizer | Evidence Panel

**PILLAR 2 — LANGGRAPH ORCHESTRATOR** | Port 8001 (FastAPI)
State Manager | Node Router | Holds ZERO API keys

**PILLAR 3 — TIERED AI ENGINE**
- Gemini 2.5 Flash → PDF ingestion and ownership extraction (unstructured data)
- NVIDIA NIM (meta/llama-3.1-70b-instruct) → Companies House JSON normalisation into graph schema (structured data)

**PILLAR 4 — MCP SERVER** | Port 8002
Zero-Trust Data Broker | Holds ALL API keys & DB credentials
Tools: fetch_uk_api (Companies House) | query_ofac (local SQLite) | known_addresses (shell address list)

### Why This Separation Wins With Judges
- MCP isolation = zero data leakage
- NVIDIA NIM = deterministic structured normalisation
- Gemini 2.5 Flash = best-in-class multimodal PDF reading
- NetworkX = math proves fraud, not AI opinion
- LangGraph = enterprise-grade pause/resume workflow

---

## 3. LANGGRAPH WORKFLOW — FULL NODE MAP

### State Object (agent/state.py)

Fields: mode, target_identifier, raw_pdf_bytes, discovered_nodes, discovered_edges, networkx_graph, incorporation_date, sic_codes, registered_address, pscs, known_shell_addresses, filing_count, current_risk_score, fatal_flags, cumulative_vectors, status, thread_id, offshore_dead_end, resolved_ubo, sanctions_hit, sanctions_detail, final_payload

### Node Definitions

NODE 1 — input_router_node
Reads state.mode. Routes to fetch_uk_api_node (api) or extract_pdf_node (document).

NODE 2A — fetch_uk_api_node [API PATH]
Calls MCP fetch_uk_api with CRN. Passes raw JSON to NVIDIA NIM normalizer. Gets back discovered_nodes and discovered_edges in graph schema. Sets offshore_dead_end if any PSC is_offshore=True.

NODE 2B — extract_pdf_node [DOCUMENT PATH]
Sends raw_pdf_bytes to Gemini 2.5 Flash. Merges extracted nodes/edges into existing state (additive, not replacing). Updates resolved_ubo from extracted individuals.

NODE 3 — calculate_risk_node
Calls graph/engine.py. Builds NetworkX graph. Runs all 6 risk vectors. Updates current_risk_score, fatal_flags, cumulative_vectors, networkx_graph.

NODE 4 — offshore_router_node [CONDITIONAL]
fatal_flags not empty → sanctions_check_node. offshore_dead_end=True → human_in_the_loop_node. else → sanctions_check_node.

NODE 5 — human_in_the_loop_node [PAUSE POINT]
Uses LangGraph interrupt(). Sets status=paused. Builds partial_payload with pause_reason. Resume via POST /approve/{thread_id}.

NODE 6 — sanctions_check_node
Calls MCP query_ofac with resolved_ubo. If match: score=100, appends OFAC_MATCH to fatal_flags.

NODE 7 — compile_output_node
Builds final_payload matching Section 8 schema exactly. Determines status: auto_reject (score≥95 or sanctions_hit) or complete.

---

## 4. DATA FLOW — ALL THREE DEMO SCENARIOS

### Scenario 1: GREEN — Monzo Bank (CRN: 09446231)
input_router → fetch_uk_api_node → NVIDIA NIM normalises → calculate_risk (score ~10) → offshore_router (clean) → sanctions_check (no match) → compile_output → AUTO_APPROVE

### Scenario 2: YELLOW → RED — IBS Management (CRN: 01683457)
fetch_uk_api_node → NVIDIA NIM normalises → calculate_risk (score 30–50, AGED_SHELL + VAGUE_SIC) → offshore_router → HITL PAUSE (BVI PSC detected) → User uploads BVI PDF → extract_pdf_node (Gemini) → calculate_risk (re-run, possible NOMINEE_PUPPET) → sanctions_check → compile_output → HIGH_RISK or AUTO_REJECT

### Scenario 3: RED — Seabon Limited (CRN: 06026625)
fetch_uk_api_node → NVIDIA NIM detects PREMIER DIRECTORS LIMITED → calculate_risk (NOMINEE_PUPPET + CIRCULAR_LOOP, fatal flags) → offshore_router (fatal flags → skip HITL) → sanctions_check (Oleg Deripaska → OFAC MATCH) → compile_output → CRITICAL / AUTO_REJECT

---

## 5. BACKEND BUILD SPEC (As Built)

### File Structure

```
backend/
├── main.py                      FastAPI app — CORS, /health, /investigate, /approve
├── load_ofac.py                 One-time: OFAC XML → sanctions.db + seeds known_addresses.db
├── requirements.txt
├── .env                         Real keys — gitignored
├── .env.example                 Template — safe to commit
├── .gitignore
├── README.md
│
├── agent/
│   ├── state.py                 InvestigationState TypedDict (single source of truth)
│   └── orchestrator.py          All 7 LangGraph nodes + run_investigation() + resume_investigation()
│
├── mcp/
│   └── server.py                FastAPI MCP broker on port 8002 — fetch_uk_api, query_ofac, known_addresses
│
├── ai/
│   ├── gemini_extractor.py      Gemini 2.5 Flash — PDF bytes → OwnershipExtraction (Pydantic)
│   └── nvidia_normalizer.py     NVIDIA NIM — raw CH JSON → nodes/edges via structured_output
│
├── graph/
│   └── engine.py                Pure NetworkX math — zero I/O, zero AI
│
├── data/
│   ├── sanctions.db             SQLite OFAC SDN list
│   ├── known_addresses.db       SQLite boiler room addresses (10 seeded)
│   └── ofac_sdn.xml             Raw OFAC XML
│
└── tests/
    ├── test_graph_engine.py     13 pytest tests — all 6 engine functions
    ├── test_mcp_server.py
    └── test_agent.py
```

### API Endpoints

POST /investigate — JSON {mode: api, crn} or multipart {mode: document, file}
POST /approve/{thread_id} — multipart {file: offshore PDF}
GET /health — {status: ok, service: fusion-backend, version: 2.0}

### MCP Endpoints (port 8002)

POST /tools/fetch_uk_api — {crn}
POST /tools/query_ofac — {name}
GET  /tools/known_addresses

### Tiered AI Routing

| Data Type | Model | Module |
|---|---|---|
| PDF (unstructured) | Gemini 2.5 Flash | ai/gemini_extractor.py |
| Companies House JSON (structured) | NVIDIA NIM llama-3.1-70b | ai/nvidia_normalizer.py |

### Risk Vectors (graph/engine.py — NON-NEGOTIABLE)

CUMULATIVE: AGED_SHELL +15 | VAGUE_SIC +15 | BOILER_ROOM +20 | SMURF_NETWORK +25
FATAL: CIRCULAR_LOOP +100 | NOMINEE_PUPPET +75

THRESHOLDS: 0–29 LOW_RISK | 30–64 MEDIUM_RISK | 65–94 HIGH_RISK | 95+ CRITICAL

---

## 6. FRONTEND BUILD SPEC

### File Structure

```
frontend/
├── src/
│   ├── App.jsx
│   ├── api/
│   │   └── client.js
│   ├── components/
│   │   ├── DualEntryGateway.jsx
│   │   ├── GraphCanvas.jsx
│   │   ├── CustomNode.jsx
│   │   ├── EvidencePanel.jsx
│   │   ├── RiskScoreboard.jsx
│   │   ├── HitlUploadZone.jsx
│   │   └── EntitySidebar.jsx
│   ├── constants/
│   │   └── riskColors.js
│   └── main.jsx
├── .env
└── vite.config.js
```

### Environment
VITE_API_BASE_URL=http://localhost:8001

### API Client Functions
investigateByAPI(crn) → POST /investigate with JSON body
investigateByDocument(pdfFile) → POST /investigate with multipart
resumeInvestigation(threadId, pdfFile) → POST /approve/{threadId}

---

## 7. UI/UX SCREEN MAP

Screen 1 — Dual-Entry Gateway: Toggle between CRN input and PDF upload
Screen 2 — Loading State: Step-by-step progress (7 nodes)
Screen 3 — HITL Pause: Orange screen, drag-drop offshore PDF upload zone
Screen 4 — Results: Three-panel layout — EntitySidebar | GraphCanvas | EvidencePanel

### Node Color Logic
AUTO_APPROVE: bg #1B5E20, border #4CAF50
MEDIUM_RISK: bg #E65100, border #FF9800
HIGH_RISK: bg #7B1FA2, border #CE93D8, pulse
CRITICAL: bg #B71C1C, border #F44336, pulse
OFFSHORE: bg #1A237E, border #5C6BC0
UNVERIFIED_AI: bg #263238, border #FF6B35, dashed edge

### Edge Trust Scores
1.0 → solid line (API-verified via Companies House)
0.4 → dashed line (AI-extracted by Gemini from PDF)
0.0 → dotted red (unverified / dead-end)

---

## 8. INTEGRATION CONTRACT (API SCHEMA)

Both teams agree on this. Do NOT change without telling each other.

### POST /investigate → Full Response

```
status: "complete" | "paused" | "auto_reject"
thread_id: uuid string
risk_score: 0–100 integer
risk_label: "LOW_RISK" | "MEDIUM_RISK" | "HIGH_RISK" | "CRITICAL"
fatal_flags: ["CIRCULAR_LOOP", "NOMINEE_PUPPET", "OFAC_MATCH"]
cumulative_vectors: ["AGED_SHELL", "VAGUE_SIC", "BOILER_ROOM", "SMURF_NETWORK"]
action_required: string
resolved_ubo: string
sanctions_hit: bool
sanctions_detail: string
graph:
  nodes: [{id, label, type, jurisdiction, risk_level, incorporation_date, sic_codes, tags}]
  edges: [{id, source, target, label, ownership_pct, trust_score, evidence_snippet, source_doc, source_page}]
stats:
  total_entities, loops_detected, puppets_detected, jurisdictions, investigation_depth
```

### POST /investigate → Paused Response (HITL)

```
status: "paused"
thread_id: uuid
pause_reason: string
partial_graph: same graph schema
risk_score: integer
```

---

## 9. DEMO SCRIPT (3 Minutes)

Setup: Pre-cache API responses. Have BVI PDF ready. Verify sanctions.db loaded. Serve built frontend.

[0:00] CRN 09446231 — Monzo. Green graph, score 10. "Clean directors, UK UBO. Cleared instantly."
[0:45] CRN 01683457 — IBS. Orange pause. Drag BVI PDF. AI reads, fuses node. "Hidden human revealed."
[1:30] CRN 06026625 — Seabon. PREMIER DIRECTORS LIMITED. 3,000 companies. NOMINEE_PUPPET fires. Circular loop. OFAC: Oleg Deripaska. Score 100. SAR Required. "Three seconds. $20B Russian Laundromat. Blocked."
[2:30] Click red edge. Evidence panel opens. "Every claim has a source."

---

## 10. HONEST BOUNDARIES

| Limitation | Why | What We Do |
|---|---|---|
| Jersey/Cayman trusts | No public beneficial ownership register | Flag as TRUST_DEAD_END node |
| Informal/verbal control | Not in any document | Out of scope |
| Crypto exit nodes | Wallets not in corporate registries | Flag when digital assets listed |
| Real-time updates | Companies House has ~24hr lag | Display data freshness timestamp |
| India MCA API | Requires login portal | PDF upload mode handles Indian companies |

---

## TEAM DIVISION

### Backend (Builds: agent/, mcp/, ai/, graph/, main.py)
1. Run load_ofac.py — seeds both databases
2. Start mcp/server.py — verify with all 4 curl tests
3. Verify graph/engine.py — run pytest tests/test_graph_engine.py
4. Test ai/ modules with sample PDF and sample CH JSON
5. Run full agent integration — all 3 CRN scenarios must pass
6. Verify CORS on all endpoints

### Frontend (Builds: React + React Flow)
1. Set up Vite, install @xyflow/react
2. Build api/client.js first
3. Build DualEntryGateway.jsx
4. Build GraphCanvas.jsx + CustomNode.jsx
5. Build EvidencePanel.jsx + RiskScoreboard.jsx
6. Wire HitlUploadZone.jsx
7. Test all three scenarios against backend

### Communication Rule
If Section 8 schema changes, BOTH teams agree and update together. No silent field additions.

---

*Document Version: 2.0 | Project Fusion 2.0 | Hackfest 2026 | Team technorev*
