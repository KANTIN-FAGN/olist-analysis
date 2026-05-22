include .env
export

.PHONY: build up down restart logs ps reset init clean db-shell superset-shell

build:
	docker compose build

up:
	docker compose up -d
	@echo ">>> Superset  : http://localhost:8088"
	@echo ">>> PostgreSQL: localhost:5432"

down:
	docker compose down

restart:
	docker compose down
	docker compose up -d --build

logs:
	docker compose logs -f

ps:
	docker compose ps

reset:
	docker compose down -v
	docker compose up -d --build

clean:
	docker compose down -v --remove-orphans

db-shell:
	docker exec -it olist_postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

superset-shell:
	docker exec -it olist_superset bash

init:
	docker compose up -d --build
	docker compose ps