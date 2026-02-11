BACKEND_DIR=backend

.PHONY: backend-fetch backend-lint backend-format backend-test

backend-fetch:
	cd $(BACKEND_DIR) && uv run python -m app.cli fetch -c PL

backend-lint:
	cd $(BACKEND_DIR) && uv run ruff check .

backend-format:
	cd $(BACKEND_DIR) && uv run ruff format .

backend-test:
	cd $(BACKEND_DIR) && uv run pytest -q
