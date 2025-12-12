PYTHON ?= python

.PHONY: init-db migrate seed-db

init-db:  ## Run migrations and seed default roles/chart of accounts
	cd backend && $(PYTHON) -m alembic upgrade head
	cd backend && $(PYTHON) -m app.initial_data

migrate:  ## Create a new alembic revision with message m="description"
	cd backend && $(PYTHON) -m alembic revision --autogenerate -m "$(m)"

seed-db:  ## Seed default roles and chart of accounts without running migrations
	cd backend && $(PYTHON) -m app.initial_data

.PHONY: create-demo-tenant
create-demo-tenant:  ## Create a demo tenant with sample data
	cd backend && $(PYTHON) -m app.management.demo_data
