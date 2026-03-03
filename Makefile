SHELL := /bin/bash

.PHONY: help env compose-config up rebuild clean-orphans down down-v ps logs smoke

help:
	@echo "Available targets:"
	@echo "  make up            # create .env if missing and start stack"
	@echo "  make rebuild       # rebuild images and force recreate containers"
	@echo "  make clean-orphans # remove orphan containers without full teardown"
	@echo "  make down          # stop stack"
	@echo "  make down-v        # stop stack and remove volumes + orphans"
	@echo "  make ps            # show compose services status"
	@echo "  make logs          # follow compose logs"
	@echo "  make smoke         # run local smoke checks"
	@echo "  make compose-config # validate compose config"

env:
	@if [ ! -f .env ]; then cp .env.example .env; fi

compose-config:
	@docker compose config -q

up: env
	@docker compose up -d --build

rebuild: env
	@docker compose up -d --build --force-recreate

clean-orphans: env
	@docker compose up -d --remove-orphans

down:
	@docker compose down

down-v:
	@docker compose down -v --remove-orphans

ps:
	@docker compose ps

logs:
	@docker compose logs -f --tail=200

smoke:
	@curl -fsS http://localhost:8000/health >/dev/null
	@curl -fsS http://localhost:5173 >/dev/null
	@curl -fsS http://localhost:9000/minio/health/live >/dev/null
	@echo "Smoke checks passed."
