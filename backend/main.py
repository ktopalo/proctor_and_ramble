import asyncio
import logging
import os
from typing import Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.config import load_config
from backend.session.manager import SessionManager
from backend.session.models import Interjection, TranscriptChunk
from backend.engines.openai_client import OpenAIClient
from backend.engines.codex_cli_client import CodexCLIClient
from backend.engines.llm_base import BaseLLMClient
from backend.engines.stt_base import BaseSTTEngine
from backend.engines.mlx_whisper import MLXWhisperEngine
from backend.question.loader import load_question
from backend.watcher.file_watcher import FileWatcher
from backend.agent.loop import AgentLoop

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

config = load_config()
manager = SessionManager()


def _build_llm() -> BaseLLMClient:
    if config.llm.provider == "codex_cli":
        log.info("LLM provider: codex_cli  model=%s", config.llm.model)
        return CodexCLIClient(
            model=config.llm.model,
            codex_path=config.llm.codex_path,
        )
    log.info("LLM provider: openai  model=%s", config.llm.model)
    return OpenAIClient(model=config.llm.model, api_key=os.environ.get("OPENAI_API_KEY"))


llm = _build_llm()

_file_watcher: FileWatcher | None = None
_agent_loop: AgentLoop | None = None
_stt_engine: BaseSTTEngine | None = None


def _build_stt() -> BaseSTTEngine:
    if config.stt.engine == "mlx_whisper":
        return MLXWhisperEngine(
            model=config.stt.model,
            pause_threshold_seconds=config.stt.speech_pause_threshold_seconds,
        )
    raise ValueError(f"Unknown STT engine: {config.stt.engine}")


async def _handle_transcript_chunk(chunk: TranscriptChunk) -> None:
    manager.add_transcript_chunk(chunk)
    await connection_manager.broadcast({
        "type": "transcript_chunk",
        "data": chunk.model_dump(mode="json"),
    })


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        log.info("WS connected  clients=%d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            log.info("WS disconnected  clients=%d", len(self.active_connections))

    async def broadcast(self, message: dict[str, Any]):
        for ws in list(self.active_connections):
            try:
                await ws.send_json(message)
            except Exception:
                log.warning("WS send failed, dropping client  type=%s", message.get("type"))
                self.disconnect(ws)


connection_manager = ConnectionManager()


async def _on_interjection(interjection: Interjection):
    await connection_manager.broadcast({
        "type": "interjection",
        "data": interjection.model_dump(mode="json"),
    })


app = FastAPI(title="Proctor & Ramble")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


class LoadQuestionRequest(BaseModel):
    url: str


@app.post("/question/load")
async def load_question_endpoint(req: LoadQuestionRequest):
    log.info("Loading question  url=%s", req.url)
    plan = await load_question(req.url, llm)
    manager.set_plan(plan)
    log.info("Question loaded  problem=%s", plan.problem_statement[:80])
    await connection_manager.broadcast({
        "type": "plan_loaded",
        "data": plan.model_dump(mode="json"),
    })
    return {"status": "ok", "plan": plan.model_dump(mode="json")}


class StartSessionRequest(BaseModel):
    watch_path: str


@app.post("/session/start")
async def start_session(req: StartSessionRequest):
    global _file_watcher, _agent_loop, _stt_engine

    log.info("Session starting  watch_path=%s", req.watch_path)
    manager.start(watch_path=req.watch_path)

    _agent_loop = AgentLoop(
        session=manager,
        llm=llm,
        min_interjection_gap_seconds=config.agent.min_seconds_between_interjections,
        on_interjection=lambda i: asyncio.ensure_future(_on_interjection(i)),
    )

    _file_watcher = FileWatcher(
        path=req.watch_path,
        on_delta=_handle_file_delta,
    )
    _file_watcher.start()

    _stt_engine = _build_stt()
    _stt_engine.set_on_transcript(_handle_transcript_chunk)
    _stt_engine.set_on_speech_pause(_agent_loop.on_speech_pause)
    _stt_engine.start()
    log.info("Session started  stt=%s", config.stt.engine)

    await connection_manager.broadcast({"type": "session_started", "data": {}})
    return {"status": "started"}


async def _handle_file_delta(delta):
    manager.add_file_delta(delta)
    await connection_manager.broadcast({
        "type": "file_delta",
        "data": delta.model_dump(mode="json"),
    })
    if _agent_loop:
        await _agent_loop.on_file_save()


@app.post("/session/end")
async def end_session():
    global _file_watcher, _stt_engine
    if _stt_engine:
        _stt_engine.stop()
        _stt_engine = None
    if _file_watcher:
        _file_watcher.stop()
        _file_watcher = None
    manager.end()
    snap = manager.snapshot
    log.info(
        "Session ended  transcript_chunks=%d  file_deltas=%d  interjections=%d",
        len(snap.transcript), len(snap.deltas), len(snap.interjections),
    )
    await connection_manager.broadcast({"type": "session_ended", "data": {}})
    return {"status": "ended"}


@app.get("/session/snapshot")
async def get_snapshot():
    return manager.snapshot.model_dump(mode="json")


@app.post("/session/feedback")
async def generate_feedback():
    snap = manager.snapshot
    if not snap.plan:
        log.warning("Feedback requested but no plan loaded")
        raise HTTPException(status_code=400, detail="No interview plan loaded")
    log.info("Generating feedback  transcript_chunks=%d  deltas=%d", len(snap.transcript), len(snap.deltas))

    transcript_text = " ".join(c.text for c in snap.transcript)
    diffs_text = "\n".join(d.diff for d in snap.deltas)
    interjections_text = "\n".join(f"- {i.text}" for i in snap.interjections)
    rubric_text = "\n".join(f"{k}: {v}" for k, v in snap.plan.rubric.items())

    prompt = f"""You are reviewing a technical interview. Evaluate the candidate on each rubric dimension.

PROBLEM: {snap.plan.problem_statement}

RUBRIC:
{rubric_text}

TRANSCRIPT:
{transcript_text}

CODE CHANGES:
{diffs_text}

PROCTOR INTERJECTIONS (hints given):
{interjections_text}

Provide structured feedback: strengths, areas for improvement, and a rating (1-5) per rubric dimension."""

    feedback_text = await llm.complete(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are a senior technical interviewer providing constructive, honest feedback.",
    )
    log.info("Feedback generated  chars=%d", len(feedback_text))
    return {"feedback": feedback_text}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
