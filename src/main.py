"""The parallax.observer application.

A FastAPI app with a websocket chat and a terminal style interface. The
corpus is the only source of facts, and every reply says which facts it
used.
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.agentic.context import ContextManager
from src.agentic.orchestrator import Orchestrator
from src.config import get_settings
from src.llm import LLMClient
from src.session import SessionStore

logger = logging.getLogger(__name__)

GUI_DIR = Path(__file__).parent / "gui"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wire the app together on startup."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())

    llm = LLMClient(
        base_url=settings.llm_api_base,
        model=settings.llm_model,
        timeout=settings.llm_timeout,
        max_tokens=settings.llm_max_tokens,
        temperature=settings.llm_temperature,
    )

    viking = None
    try:
        from src.memory.viking_client import VikingClient

        viking = VikingClient(
            server=settings.openviking_url,
            user=settings.openviking_user,
            profile_dir=settings.profile_path,
            api_key=settings.openviking_api_key,
            account=settings.openviking_account,
        )
        logger.info("the memory server is up: %s", viking.health())
    except Exception as exc:
        logger.warning("the memory server is not reachable: %s", exc)
        viking = None

    app.state.settings = settings
    app.state.llm = llm
    app.state.viking = viking
    app.state.sessions = SessionStore(profile_dir=settings.profile_path, viking=viking)
    app.state.orchestrator = Orchestrator(
        llm=llm,
        viking=viking,
        context_manager=ContextManager(
            max_tokens=settings.context_max_tokens,
            alert_threshold=settings.context_alert_threshold,
            recent_turns_kept=settings.context_recent_turns,
        ),
        top_k=settings.retrieval_top_k,
        target_tier=settings.retrieval_target,
    )

    yield

    await llm.aclose()
    if viking is not None:
        viking.close()


app = FastAPI(title="parallax.observer", version="0.1.0", lifespan=lifespan)


# ----------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """The interface."""
    page = GUI_DIR / "index.html"
    if not page.exists():
        return HTMLResponse("<h1>parallax.observer</h1><p>the interface is missing</p>")
    return HTMLResponse(page.read_text())


# ----------------------------------------------------------------------
# Health and status
# ----------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, Any]:
    """Is the app up."""
    return {"status": "ok"}


@app.get("/api/status")
async def status() -> dict[str, Any]:
    """What the monitoring bar shows."""
    llm: LLMClient = app.state.llm
    viking = app.state.viking

    llm_up = llm.available()
    viking_up = False
    corpus: dict[str, Any] = {}
    if viking is not None:
        try:
            viking_up = bool(viking.health())
            corpus = viking.stats()
        except Exception:
            viking_up = False

    stats = llm.stats
    return {
        "llm": {
            "up": llm_up,
            "model": llm.model,
            "requests": stats.requests,
            "failures": stats.failures,
            "prompt_tokens": stats.prompt_tokens,
            "completion_tokens": stats.completion_tokens,
            "avg_latency": round(stats.average_latency, 3),
            "p95_latency": round(stats.p95_latency, 3),
            "tokens_per_second": round(
                stats.completion_tokens / stats.total_seconds, 1
            )
            if stats.total_seconds
            else 0.0,
        },
        "viking": {
            "up": viking_up,
            "corpus": corpus,
        },
        "sessions": len(app.state.sessions.list()),
    }


@app.get("/api/gpu")
async def gpu() -> dict[str, Any]:
    """The GPU, if there is one."""
    try:
        import pynvml

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        name = pynvml.nvmlDeviceGetName(handle)

        temperature = 0
        with suppress(Exception):
            temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

        power = 0
        with suppress(Exception):
            power = pynvml.nvmlDeviceGetPowerUsage(handle) // 1000

        pynvml.nvmlShutdown()
        return {
            "name": name,
            "util": util.gpu,
            "memory_used_mb": memory.used // 1024 // 1024,
            "memory_total_mb": memory.total // 1024 // 1024,
            "temperature": temperature,
            "power_watts": power,
        }
    except Exception as exc:
        return {"error": str(exc)}


@app.get("/api/fact")
async def fact(uri: str) -> JSONResponse:
    """One fact, with its text, for the lab view."""
    viking = app.state.viking
    if viking is None:
        return JSONResponse({"error": "the corpus is not reachable"}, status_code=503)

    try:
        payload = {
            "uri": uri,
            "abstract": viking.get_abstract(uri),
            "overview": viking.get_overview(uri),
            "content": viking.get_content(uri),
        }
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)

    return JSONResponse(payload)


# ----------------------------------------------------------------------
# Sessions
# ----------------------------------------------------------------------


@app.post("/api/session")
async def create_session(payload: dict[str, Any]) -> JSONResponse:
    """Start a session."""
    store: SessionStore = app.state.sessions
    session = store.create(
        alterego=payload.get("alterego", "Visitor"),
        belief=payload.get("belief"),
        goal=payload.get("goal"),
        worldview=payload.get("worldview"),
    )
    return JSONResponse(session.to_dict())


@app.get("/api/session/{session_id}")
async def get_session(session_id: str) -> JSONResponse:
    """One session, with its transcript."""
    store: SessionStore = app.state.sessions
    session = store.get(session_id)
    if session is None:
        return JSONResponse({"error": "no such session"}, status_code=404)
    return JSONResponse(session.to_dict())


@app.get("/api/sessions")
async def list_sessions() -> JSONResponse:
    """Every session."""
    store: SessionStore = app.state.sessions
    return JSONResponse([session.to_dict() for session in store.list()])


# ----------------------------------------------------------------------
# The chat
# ----------------------------------------------------------------------


@app.websocket("/ws/{session_id}")
async def chat(websocket: WebSocket, session_id: str) -> None:
    """The conversation."""
    await websocket.accept()

    store: SessionStore = app.state.sessions
    session = store.get(session_id)
    if session is None:
        await websocket.send_json({"type": "error", "message": "no such session"})
        await websocket.close()
        return

    orchestrator: Orchestrator = app.state.orchestrator
    llm: LLMClient = app.state.llm

    await websocket.send_json(
        {
            "type": "ready",
            "session": session.to_dict(),
            "model": llm.model,
            "corpus": app.state.viking is not None,
        }
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                message = {"type": "message", "text": raw}

            kind = message.get("type", "message")

            if kind == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if kind != "message":
                continue

            text = (message.get("text") or "").strip()
            if not text:
                continue

            await websocket.send_json({"type": "thinking", "text": text})

            try:
                turn = await orchestrator.run_turn(
                    message=text,
                    worldview=session.worldview,
                    alterego=session.alterego,
                    belief=session.belief,
                    goal=session.goal,
                    state=session.state,
                    emotion_state=session.emotion,
                    history=session.history,
                    preserved=session.preserved(),
                    category=message.get("category"),
                )
            except Exception as exc:
                logger.exception("the turn failed")
                await websocket.send_json(
                    {"type": "error", "message": f"something went wrong: {exc}"}
                )
                continue

            success = message.get("agreed")
            store.record_turn(session, turn, success=success)

            await websocket.send_json({"type": "reply", "turn": turn.to_dict()})

    except WebSocketDisconnect:
        logger.info("session %s disconnected", session_id)
    except Exception:
        logger.exception("the websocket failed")


# ----------------------------------------------------------------------
# Static
# ----------------------------------------------------------------------

static_dir = GUI_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
