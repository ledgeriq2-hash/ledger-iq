DOCKER_COMPOSE ?= docker compose

.PHONY: run up down logs restart ps migrate seed verify test-backend test-frontend clean

run:
	$(DOCKER_COMPOSE) up --build

up:
	$(DOCKER_COMPOSE) up -d --build

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f --tail=200

restart:
	$(DOCKER_COMPOSE) restart

ps:
	$(DOCKER_COMPOSE) ps

migrate:
	$(DOCKER_COMPOSE) exec backend alembic upgrade head

seed:
	$(DOCKER_COMPOSE) exec backend python -m app.initial_data

verify:
	$(DOCKER_COMPOSE) exec backend python scripts/verify_sprint3.py
	$(DOCKER_COMPOSE) exec backend python scripts/verify_sprint4.py
	$(DOCKER_COMPOSE) exec backend python scripts/verify_sprint5.py
	$(DOCKER_COMPOSE) exec backend python scripts/verify_sprint6.py

test-backend:
	$(DOCKER_COMPOSE) exec backend pytest -q

test-frontend:
	@echo "Frontend does not define npm test; run npm run test:e2e inside frontend if needed"

clean:
	$(DOCKER_COMPOSE) down -v
