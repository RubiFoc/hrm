set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

default:
  @just --list

env:
  [ -f .env ] || cp .env.example .env

compose-config:
  docker compose config -q

up:
  just env
  docker compose up -d --build

rebuild:
  just env
  docker compose up -d --build --force-recreate

clean-orphans:
  just env
  docker compose up -d --remove-orphans

down:
  docker compose down

down-v:
  docker compose down -v --remove-orphans

ps:
  docker compose ps

logs:
  docker compose logs -f --tail=200

smoke:
  ./scripts/smoke-compose.sh
