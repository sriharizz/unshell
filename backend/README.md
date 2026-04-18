# Project Fusion 2.0 — Hyper-RAG Edition

AML/KYB intelligence system using NVIDIA NIM, FAISS, and LangGraph.

## Setup Instructions

1. **Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: On first run, HuggingFace will download the `all-MiniLM-L6-v2` embedding model (~80MB).*

3. **Environment Setup**:
   Copy the example environment file and fill in your keys:
   ```bash
   cp .env.example .env
   ```
   You must paste your NVIDIA NIM API key (from api.build.nvidia.com) into the `.env` file.

4. **Run the Server**:
   ```bash
   uvicorn main:app --port 8001 --reload
   ```

*See the master prompt for instructions on running the MCP broker and seeding the SQLite database.*
