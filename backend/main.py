import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agent.orchestrator import run_investigation, resume_investigation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fusion.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Project Fusion 2.0 starting on port 8001")
    logger.info("📡 MCP broker: http://localhost:8002")
    logger.info("🔒 CORS: http://localhost:5173")
    yield
    logger.info("🛑 Shutting down")


app = FastAPI(
    title="Project Fusion 2.0",
    description="AML/KYB Intelligence Graph — Hackfest 2026",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__},
    )


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "service": "fusion-backend", "version": "2.0"}


@app.post("/investigate", tags=["Investigation"])
async def investigate(
    mode: str = Form(...),
    crn: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    if mode == "api":
        if not crn:
            raise HTTPException(status_code=422, detail="crn is required for api mode")
        result = await run_investigation(mode="api", crn=crn)

    elif mode == "document":
        if not file:
            raise HTTPException(status_code=422, detail="file is required for document mode")
        pdf_bytes = await file.read()
        result = await run_investigation(mode="document", pdf_bytes=pdf_bytes)

    else:
        raise HTTPException(status_code=422, detail=f"Invalid mode: {mode}")

    return result


@app.post("/approve/{thread_id}", tags=["Investigation"])
async def approve(thread_id: str, file: UploadFile = File(...)):
    pdf_bytes = await file.read()
    try:
        result = await resume_investigation(thread_id=thread_id, pdf_bytes=pdf_bytes)
    except Exception as exc:
        if "not found" in str(exc).lower() or "no checkpoint" in str(exc).lower():
            raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")
        raise
    return result
