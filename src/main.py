"""The parallax.observer application.

A FastAPI app with a websocket chat and a terminal style interface. The
corpus is the only source of facts, and every reply says which facts it
used.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.agentic.context import ContextManager
from src.agentic.fire_chat import STAGE_ORDER, Debate, FireChat, Side, Stage
from src.agentic.orchestrator import Orchestrator
from src.config import get_settings
from src.demos import demo_list, get_demo
from src.llm import LLMClient
from src.observability import setup_tracing
from src.session import Session, SessionStore

logger = logging.getLogger(__name__)

GUI_DIR = Path(__file__).parent / "gui"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wire the app together on startup."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())

    if settings.phoenix_enabled:
        setup_tracing(settings.otel_endpoint, enabled=True)

    llm = LLMClient(
        base_url=settings.llm_api_base,
        model=settings.llm_model,
        timeout=settings.llm_timeout,
        max_tokens=settings.llm_max_tokens,
        temperature=settings.llm_temperature,
        instrument=settings.phoenix_enabled,
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


@app.get("/api/image")
async def image(worldview: str, name: str) -> JSONResponse:
    """The picture of a fact, if it has one."""
    if not worldview or not name:
        return JSONResponse({"error": "worldview and name are needed"}, status_code=400)

    if "/" in name or ".." in name or "/" in worldview or ".." in worldview:
        return JSONResponse({"error": "no"}, status_code=400)

    directory = Path("facts/knowledge") / worldview / "images" / name
    if not directory.is_dir():
        return JSONResponse({"error": "no such image"}, status_code=404)

    for picture in sorted(directory.iterdir()):
        if picture.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            return FileResponse(picture, media_type=f"image/{picture.suffix.lstrip('.').lower()}")

    return JSONResponse({"error": "no picture in it"}, status_code=404)


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
        turn_task: asyncio.Task | None = None

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

            if turn_task is not None and not turn_task.done():
                # the visitor spoke over the agent, cut it off
                turn_task.cancel()
                with suppress(asyncio.CancelledError):
                    await turn_task
                await websocket.send_json(
                    {"type": "interrupted", "text": text}
                )

            await websocket.send_json({"type": "thinking", "text": text})
            turn_task = asyncio.create_task(
                _run_and_stream(
                    websocket,
                    orchestrator,
                    store,
                    session,
                    text,
                    message.get("category"),
                )
            )

    except WebSocketDisconnect:
        logger.info("session %s disconnected", session_id)
    except Exception:
        logger.exception("the websocket failed")


async def _run_and_stream(
    websocket: WebSocket,
    orchestrator: Orchestrator,
    store: SessionStore,
    session: Session,
    text: str,
    category: str | None = None,
) -> None:
    """One turn, streamed to the socket."""
    try:
        turn = None
        async for piece in orchestrator.stream_turn(
            message=text,
            worldview=session.worldview,
            alterego=session.alterego,
            belief=session.belief,
            goal=session.goal,
            state=session.state,
            emotion_state=session.emotion,
            history=session.history,
            preserved=session.preserved(),
            category=category,
        ):
            if isinstance(piece, str):
                await websocket.send_json({"type": "delta", "text": piece})
            else:
                turn = piece

        if turn is None:
            return

        store.record_turn(session, turn)
        await websocket.send_json({"type": "reply", "turn": turn.to_dict()})

    except asyncio.CancelledError:
        logger.info("the turn was cut off")
        raise
    except Exception as exc:
        logger.exception("the turn failed")
        with suppress(Exception):
            await websocket.send_json(
                {"type": "error", "message": f"something went wrong: {exc}"}
            )


@app.websocket("/ws/fire/{session_id}")
async def fire_chat(websocket: WebSocket, session_id: str) -> None:
    """The three way debate."""
    await websocket.accept()

    store: SessionStore = app.state.sessions
    session = store.get(session_id)
    if session is None:
        await websocket.send_json({"type": "error", "message": "no such session"})
        await websocket.close()
        return

    llm: LLMClient = app.state.llm
    viking = app.state.viking

    await websocket.send_json(
        {"type": "ready", "session": session.to_dict(), "model": llm.model}
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                message = {"type": "start", "topic": raw}

            if message.get("type") != "start":
                continue

            topic = (message.get("topic") or "").strip()
            if not topic:
                continue

            worldviews = message.get("worldviews") or [
                "spherical-earth",
                "flat-earth",
                "discworld",
            ]
            sides = [Side.from_worldview(world) for world in worldviews]

            chat = FireChat(llm, viking)
            debate = Debate(sides=sides)

            for stage in STAGE_ORDER:
                debate.stage = stage
                if stage == Stage.JUDGMENT:
                    break

                for index, side in enumerate(sides):
                    await websocket.send_json(
                        {"type": "stage", "stage": str(stage), "speaker": side.name}
                    )
                    speech = await chat.speak(debate, side, stage, topic, index)
                    debate.speeches.append(speech)
                    await websocket.send_json(
                        {"type": "speech", "speech": speech.to_dict()}
                    )

            debate.stage = Stage.JUDGMENT
            debate.moderation = await chat.moderator.score(
                debate.transcript, [side.name for side in sides]
            )
            await websocket.send_json(
                {"type": "verdict", "moderation": debate.moderation.model_dump()}
            )

    except WebSocketDisconnect:
        logger.info("the debate disconnected")
    except Exception:
        logger.exception("the debate failed")


@app.get("/api/demos")
async def demos() -> JSONResponse:
    """The scripts that can be watched."""
    return JSONResponse(demo_list())


@app.post("/api/demo")
async def start_demo(payload: dict[str, Any]) -> JSONResponse:
    """Start one of the scripts."""
    demo = get_demo(payload.get("id", ""))
    if demo is None:
        return JSONResponse({"error": "no such demo"}, status_code=404)

    store: SessionStore = app.state.sessions
    session = store.create(
        alterego=payload.get("alterego", "Visitor"),
        belief=demo.belief,
        worldview=demo.worldview,
    )
    return JSONResponse({"session": session.to_dict(), "demo": demo.to_dict()})


@app.websocket("/ws/demo/{session_id}")
async def watch_demo(websocket: WebSocket, session_id: str) -> None:
    """Play a script, with the agent answering live.

    The server drives the visitor's side, so the reader only has to watch.
    A message from the reader takes over and the script stops.
    """
    await websocket.accept()

    store: SessionStore = app.state.sessions
    session = store.get(session_id)
    if session is None:
        await websocket.send_json({"type": "error", "message": "no such session"})
        await websocket.close()
        return

    orchestrator: Orchestrator = app.state.orchestrator
    llm: LLMClient = app.state.llm

    demo = get_demo(websocket.query_params.get("demo", ""))
    if demo is None:
        await websocket.send_json({"type": "error", "message": "no such demo"})
        await websocket.close()
        return

    await websocket.send_json(
        {
            "type": "ready",
            "session": session.to_dict(),
            "demo": demo.to_dict(),
            "model": llm.model,
        }
    )

    playback = asyncio.create_task(
        _play_demo(websocket, orchestrator, store, session, demo)
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

            if kind == "skip":
                playback.cancel()
                playback = asyncio.create_task(
                    _play_demo(
                        websocket,
                        orchestrator,
                        store,
                        session,
                        demo,
                        start=len(demo.lines) - 1,
                    )
                )
                continue

            if kind != "message":
                continue

            # the reader takes over, the script is over
            playback.cancel()
            text = (message.get("text") or "").strip()
            if not text:
                continue

            await websocket.send_json({"type": "line", "text": text, "taken_over": True})
            await _run_and_stream(
                websocket, orchestrator, store, session, text, message.get("category")
            )

    except WebSocketDisconnect:
        playback.cancel()
        logger.info("the demo disconnected")
    except Exception:
        playback.cancel()
        logger.exception("the demo failed")


async def _play_demo(
    websocket: WebSocket,
    orchestrator: Orchestrator,
    store: SessionStore,
    session: Session,
    demo: Any,
    start: int = 0,
) -> None:
    """Play the script, one line at a time."""
    for line in demo.lines[start:]:
        try:
            # the visitor types it out, so it reads like a conversation
            await _type_out(websocket, line.text)
            await websocket.send_json(
                {"type": "line", "text": line.text, "note": line.note}
            )
            await asyncio.sleep(line.pause)

            turn = None
            async for piece in orchestrator.stream_turn(
                message=line.text,
                worldview=session.worldview,
                alterego=session.alterego,
                belief=session.belief,
                goal=session.goal,
                state=session.state,
                emotion_state=session.emotion,
                history=session.history,
                preserved=session.preserved(),
            ):
                if isinstance(piece, str):
                    await websocket.send_json({"type": "delta", "text": piece})
                else:
                    turn = piece

            if turn is None:
                return

            # the visitor's reaction is what says whether the argument landed
            success: bool | None = None
            if session.state.user_agreed:
                success = True
            elif session.state.user_rejected:
                success = False

            store.record_turn(session, turn, success=success)
            await websocket.send_json({"type": "reply", "turn": turn.to_dict()})
            await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            logger.info("the playback was cut off")
            raise
        except Exception as exc:
            logger.exception("the playback failed")
            with suppress(Exception):
                await websocket.send_json(
                    {"type": "error", "message": f"something went wrong: {exc}"}
                )
            return

    await websocket.send_json(
        {
            "type": "done",
            "summary": {
                "turns": len(session.turns),
                "arguments_worked": session.arguments_worked,
                "arguments_rejected": session.arguments_rejected,
            },
        }
    )


async def _type_out(websocket: WebSocket, text: str, speed: float = 0.012) -> None:
    """The visitor types, so the reader can follow along."""
    for index, char in enumerate(text):
        await websocket.send_json({"type": "typing", "text": char})
        if char in ".,!? " and index % 8 == 0:
            await asyncio.sleep(speed * 8)
        else:
            await asyncio.sleep(speed)


# ----------------------------------------------------------------------
# Static
# ----------------------------------------------------------------------

class NoCacheStaticFiles(StaticFiles):
    """Static files that are never cached.

    The interface changes while the lab is running, and a cached script is
    a confusing way to lose an afternoon.
    """

    def file_response(self, *args: Any, **kwargs: Any) -> Any:
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return response


static_dir = GUI_DIR / "static"
if static_dir.exists():
    app.mount("/static", NoCacheStaticFiles(directory=static_dir), name="static")
