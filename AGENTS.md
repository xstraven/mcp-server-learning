# Repository Guidelines

## Project Structure & Module Organization
- `src/mcp_server_learning/`: MCP servers and connectors
  - `fastmcp_flashcard_server.py`: flashcard creation, LaTeX/HTML preview, Anki integration
  - `fastmcp_zotero_server.py`, `zotero_mcp_server.py`: Zotero tools and server entry points
  - `obsidian_mcp_server.py`, `obsidian_connector.py`: Obsidian-related tooling
- `tests/`: pytest suites (unit and integration). See markers in `pytest.ini`.
- `README.md`: feature overview and tool usage.
- `.env.example` → copy to `.env` for local secrets/config.

## Build, Test, and Development Commands
- `uv sync`: install/lock dependencies for this project.
- `uv run pytest`: run all tests.
- `uv run pytest -m "not integration"`: skip integration tests (Anki/Zotero).
- `uv run black . && uv run isort .`: auto-format imports and code.
- `uv run mypy src`: type-check (Python 3.12 target).
- Run servers locally:
  - `uv run fastmcp-flashcard-server`
  - `uv run zotero-mcp-server`
  - `uv run obsidian-mcp-server`

## Coding Style & Naming Conventions
- Formatting: Black (line length 100) + isort (profile "black").
- Typing: mypy enabled; add type hints (untyped defs are disallowed).
- Naming: files/modules `snake_case.py`; classes `PascalCase`; functions/vars `snake_case`.
- Imports: prefer absolute within `mcp_server_learning` package.

## Testing Guidelines
- Framework: pytest. Place tests under `tests/`, name `test_*.py`.
- Markers: use `@pytest.mark.integration` for tests requiring running Anki/Zotero.
- Strategy: mock network/IO in unit tests; keep tests fast and deterministic.
- Examples: `uv run pytest tests/test_latex_rendering.py -v`.

## Commit & Pull Request Guidelines
- Commits: short, imperative, scoped messages (e.g., "flashcards: fix LaTeX rendering").
- Include tests/docs with behavior changes; keep diffs focused.
- PRs: provide description, rationale, linked issues, and screenshots/logs for server output when relevant.
- Verify `pytest`, `black`, `isort`, and `mypy` pass before requesting review.

## Security & Configuration Tips
- Use `.env` for secrets (copy from `.env.example`); never commit secrets.
- External apps/keys: Anki (AnkiConnect), Zotero API. Prefer environment variables over hardcoding.
