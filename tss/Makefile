.PHONY: up down db migrate dev test shell logs

up:
	docker compose up

down:
	docker compose down

db:
	docker compose up -d db

migrate:
	alembic upgrade head

dev: db
	uvicorn app.main:app --reload

test:
	pytest

logs:
	docker compose logs -f

shell:
	docker compose exec db psql -U tss -d tss
