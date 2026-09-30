.PHONY: dev test deploy eval lint

dev:
	cp -n .env.example .env 2>/dev/null || true
	docker compose up --build

test:
	cd backend && poetry run pytest
	cd frontend && npm install && npm run build

deploy:
	git push origin main

eval:
	python evaluation/run_eval.py

lint:
	cd backend && poetry run python -m compileall app
