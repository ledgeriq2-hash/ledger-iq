DOCKER_COMPOSE ?= docker compose

.PHONY: up down logs restart ps migrate test-backend test-frontend clean

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

test-backend:
	$(DOCKER_COMPOSE) exec backend pytest -q

test-frontend:
	@echo "Frontend does not define npm test; run npm run test:e2e inside frontend if needed"

clean:
	$(DOCKER_COMPOSE) down -v
