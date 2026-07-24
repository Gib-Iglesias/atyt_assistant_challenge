.DEFAULT_GOAL := help
.PHONY: help up down clean logs ps test test-api test-django seed reindex sh-django sh-api

help:
	@echo "up          arrancar todo (primera vez: make env && make up)"
	@echo "down        parar los contenedores"
	@echo "clean       parar y borrar el volumen de datos"
	@echo "logs        seguir los logs de todos los servicios"
	@echo "test        correr toda la bateria de tests"
	@echo "seed        regenerar los datos de ejemplo"
	@echo "reindex     reconstruir el indice FTS5"

env:
	@test -f .env || cp .env.example .env
	@echo ".env listo"

up: env
	docker compose up --build

down:
	docker compose down

clean:
	docker compose down -v

logs:
	docker compose logs -f

ps:
	docker compose ps

test: test-api test-django

test-api:
	docker compose run --rm api pytest -q

test-django:
	docker compose run --rm django python manage.py test

seed:
	docker compose exec django python manage.py seed_demo

reindex:
	docker compose exec django python manage.py ingest_docs --reindex

sh-django:
	docker compose exec django bash

sh-api:
	docker compose exec api bash
