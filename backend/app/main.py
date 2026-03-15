from fastapi import Depends, FastAPI, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import get_db
from app.api import auth, dashboard, stations, tickets, tasks, chat, users, notifications, attachments, reports, board
from app.api.chat_ws import handle_ws_chat

app = FastAPI(
    title="CRM АЗС Backend",
    version="0.1.0",
    description="Backend CRM для сети АЗС и офиса заявок/задач.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Все API под /api (nginx передаёт полный URI: /api/... -> backend /api/...)
app.include_router(auth.router, prefix="/api")
app.include_router(stations.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(attachments.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(board.router, prefix="/api")


@app.websocket("/ws/chat/{chat_id}")
async def websocket_chat(
    websocket: WebSocket,
    chat_id: int,
    token: str | None = Query(None),
):
    await handle_ws_chat(websocket, chat_id, token)


@app.get("/health", tags=["system"])
def health_check(db=Depends(get_db)) -> dict:
    from sqlalchemy import text
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok", "app": settings.project_name, "db": db_status}
