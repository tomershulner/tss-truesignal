# TSS — Toxicity Scoring System

TSS is a FastAPI backend that tracks message toxicity across live sessions. Users are grouped into sessions, send messages, and each message accumulates a **vibe score** — a toxicity signal derived from the vibe scores of the users who sent that content. When a session closes, the scores are reconciled and the session tables are cleared.

---

## Quick Start

```bash
# Start the database
docker compose up -d

# Apply migrations
cd tss
alembic upgrade head

# Run the API
uvicorn app.main:app --reload

# Verify
curl http://localhost:8000/health
```

---

## How It Works

### Core concepts

**Users** — each user has a `vibe_score` (0–100) representing their personal toxicity level. Scores are set externally (e.g. via the admin panel or a classifier).

**Sessions** — a live grouping of users. A session is either `active` or `closed`. Messages can only be sent to active sessions.

**Messages (knowledge base)** — the `messages` table is a content-keyed store. Each unique piece of content has exactly one row, and its `vibe_score` is the aggregate toxicity of that content based on who has sent it historically.

**Session Messages** — the `session_messages` table is the transient inbox for an active session. It holds every message sent during the session and is cleared when the session closes.

### Session lifecycle

```
1. POST /session/create           → session created, status = "active"
2. POST /{session_id}/users       → users registered into the session (async)
3. POST /{session_id}/message     → messages sent; stored in session_messages,
                                    existing vibe_score from messages table returned (or null)
4. POST /{session_id}/close       → session marked "closed", background task fires:
                                      - groups session_messages by unique content
                                      - for each unique content, averages the vibe_scores
                                        of the distinct users who sent it
                                      - upserts into messages: new vibe_score = avg(existing, new)
                                      - deletes all session_messages and session_users for this session
```

### Vibe score update formula

When a session closes, for each unique message content:

```
sender_avg  = average vibe_score of distinct users who sent that content
final_score = (existing_message_vibe_score + sender_avg) / 2   # if content already known
            = sender_avg                                         # if content is new
```

This means repeated appearances of toxic content from toxic users gradually push the message's score up, while benign senders pull it down over time.

---

## API Reference

### Health

```
GET /health

Response 200:
{ "status": "ok", "db": "ok" }
```

---

### Sessions

#### Create a session

```
POST /session/create

Response 201:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-03-20T12:00:00Z",
  "status": "active"
}
```

#### Register users into a session

Accepts up to 100 user IDs. Returns 202 immediately; the actual DB writes happen in a background task.

```
POST /{session_id}/users

Request:
{ "user_ids": [1, 2, 3] }

Response 202:
{
  "accepted": true,
  "session_id": "550e8400-...",
  "user_count": 3
}

Errors:
  404 — session not found
  422 — more than 100 user_ids provided
```

#### Send a message in a session

The message is stored in `session_messages`. The response includes the content's existing vibe score from the knowledge base (`null` if the content has never been seen before).

```
POST /{session_id}/message

Request:
{ "user_id": 1, "content": "hello world" }

Response 200:
{
  "id": 42,
  "vibe_score": 15.3   // null if content not yet in messages table
}

Errors:
  404 — session not found or not active
  404 — user not in session
```

#### Close a session

Marks the session as closed and triggers background processing: vibe scores are reconciled into the `messages` table, then `session_messages` and `session_users` for this session are deleted.

```
POST /{session_id}/close

Response 200:
{ "session_id": "550e8400-..." }

Errors:
  404 — session not found
```

---

### Users

#### List all users

```
GET /api/v1/users

Response 200:
{
  "users": [
    { "user_id": 1, "vibe_score": 42.0, "created_at": "...", "updated_at": "..." }
  ],
  "total": 1
}
```

#### Bulk create users

Creates `count` new users with default vibe score 0.

```
POST /api/v1/users/bulk

Request:
{ "count": 10 }

Response 200:
{
  "users": [ { "user_id": 1, ... }, ... ],
  "total": 10,
  "created": 10
}
```

#### Get a user's vibe score

```
GET /api/v1/users/{user_id}/vibe-score

Response 200:
{ "user_id": 1, "vibe_score": 42.0, "scores": {} }

Errors:
  404 — user not found
```

---

### Messages (knowledge base)

#### List messages

```
GET /api/v1/messages?limit=20&offset=0

Response 200:
{
  "items": [
    { "message_id": 1, "content": "hello", "vibe_score": 15.3, "received_at": "..." }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

#### Get a single message

```
GET /api/v1/messages/{message_id}

Response 200:
{ "message_id": 1, "content": "hello", "vibe_score": 15.3, "received_at": "..." }

Errors:
  404 — message not found
```

#### Ingest a message (direct, outside a session)

Requires `X-tss-user-id` header. Inserts into the `messages` knowledge base directly and runs the classifier pipeline.

```
POST /api/v1/messages
X-tss-user-id: 1

Request:
{ "content": "hello world" }

Response 201:
{
  "message_id": 42,
  "user_id": 1,
  "vibe_score": 15.3
}

Errors:
  404 — user not found
```

---

### Admin

#### Dashboard

```
GET /admin   → HTML admin panel
```

The dashboard has tabs for each table. Every tab supports creating, editing, and deleting rows.

#### Users

```
GET    /api/v1/admin/users              — list all users
POST   /api/v1/admin/users              — create a user
PATCH  /api/v1/admin/users/{user_id}    — update vibe_score
DELETE /api/v1/admin/users/{user_id}    — delete user
```

#### Messages

```
GET    /api/v1/admin/messages                 — list all messages
POST   /api/v1/admin/messages                 — create a message  { "content": "..." }
PATCH  /api/v1/admin/messages/{message_id}    — update vibe_score { "vibe_score": 50.0 }
DELETE /api/v1/admin/messages/{message_id}    — delete message
```

#### Sessions

```
GET    /api/v1/admin/sessions                 — list all sessions
POST   /api/v1/admin/sessions                 — create a session
DELETE /api/v1/admin/sessions/{session_id}    — delete session
```

#### Session Users

```
GET    /api/v1/admin/session-users                          — list all session-user links
POST   /api/v1/admin/session-users                          — add user to session  { "session_id": "...", "user_id": 1 }
DELETE /api/v1/admin/session-users/{session_id}/{user_id}   — remove user from session
```

#### Session Messages

```
GET    /api/v1/admin/session-messages         — list all session messages
POST   /api/v1/admin/session-messages         — add a message  { "session_id": "...", "user_id": 1, "content": "..." }
DELETE /api/v1/admin/session-messages/{id}    — delete session message
```

---

## Database Schema

```
sessions
  session_id   UUID           PK
  status       TEXT           "active" | "closed"
  created_at   TIMESTAMPTZ

session_users
  session_id   UUID FK → sessions
  user_id      BIGINT FK → users
  joined_at    TIMESTAMPTZ

session_messages
  id           BIGINT         PK (identity)
  session_id   UUID FK → sessions
  user_id      BIGINT FK → users
  content      TEXT
  sent_at      TIMESTAMPTZ

users
  user_id      BIGINT         PK (identity)
  vibe_score   DOUBLE         default 0.0
  created_at   TIMESTAMPTZ
  updated_at   TIMESTAMPTZ

messages
  message_id   BIGINT         PK (identity)
  content      TEXT           UNIQUE
  vibe_score   DOUBLE         default 0.0
  received_at  TIMESTAMPTZ
```

---

## Architecture

```
app/
  routers/        FastAPI route handlers (sessions, users, messages, admin, health)
  repositories/   Raw async SQLAlchemy queries
  services/       Business logic (MessageService, classification, session cache)
  models/         SQLAlchemy ORM models
  schemas/        Pydantic request/response schemas
  classification/ Pluggable classifier interface (swap StubClassifier for a real model)
```

All database access is async (`AsyncSession`). Background tasks are used for non-blocking operations: registering session users and processing session close both run outside the request/response cycle.

---

## Development

```bash
pip install -e ".[dev]"
docker compose up -d db
cd tss && uvicorn app.main:app --reload
pytest
```

### Migrations

```bash
cd tss
alembic upgrade head          # apply all migrations
alembic revision -m "name"    # create a new migration
```
