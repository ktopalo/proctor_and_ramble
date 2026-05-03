import asyncio
import os
from typing import Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.config import load_config
from backend.session.manager import SessionManager
from backend.session.models import Interjection
from backend.engines.openai_client import OpenAIClient
from backend.question.loader import load_question
from backend.watcher.file_watcher import FileWatcher
from backend.agent.loop import AgentLoop

load_dotenv()

config = load_config()
manager = SessionManager()
llm = OpenAIClient(model=config.llm.model, api_key=os.environ.get("OPENAI_API_KEY"))

_file_watcher: FileWatcher | None = None
_agent_loop: AgentLoop | None = None


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]):
        for ws in list(self.active_connections):
            try:
                await ws.send_json(message)
            except Exception:
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
    plan = await load_question(req.url, llm)
    manager.set_plan(plan)
    await connection_manager.broadcast({
        "type": "plan_loaded",
        "data": plan.model_dump(mode="json"),
    })
    return {"status": "ok", "plan": plan.model_dump(mode="json")}


class StartSessionRequest(BaseModel):
    watch_path: str


@app.post("/session/start")
async def start_session(req: StartSessionRequest):
    global _file_watcher, _agent_loop

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
    global _file_watcher
    if _file_watcher:
        _file_watcher.stop()
        _file_watcher = None
    manager.end()
    await connection_manager.broadcast({"type": "session_ended", "data": {}})
    return {"status": "ended"}


@app.get("/session/snapshot")
async def get_snapshot():
    return manager.snapshot.model_dump(mode="json")


@app.post("/session/feedback")
async def generate_feedback():
    snap = manager.snapshot
    if not snap.plan:
        raise HTTPException(status_code=400, detail="No interview plan loaded")

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
    return {"feedback": feedback_text}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
