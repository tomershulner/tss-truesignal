from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.message import Message
from app.models.session import Session, SessionMessage, SessionUser
from app.models.user import User
from app.repositories import message_repo, session_repo, user_repo

router = APIRouter()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserRow(BaseModel):
    user_id: int
    external_id: str | None
    vibe_score: float
    created_at: str


class UsersResponse(BaseModel):
    rows: list[UserRow]
    total: int


class UpdateVibeBody(BaseModel):
    vibe_score: float


@router.get("/api/v1/admin/users", response_model=UsersResponse)
async def admin_list_users(db: AsyncSession = Depends(get_db)):
    users = await user_repo.list_users(db)
    rows = [
        UserRow(
            user_id=u.user_id,
            external_id=u.external_id,
            vibe_score=u.vibe_score,
            created_at=u.created_at.isoformat(),
        )
        for u in users
    ]
    return UsersResponse(rows=rows, total=len(rows))


class UpdateUserBody(BaseModel):
    vibe_score: float | None = None
    external_id: str | None = None


@router.patch("/api/v1/admin/users/{user_id}", response_model=UserRow)
async def admin_update_user(user_id: int, body: UpdateUserBody, db: AsyncSession = Depends(get_db)):
    user = await user_repo.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.vibe_score is not None:
        user.vibe_score = body.vibe_score
    if body.external_id is not None:
        user.external_id = body.external_id
    await db.commit()
    await db.refresh(user)
    return UserRow(
        user_id=user.user_id,
        external_id=user.external_id,
        vibe_score=user.vibe_score,
        created_at=user.created_at.isoformat(),
    )


@router.post("/api/v1/admin/users", response_model=UserRow, status_code=201)
async def admin_create_user(db: AsyncSession = Depends(get_db)):
    user = await user_repo.create_user(db)
    await db.commit()
    await db.refresh(user)
    return UserRow(
        user_id=user.user_id,
        external_id=user.external_id,
        vibe_score=user.vibe_score,
        created_at=user.created_at.isoformat(),
    )


@router.delete("/api/v1/admin/users", status_code=204)
async def admin_delete_all_users(db: AsyncSession = Depends(get_db)):
    await db.execute(User.__table__.delete())
    await db.commit()


@router.delete("/api/v1/admin/users/{user_id}", status_code=204)
async def admin_delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await user_repo.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

class MessageRow(BaseModel):
    message_id: int
    vibe_score: float
    content: str
    received_at: str


class MessagesResponse(BaseModel):
    rows: list[MessageRow]
    total: int


class CreateMessageBody(BaseModel):
    content: str


@router.get("/api/v1/admin/messages", response_model=MessagesResponse)
async def admin_list_messages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Message).order_by(Message.received_at.desc()))
    messages = list(result.scalars().all())
    rows = [
        MessageRow(
            message_id=m.message_id,
            vibe_score=m.vibe_score,
            content=m.content,
            received_at=m.received_at.isoformat(),
        )
        for m in messages
    ]
    return MessagesResponse(rows=rows, total=len(rows))


@router.patch("/api/v1/admin/messages/{message_id}", response_model=MessageRow)
async def admin_update_message_vibe(message_id: int, body: UpdateVibeBody, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Message).where(Message.message_id == message_id))
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    message.vibe_score = body.vibe_score
    await db.commit()
    await db.refresh(message)
    return MessageRow(
        message_id=message.message_id,
        vibe_score=message.vibe_score,
        content=message.content,
        received_at=message.received_at.isoformat(),
    )


@router.post("/api/v1/admin/messages", response_model=MessageRow, status_code=201)
async def admin_create_message(body: CreateMessageBody, db: AsyncSession = Depends(get_db)):
    message = await message_repo.insert_message(db, body.content)
    await db.commit()
    await db.refresh(message)
    return MessageRow(
        message_id=message.message_id,
        vibe_score=message.vibe_score,
        content=message.content,
        received_at=message.received_at.isoformat(),
    )


@router.delete("/api/v1/admin/messages/{message_id}", status_code=204)
async def admin_delete_message(message_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Message).where(Message.message_id == message_id))
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    await db.delete(message)
    await db.commit()


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

class SessionRow(BaseModel):
    session_id: str
    status: str
    created_at: str


class SessionsResponse(BaseModel):
    rows: list[SessionRow]
    total: int


@router.get("/api/v1/admin/sessions", response_model=SessionsResponse)
async def admin_list_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).order_by(Session.created_at.desc()))
    sessions = list(result.scalars().all())
    rows = [
        SessionRow(
            session_id=str(s.session_id),
            status=s.status,
            created_at=s.created_at.isoformat(),
        )
        for s in sessions
    ]
    return SessionsResponse(rows=rows, total=len(rows))


@router.post("/api/v1/admin/sessions", response_model=SessionRow, status_code=201)
async def admin_create_session(db: AsyncSession = Depends(get_db)):
    session = await session_repo.create_session(db)
    await db.commit()
    await db.refresh(session)
    return SessionRow(
        session_id=str(session.session_id),
        status=session.status,
        created_at=session.created_at.isoformat(),
    )


@router.delete("/api/v1/admin/sessions/{session_id}", status_code=204)
async def admin_delete_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    session = await session_repo.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()


# ---------------------------------------------------------------------------
# Session Users
# ---------------------------------------------------------------------------

class SessionUserRow(BaseModel):
    session_id: str
    user_id: int
    joined_at: str


class SessionUsersResponse(BaseModel):
    rows: list[SessionUserRow]
    total: int


class CreateSessionUserBody(BaseModel):
    session_id: UUID
    user_id: int


@router.get("/api/v1/admin/session-users", response_model=SessionUsersResponse)
async def admin_list_session_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SessionUser).order_by(SessionUser.joined_at.desc()))
    rows = [
        SessionUserRow(
            session_id=str(r.session_id),
            user_id=r.user_id,
            joined_at=r.joined_at.isoformat(),
        )
        for r in result.scalars().all()
    ]
    return SessionUsersResponse(rows=rows, total=len(rows))


@router.delete("/api/v1/admin/session-users/{session_id}/{user_id}", status_code=204)
async def admin_delete_session_user(session_id: UUID, user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SessionUser).where(
            SessionUser.session_id == session_id,
            SessionUser.user_id == user_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Session user not found")
    await db.delete(row)
    await db.commit()


@router.post("/api/v1/admin/session-users", response_model=SessionUserRow, status_code=201)
async def admin_create_session_user(body: CreateSessionUserBody, db: AsyncSession = Depends(get_db)):
    session = await session_repo.get_session(db, body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    user = await user_repo.get_user_by_id(db, body.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await session_repo.add_session_users(db, body.session_id, [body.user_id])
    await db.commit()
    result = await db.execute(
        select(SessionUser).where(
            SessionUser.session_id == body.session_id,
            SessionUser.user_id == body.user_id,
        )
    )
    row = result.scalar_one()
    return SessionUserRow(
        session_id=str(row.session_id),
        user_id=row.user_id,
        joined_at=row.joined_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Session Messages
# ---------------------------------------------------------------------------

class SessionMessageRow(BaseModel):
    id: int
    session_id: str
    user_id: int
    content: str
    sent_at: str


class SessionMessagesResponse(BaseModel):
    rows: list[SessionMessageRow]
    total: int


class CreateSessionMessageBody(BaseModel):
    session_id: UUID
    user_id: int
    content: str


@router.get("/api/v1/admin/session-messages", response_model=SessionMessagesResponse)
async def admin_list_session_messages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SessionMessage).order_by(SessionMessage.sent_at.desc()))
    rows = [
        SessionMessageRow(
            id=r.id,
            session_id=str(r.session_id),
            user_id=r.user_id,
            content=r.content,
            sent_at=r.sent_at.isoformat(),
        )
        for r in result.scalars().all()
    ]
    return SessionMessagesResponse(rows=rows, total=len(rows))


@router.delete("/api/v1/admin/session-messages/{id}", status_code=204)
async def admin_delete_session_message(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SessionMessage).where(SessionMessage.id == id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Session message not found")
    await db.delete(row)
    await db.commit()


@router.post("/api/v1/admin/session-messages", response_model=SessionMessageRow, status_code=201)
async def admin_create_session_message(body: CreateSessionMessageBody, db: AsyncSession = Depends(get_db)):
    session = await session_repo.get_session(db, body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    msg = await session_repo.add_session_message(db, body.session_id, body.user_id, body.content)
    await db.commit()
    await db.refresh(msg)
    return SessionMessageRow(
        id=msg.id,
        session_id=str(msg.session_id),
        user_id=msg.user_id,
        content=msg.content,
        sent_at=msg.sent_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Dashboard HTML
# ---------------------------------------------------------------------------

_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TSS Admin</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f4f5f7; color: #2d3748; }
    header { background: #1a202c; color: #fff; padding: 14px 28px; display: flex; align-items: center; justify-content: space-between; }
    header h1 { font-size: 16px; font-weight: 600; letter-spacing: 0.3px; }
    .tag { font-size: 11px; background: #2d3748; padding: 3px 10px; border-radius: 10px; color: #a0aec0; }
    main { padding: 28px; max-width: 1200px; margin: 0 auto; }
    .tabs { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 2px solid #e2e8f0; padding-bottom: 0; }
    .tab-btn { padding: 9px 18px; font-size: 13px; font-weight: 500; color: #718096; background: none; border: none; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; transition: color .15s, border-color .15s; }
    .tab-btn:hover { color: #2d3748; }
    .tab-btn.active { color: #3182ce; border-bottom-color: #3182ce; }
    .tab-panel { display: none; }
    .tab-panel.active { display: block; }
    .card { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.08); overflow: hidden; }
    .card-header { padding: 14px 20px; border-bottom: 1px solid #edf2f7; display: flex; align-items: center; justify-content: space-between; }
    .card-header h2 { font-size: 12px; font-weight: 600; color: #718096; text-transform: uppercase; letter-spacing: 0.6px; }
    .controls { display: flex; align-items: center; gap: 10px; }
    .last-updated { font-size: 11px; color: #a0aec0; }
    .btn { font-size: 12px; padding: 5px 12px; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; cursor: pointer; color: #4a5568; }
    .btn:hover { background: #f7fafc; }
    .btn-primary { background: #3182ce; color: #fff; border-color: #3182ce; }
    .btn-primary:hover { background: #2b6cb0; }
    .btn-sm { padding: 4px 10px; font-size: 11px; }
    .add-form { padding: 16px 20px; background: #f7fafc; border-bottom: 1px solid #edf2f7; display: none; }
    .add-form.open { display: block; }
    .form-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end; }
    .form-field { display: flex; flex-direction: column; gap: 4px; }
    .form-field label { font-size: 11px; font-weight: 600; color: #718096; text-transform: uppercase; letter-spacing: 0.4px; }
    .form-field input { padding: 6px 10px; font-size: 13px; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; color: #2d3748; min-width: 160px; }
    .form-field input:focus { outline: none; border-color: #3182ce; }
    .form-error { font-size: 12px; color: #e53e3e; margin-top: 6px; }
    table { width: 100%; border-collapse: collapse; }
    th { text-align: left; padding: 10px 20px; font-size: 11px; font-weight: 600; color: #a0aec0; text-transform: uppercase; letter-spacing: 0.5px; background: #f7fafc; border-bottom: 1px solid #edf2f7; }
    td { padding: 12px 20px; font-size: 13px; border-bottom: 1px solid #f0f4f8; vertical-align: middle; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #fafcff; }
    .mono { font-family: monospace; font-size: 12px; color: #718096; }
    .truncate { max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
    .badge-active { background: #c6f6d5; color: #276749; }
    .badge-closed { background: #e2e8f0; color: #718096; }
    .vibe { display: inline-block; padding: 3px 9px; border-radius: 12px; font-size: 12px; font-weight: 600; cursor: pointer; }
    .vibe:hover { opacity: 0.8; }
    .vibe-low { background: #c6f6d5; color: #276749; }
    .vibe-mid { background: #feebc8; color: #9c4221; }
    .vibe-high { background: #fed7d7; color: #9b2c2c; }
    .vibe-edit { display: inline-flex; align-items: center; gap: 4px; }
    .vibe-edit input { width: 70px; padding: 2px 6px; font-size: 12px; border: 1px solid #3182ce; border-radius: 6px; outline: none; }
    .vibe-edit button { font-size: 11px; padding: 2px 7px; border: none; border-radius: 5px; cursor: pointer; }
    .vibe-save { background: #3182ce; color: #fff; }
    .vibe-cancel { background: #e2e8f0; color: #4a5568; }
    .empty { text-align: center; padding: 48px; color: #a0aec0; font-size: 13px; }
    .btn-danger { background: #fff5f5; color: #c53030; border-color: #feb2b2; }
    .btn-danger:hover { background: #fed7d7; }
  </style>
</head>
<body>
  <header>
    <h1>TSS Admin</h1>
    <span class="tag">Dashboard</span>
  </header>
  <main>
    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('users')">Users</button>
      <button class="tab-btn" onclick="switchTab('messages')">Messages</button>
      <button class="tab-btn" onclick="switchTab('sessions')">Sessions</button>
      <button class="tab-btn" onclick="switchTab('session-users')">Session Users</button>
      <button class="tab-btn" onclick="switchTab('session-messages')">Session Messages</button>
    </div>

    <!-- USERS -->
    <div class="tab-panel active" id="tab-users">
      <div class="card">
        <div class="card-header">
          <h2>Users</h2>
          <div class="controls">
            <span class="last-updated" id="users-updated"></span>
            <button class="btn btn-primary" onclick="createUser()">+ New User</button>
            <button class="btn btn-danger" onclick="deleteAllUsers()">Delete All</button>
            <button class="btn" onclick="loadUsers()">Refresh</button>
          </div>
        </div>
        <div class="form-error" id="users-error" style="padding:8px 20px;"></div>
        <table>
          <thead><tr><th>ID</th><th>Username</th><th>Vibe Score</th><th>Created At</th><th></th></tr></thead>
          <tbody id="users-tbody"></tbody>
        </table>
      </div>
    </div>

    <!-- MESSAGES -->
    <div class="tab-panel" id="tab-messages">
      <div class="card">
        <div class="card-header">
          <h2>Messages</h2>
          <div class="controls">
            <span class="last-updated" id="messages-updated"></span>
            <button class="btn" onclick="toggleAdd('messages')">+ Add</button>
            <button class="btn" onclick="loadMessages()">Refresh</button>
          </div>
        </div>
        <div class="add-form" id="messages-add-form">
          <div class="form-row">
            <div class="form-field">
              <label>Content</label>
              <input id="messages-content" placeholder="Message text" />
            </div>
            <button class="btn btn-primary btn-sm" onclick="createMessage()">Create</button>
          </div>
          <div class="form-error" id="messages-error"></div>
        </div>
        <table>
          <thead><tr><th>ID</th><th>Vibe Score</th><th>Content</th><th>Received At</th><th></th></tr></thead>
          <tbody id="messages-tbody"></tbody>
        </table>
      </div>
    </div>

    <!-- SESSIONS -->
    <div class="tab-panel" id="tab-sessions">
      <div class="card">
        <div class="card-header">
          <h2>Sessions</h2>
          <div class="controls">
            <span class="last-updated" id="sessions-updated"></span>
            <button class="btn" onclick="createSession()">+ New Session</button>
            <button class="btn" onclick="loadSessions()">Refresh</button>
          </div>
        </div>
        <div class="form-error" id="sessions-error" style="padding:8px 20px;"></div>
        <table>
          <thead><tr><th>Session ID</th><th>Status</th><th>Created At</th><th></th></tr></thead>
          <tbody id="sessions-tbody"></tbody>
        </table>
      </div>
    </div>

    <!-- SESSION USERS -->
    <div class="tab-panel" id="tab-session-users">
      <div class="card">
        <div class="card-header">
          <h2>Session Users</h2>
          <div class="controls">
            <span class="last-updated" id="session-users-updated"></span>
            <button class="btn" onclick="toggleAdd('session-users')">+ Add</button>
            <button class="btn" onclick="loadSessionUsers()">Refresh</button>
          </div>
        </div>
        <div class="add-form" id="session-users-add-form">
          <div class="form-row">
            <div class="form-field"><label>Session ID</label><input id="su-session-id" placeholder="uuid" /></div>
            <div class="form-field"><label>User ID</label><input id="su-user-id" type="number" placeholder="1" /></div>
            <button class="btn btn-primary btn-sm" onclick="createSessionUser()">Add</button>
          </div>
          <div class="form-error" id="session-users-error"></div>
        </div>
        <table>
          <thead><tr><th>Session ID</th><th>User ID</th><th>Joined At</th><th></th></tr></thead>
          <tbody id="session-users-tbody"></tbody>
        </table>
      </div>
    </div>

    <!-- SESSION MESSAGES -->
    <div class="tab-panel" id="tab-session-messages">
      <div class="card">
        <div class="card-header">
          <h2>Session Messages</h2>
          <div class="controls">
            <span class="last-updated" id="session-messages-updated"></span>
            <button class="btn" onclick="toggleAdd('session-messages')">+ Add</button>
            <button class="btn" onclick="loadSessionMessages()">Refresh</button>
          </div>
        </div>
        <div class="add-form" id="session-messages-add-form">
          <div class="form-row">
            <div class="form-field"><label>Session ID</label><input id="sm-session-id" placeholder="uuid" /></div>
            <div class="form-field"><label>User ID</label><input id="sm-user-id" type="number" placeholder="1" /></div>
            <div class="form-field"><label>Content</label><input id="sm-content" placeholder="Message text" /></div>
            <button class="btn btn-primary btn-sm" onclick="createSessionMessage()">Add</button>
          </div>
          <div class="form-error" id="session-messages-error"></div>
        </div>
        <table>
          <thead><tr><th>ID</th><th>Session ID</th><th>User ID</th><th>Content</th><th>Sent At</th><th></th></tr></thead>
          <tbody id="session-messages-tbody"></tbody>
        </table>
      </div>
    </div>
  </main>

  <script>
    function switchTab(name) {
      document.querySelectorAll('.tab-btn').forEach((b, i) => {
        const tabs = ['users','messages','sessions','session-users','session-messages'];
        b.classList.toggle('active', tabs[i] === name);
      });
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      document.getElementById('tab-' + name).classList.add('active');
      ({ users: loadUsers, messages: loadMessages, sessions: loadSessions,
         'session-users': loadSessionUsers, 'session-messages': loadSessionMessages })[name]?.();
    }

    function toggleAdd(tab) {
      document.getElementById(tab + '-add-form').classList.toggle('open');
    }

    function ts(id) { document.getElementById(id).textContent = 'Updated ' + new Date().toLocaleTimeString(); }
    function err(id, msg) { document.getElementById(id).textContent = msg || ''; }

    function vibeBadge(v, entity, id) {
      const cls = v < 30 ? 'vibe-low' : v < 60 ? 'vibe-mid' : 'vibe-high';
      return `<span class="vibe ${cls}" onclick="editVibe(this,'${entity}',${id},${v})">${v.toFixed(1)}</span>`;
    }

    function editVibe(el, entity, id, current) {
      el.parentElement.innerHTML = `<span class="vibe-edit">
        <input type="number" step="0.1" value="${current}" id="vi-${entity}-${id}" />
        <button class="vibe-save" onclick="saveVibe('${entity}',${id})">Save</button>
        <button class="vibe-cancel" onclick="${entity === 'user' ? 'loadUsers' : 'loadMessages'}()">✕</button>
      </span>`;
      document.getElementById(`vi-${entity}-${id}`).focus();
    }

    async function saveVibe(entity, id) {
      const value = parseFloat(document.getElementById(`vi-${entity}-${id}`).value);
      if (isNaN(value)) return;
      try {
        await apiFetch(`/api/v1/admin/${entity}s/${id}`, {
          method: 'PATCH', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ vibe_score: value })
        });
        entity === 'user' ? loadUsers() : loadMessages();
      } catch(e) { alert(e.message); }
    }

    function emptyRow(cols, msg) {
      return `<tr><td colspan="${cols}" class="empty">${msg}</td></tr>`;
    }

    async function apiFetch(url, opts) {
      const res = await fetch(url, opts);
      if (res.status === 204) return null;
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Request failed');
      return data;
    }

    async function deleteRow(url, reload) {
      if (!confirm('Delete this row?')) return;
      try {
        await apiFetch(url, { method: 'DELETE' });
        reload();
      } catch(e) { alert(e.message); }
    }

    async function loadUsers() {
      const data = await apiFetch('/api/v1/admin/users');
      ts('users-updated');
      document.getElementById('users-tbody').innerHTML = data.rows.length
        ? data.rows.map(r => `<tr>
            <td class="mono">${r.user_id}</td>
            <td id="eid-cell-${r.user_id}"><span class="vibe vibe-low" style="background:#edf2f7;color:#4a5568;" onclick="editExternalId(${r.user_id},'${r.external_id ?? ''}')">${r.external_id ?? '—'}</span></td>
            <td>${vibeBadge(r.vibe_score, 'user', r.user_id)}</td>
            <td class="mono">${r.created_at}</td>
            <td><button class="btn btn-sm btn-danger" onclick="deleteRow('/api/v1/admin/users/${r.user_id}', loadUsers)">Delete</button></td>
          </tr>`).join('')
        : emptyRow(5, 'No users yet');
    }

    function editExternalId(userId, current) {
      const cell = document.getElementById('eid-cell-' + userId);
      cell.innerHTML = `<span class="vibe-edit">
        <input type="text" value="${current}" id="eid-input-${userId}" style="min-width:120px;" />
        <button class="vibe-save" onclick="saveExternalId(${userId})">Save</button>
        <button class="vibe-cancel" onclick="loadUsers()">✕</button>
      </span>`;
      document.getElementById('eid-input-' + userId).focus();
    }

    async function saveExternalId(userId) {
      const value = document.getElementById('eid-input-' + userId).value.trim();
      try {
        await apiFetch(`/api/v1/admin/users/${userId}`, {
          method: 'PATCH', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ external_id: value || null })
        });
        loadUsers();
      } catch(e) { alert(e.message); }
    }

    async function deleteAllUsers() {
      if (!confirm('Delete ALL users? This cannot be undone.')) return;
      try {
        await apiFetch('/api/v1/admin/users', { method: 'DELETE' });
        loadUsers();
      } catch(e) { err('users-error', e.message); }
    }

    async function createUser() {
      err('users-error');
      try {
        await apiFetch('/api/v1/admin/users', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' });
        loadUsers();
      } catch(e) { err('users-error', e.message); }
    }

    async function loadMessages() {
      const data = await apiFetch('/api/v1/admin/messages');
      ts('messages-updated');
      document.getElementById('messages-tbody').innerHTML = data.rows.length
        ? data.rows.map(r => `<tr>
            <td class="mono">#${r.message_id}</td>
            <td>${vibeBadge(r.vibe_score, 'message', r.message_id)}</td>
            <td class="truncate">${r.content}</td>
            <td class="mono">${r.received_at}</td>
            <td><button class="btn btn-sm btn-danger" onclick="deleteRow('/api/v1/admin/messages/${r.message_id}', loadMessages)">Delete</button></td>
          </tr>`).join('')
        : emptyRow(5, 'No messages yet');
    }

    async function createMessage() {
      err('messages-error');
      try {
        const content = document.getElementById('messages-content').value.trim();
        if (!content) { err('messages-error', 'Content is required'); return; }
        await apiFetch('/api/v1/admin/messages', {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ content })
        });
        document.getElementById('messages-content').value = '';
        document.getElementById('messages-add-form').classList.remove('open');
        loadMessages();
      } catch(e) { err('messages-error', e.message); }
    }

    async function loadSessions() {
      const data = await apiFetch('/api/v1/admin/sessions');
      ts('sessions-updated');
      document.getElementById('sessions-tbody').innerHTML = data.rows.length
        ? data.rows.map(r => `<tr>
            <td class="mono truncate">${r.session_id}</td>
            <td><span class="badge badge-${r.status}">${r.status}</span></td>
            <td class="mono">${r.created_at}</td>
            <td>${r.status === 'active' ? `<button class="btn btn-sm" onclick="closeSession('${r.session_id}')">Close</button>` : ''}</td>
          </tr>`).join('')
        : emptyRow(4, 'No sessions yet');
    }

    async function createSession() {
      err('sessions-error');
      try {
        await apiFetch('/api/v1/admin/sessions', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' });
        loadSessions();
      } catch(e) { err('sessions-error', e.message); }
    }

    async function closeSession(session_id) {
      err('sessions-error');
      try {
        await apiFetch(`/${session_id}/close`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' });
        loadSessions();
      } catch(e) { err('sessions-error', e.message); }
    }

    async function loadSessionUsers() {
      const data = await apiFetch('/api/v1/admin/session-users');
      ts('session-users-updated');
      document.getElementById('session-users-tbody').innerHTML = data.rows.length
        ? data.rows.map(r => `<tr>
            <td class="mono truncate">${r.session_id}</td>
            <td class="mono">${r.user_id}</td>
            <td class="mono">${r.joined_at}</td>
            <td><button class="btn btn-sm btn-danger" onclick="deleteRow('/api/v1/admin/session-users/${r.session_id}/${r.user_id}', loadSessionUsers)">Delete</button></td>
          </tr>`).join('')
        : emptyRow(4, 'No session users yet');
    }

    async function createSessionUser() {
      err('session-users-error');
      try {
        const session_id = document.getElementById('su-session-id').value.trim();
        const user_id = parseInt(document.getElementById('su-user-id').value);
        if (!session_id || !user_id) { err('session-users-error', 'All fields required'); return; }
        await apiFetch('/api/v1/admin/session-users', {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ session_id, user_id })
        });
        document.getElementById('su-session-id').value = '';
        document.getElementById('su-user-id').value = '';
        document.getElementById('session-users-add-form').classList.remove('open');
        loadSessionUsers();
      } catch(e) { err('session-users-error', e.message); }
    }

    async function loadSessionMessages() {
      const data = await apiFetch('/api/v1/admin/session-messages');
      ts('session-messages-updated');
      document.getElementById('session-messages-tbody').innerHTML = data.rows.length
        ? data.rows.map(r => `<tr>
            <td class="mono">${r.id}</td>
            <td class="mono truncate">${r.session_id}</td>
            <td class="mono">${r.user_id}</td>
            <td class="truncate">${r.content}</td>
            <td class="mono">${r.sent_at}</td>
            <td><button class="btn btn-sm btn-danger" onclick="deleteRow('/api/v1/admin/session-messages/${r.id}', loadSessionMessages)">Delete</button></td>
          </tr>`).join('')
        : emptyRow(6, 'No session messages yet');
    }

    async function createSessionMessage() {
      err('session-messages-error');
      try {
        const session_id = document.getElementById('sm-session-id').value.trim();
        const user_id = parseInt(document.getElementById('sm-user-id').value);
        const content = document.getElementById('sm-content').value.trim();
        if (!session_id || !user_id || !content) { err('session-messages-error', 'All fields required'); return; }
        await apiFetch('/api/v1/admin/session-messages', {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ session_id, user_id, content })
        });
        document.getElementById('sm-session-id').value = '';
        document.getElementById('sm-user-id').value = '';
        document.getElementById('sm-content').value = '';
        document.getElementById('session-messages-add-form').classList.remove('open');
        loadSessionMessages();
      } catch(e) { err('session-messages-error', e.message); }
    }

    loadUsers();
  </script>
</body>
</html>"""


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_dashboard():
    return _DASHBOARD_HTML
