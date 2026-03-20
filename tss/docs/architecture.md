# TSS Backend Architecture

## System Overview

TSS is a lightweight Python backend that receives a stream of messages from users, classifies them, and maintains per-user "vibe scores" reflecting behavior patterns over time.

**Two message types:**
- **Verbal** — text content classified across bad-behavior dimensions (harmful, hate, sexual_harassment). Classification scores feed a per-user vibe score.
- **Nonverbal** — opaque payloads (reactions, images, stickers) that inherit scores seeded from the sender's current user vibe score.

---

## Technology Stack

| Layer | Choice |
|---|---|
| Framework | FastAPI (async, Pydantic v2, OpenAPI docs) |
| ORM | SQLAlchemy 2.x (async) |
| DB Driver | asyncpg |
| Migrations | Alembic |
| Config | pydantic-settings (.env) |
| Container | Docker + Docker Compose |

---

## Message Flow Diagrams

### Verbal Message Ingestion

```
POST /api/v1/messages/verbal
        │
        ▼
  [MessageService.ingest_verbal]
        │
        ├─▶ UserRepo.upsert_user(external_id)
        │         └─▶ INSERT INTO users ON CONFLICT DO UPDATE
        │
        ├─▶ MessageRepo.insert_verbal_message(user_id, content)
        │         └─▶ INSERT messages (type=verbal)
        │             INSERT verbal_messages (content, language)
        │
        ├─▶ ClassificationService.classify(content)
        │         └─▶ Classifier.classify(content) → ClassificationResult {dim: 0.0–1.0}
        │
        ├─▶ ClassificationRepo.bulk_upsert_scores(message, message_id, scores)
        │         └─▶ INSERT INTO scores ON CONFLICT DO UPDATE
        │
        ├─▶ VerbalMessage.classified_at = now(), classification_raw = raw
        │
        ├─▶ VibeService.recalculate_user_scores(user_id, scores)
        │         └─▶ ClassificationRepo.bulk_upsert_scores(user, user_id, scores)
        │
        └─▶ VibeService.compute_vibe_score(user_scores) → float
              └─▶ weighted average over score_types.weight

Response: {message_id, user_id, message_scores, user_vibe_score}
```

### Nonverbal Message Ingestion

```
POST /api/v1/messages/nonverbal
        │
        ▼
  [MessageService.ingest_nonverbal]
        │
        ├─▶ UserRepo.upsert_user(external_id)
        │
        ├─▶ ClassificationRepo.get_entity_scores(user, user_id)
        │         └─▶ snapshot = {score_type_id: score, ...}
        │
        ├─▶ MessageRepo.insert_nonverbal_message(user_id, payload, snapshot)
        │         └─▶ INSERT messages (type=nonverbal)
        │             INSERT nonverbal_messages (payload, user_scores_snapshot)
        │
        ├─▶ VibeService.score_nonverbal_message(message_id, snapshot)
        │         └─▶ ClassificationRepo.bulk_upsert_scores(message, message_id, snapshot)
        │
        └─▶ VibeService.compute_vibe_score(message_scores) → float

Response: {message_id, user_id, message_vibe_score}
```

---

## Table Schemas

### Enums

```sql
CREATE TYPE message_type AS ENUM ('verbal', 'nonverbal');
CREATE TYPE score_entity_type AS ENUM ('message', 'user');
```

### score_types

Defines scoring dimensions. Both messages and users are scored against these.

```sql
CREATE TABLE score_types (
    score_type_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    description     TEXT,
    weight          DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Seeded with: `harmful`, `hate`, `sexual_harassment` (weight=1.0 each).

### users

```sql
CREATE TABLE users (
    user_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_id     TEXT NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata        JSONB
);
```

### messages

```sql
CREATE TABLE messages (
    message_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(user_id),
    message_type    message_type NOT NULL,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    client_ts       TIMESTAMPTZ,
    metadata        JSONB
);
```

### verbal_messages

```sql
CREATE TABLE verbal_messages (
    verbal_message_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    message_id          BIGINT NOT NULL UNIQUE REFERENCES messages(message_id),
    content             TEXT NOT NULL,
    language            TEXT,
    classified_at       TIMESTAMPTZ,
    classification_raw  JSONB
);
-- Partial index on unclassified messages for future async queue
CREATE INDEX ON verbal_messages (classified_at) WHERE classified_at IS NULL;
```

### nonverbal_messages

```sql
CREATE TABLE nonverbal_messages (
    nonverbal_message_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    message_id              BIGINT NOT NULL UNIQUE REFERENCES messages(message_id),
    payload                 JSONB NOT NULL,
    user_scores_snapshot    JSONB,
    scored_at               TIMESTAMPTZ
);
```

### scores

Single unified scoring table for messages and users.

```sql
CREATE TABLE scores (
    score_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_type     score_entity_type NOT NULL,
    entity_id       BIGINT NOT NULL,
    score_type_id   BIGINT NOT NULL REFERENCES score_types(score_type_id),
    score           INTEGER NOT NULL CHECK (score >= 0 AND score <= 100),
    scored_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (entity_type, entity_id, score_type_id)
);
```

---

## API Reference

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/users/bulk` | Pre-register users at session start (idempotent) |
| POST | `/api/v1/messages/verbal` | Ingest verbal message, classify, update user scores |
| POST | `/api/v1/messages/nonverbal` | Ingest nonverbal message, seed scores from user snapshot |
| GET | `/api/v1/users/{user_id}/vibe-score` | Get materialized user vibe score |
| GET | `/api/v1/users/{user_id}/score-breakdown` | Per-dimension score breakdown with message-level contributions |
| GET | `/api/v1/users/{user_id}/messages` | Paginated message history |
| GET | `/api/v1/messages/{message_id}` | Single message detail |
| GET | `/health` | DB connectivity check |

### Example: POST /api/v1/messages/verbal

Request:
```json
{
  "external_id": "user-abc",
  "content": "hello world",
  "language": "en"
}
```

Response (201):
```json
{
  "message_id": 1,
  "user_id": 1,
  "external_id": "user-abc",
  "message_scores": {"harmful": 23, "hate": 7, "sexual_harassment": 14},
  "user_vibe_score": 14.67
}
```

### Example: POST /api/v1/users/bulk

Pre-registers all session participants. New users are inserted; existing ones are left untouched. Safe to call multiple times with the same list.

Request:
```json
{
  "external_ids": ["player1", "player2", "player3"]
}
```

Response (200):
```json
{
  "users": [
    {"user_id": 1, "external_id": "player1", "created_at": "...", "updated_at": "..."},
    {"user_id": 2, "external_id": "player2", "created_at": "...", "updated_at": "..."},
    {"user_id": 3, "external_id": "player3", "created_at": "...", "updated_at": "..."}
  ],
  "total": 3,
  "created": 3,
  "existing": 0
}
```

### Example: GET /api/v1/users/1/vibe-score

Response:
```json
{
  "user_id": 1,
  "external_id": "user-abc",
  "vibe_score": 14.67,
  "scores": {"harmful": 23, "hate": 7, "sexual_harassment": 14}
}
```

---

## Classification Layer Design

```
app/classification/
├── base.py       BaseClassifier (ABC) + ClassificationResult (dataclass)
├── stub.py       StubClassifier — random scores for dev
└── registry.py   get_classifier() → active classifier instance
```

**`ClassificationResult`** carries:
- `scores: dict[str, float]` — per-dimension scores 0.0–1.0
- `raw: dict` — raw classifier output for storage in `verbal_messages.classification_raw`

**Swapping classifiers** requires only changing `registry.py`. All callers go through `ClassificationService.classify()` and are insulated from the implementation.

**Float → integer mapping:** `ClassificationService.to_integer_scores()` converts 0.0–1.0 → 0–100 (`round(value * 100)`) and maps dimension names to `score_type_id` keys for DB insertion.

---

## Vibe Score Design

Both users and messages share the same score structure: one `scores` row per (entity, score_type), integer 0–100.

### User scores (`entity_type='user'`)

After each verbal message is classified, `VibeService.recalculate_user_scores()` upserts one `scores` row per active `score_type` for the user. Current behavior: scores reflect the most recent verbal message. The scalar vibe score returned in API responses is the weighted average:

```
vibe_score = Σ(score_i × weight_i) / Σ(weight_i)
```

Weights come from `score_types.weight`. Adding a dimension = one INSERT into `score_types`, zero DDL.

### Verbal message scores (`entity_type='message'`)

One row per dimension per message. Set during ingestion from classifier output.

### Nonverbal message scores (`entity_type='message'`)

1. Snapshot sender's current user `scores` rows → stored in `nonverbal_messages.user_scores_snapshot` as `{score_type_id: score}`
2. Insert one `scores` row per dimension, value seeded from the snapshot

The JSONB snapshot ensures nonverbal scores are reproducible even as user scores evolve over time.

---

## Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Message inheritance | `messages` table + two child tables (1:1 FK) | Unified chronological stream; exact-one-child enforced by UNIQUE FK |
| User vibe score | Materialized on write via `scores` table | Reads are frequent; on-the-fly aggregation of all history is unbounded cost |
| Score types | Dedicated `score_types` table with `weight` and `is_active` | Dimensions are first-class; adding a dimension = one INSERT, zero DDL |
| Scores | Single polymorphic `scores` table (entity_type + entity_id) | One unified score model for both messages and users; SQL-queryable by entity and dimension |
| Classification | Synchronous stub, async-ready schema | Simple first; `classified_at IS NULL` partial index supports a future async queue |
| User identity | `external_id` TEXT as caller-supplied ID | Server doesn't own auth; internal `user_id` BIGINT is stable PK |
| Auth | None in v1 | Add API key middleware as a single `Depends` when needed; schema unaffected |
| Score integer range | 0–100 | Human-readable, SQL-aggregatable, no float precision issues |

---

## Running Locally

```bash
# Start the stack
cd tss
cp .env.example .env
docker compose up

# Run migrations (first time)
docker compose exec api alembic upgrade head

# Verify
curl http://localhost:8000/health
```
