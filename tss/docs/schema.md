# Database Schema

Two tables: `users` and `messages`.

## `users`

| Column | Type | Notes |
|---|---|---|
| `user_id` | `BIGINT GENERATED ALWAYS AS IDENTITY` PK | |
| `external_id` | `TEXT NOT NULL UNIQUE` | caller-supplied identity |
| `vibe_score` | `DOUBLE PRECISION NOT NULL DEFAULT 0.0` | set externally |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |
| `updated_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |

## `messages`

| Column | Type | Notes |
|---|---|---|
| `message_id` | `BIGINT GENERATED ALWAYS AS IDENTITY` PK | |
| `user_id` | `BIGINT NOT NULL REFERENCES users(user_id)` | |
| `vibe_score` | `DOUBLE PRECISION NOT NULL DEFAULT 0.0` | snapshot of user's score at send time |
| `payload` | `JSONB NOT NULL` | nonverbal content |
| `received_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |
| `client_ts` | `TIMESTAMPTZ` | optional client-supplied timestamp |

## Relationships

Each `messages` row belongs to one `users` row via `user_id`.

## `vibe_score` write pattern

- **`users.vibe_score`** is written externally (e.g. by a scoring service). It represents the user's current vibe score.
- **`messages.vibe_score`** is a snapshot of the user's `vibe_score` at the time the message was received. This allows historical analysis without recomputing scores.
