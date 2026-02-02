# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A collection of MCP (Model Context Protocol) servers for learning tasks, built with FastMCP:
- **Flashcard Server**: Flashcards with LaTeX support and Anki integration
- **Math Verification Server**: Verify mathematical expressions/proofs using SymPy with LaTeX input
- **Zotero Server**: Interact with Zotero libraries via pyzotero
- **Obsidian Server**: Connect to Obsidian vaults for note management

## Development Commands

```bash
# Setup
uv sync

# Run servers
uv run fastmcp-flashcard-server
uv run fastmcp-math-server
uv run fastmcp-zotero-server    # requires ZOTERO_API_KEY, ZOTERO_LIBRARY_ID, ZOTERO_LIBRARY_TYPE
uv run fastmcp-obsidian-server  # requires OBSIDIAN_VAULT_PATH

# Testing
uv run pytest                                    # all tests
uv run pytest tests/test_math_verification.py   # single file
uv run pytest -m "not integration"              # skip integration tests
uv run pytest tests/test_anki_connectivity.py::TestAnkiConnectivity::test_make_request_success  # single test

# Code quality
uv run black src/    # format (100 char line length)
uv run isort src/    # sort imports
uv run mypy src/     # type check
```

## Architecture

All servers follow the same pattern in `src/mcp_server_learning/`:
```python
mcp = FastMCP("Server Name")

@mcp.tool
def my_tool(param: str) -> Dict[str, Any]:
    """Docstring becomes tool description."""
    return {"success": True, "data": result, "message": "...", "error": None}

def main():
    mcp.run()
```

Console scripts registered in `pyproject.toml` under `[project.scripts]`.

### Key Classes

**Flashcard Server** (`fastmcp_flashcard_server.py`):
- `AnkiConnector`: AnkiConnect API interface (localhost:8765)
- `FlashcardGenerator`: Text → flashcards with LaTeX handling
- `AnkiCardManager`: Converts and uploads cards to Anki

**Math Verification Server** (`fastmcp_math_verification_server.py`):
- `LaTeXParser.parse()`: LaTeX → SymPy (uses latex2sympy2, falls back to sympy.parsing.latex)
- `SymPyVerifier`: Verification for equality, derivatives, integrals, limits
- `ProofStepValidator`: Multi-step proof validation

**Obsidian Server** (`fastmcp_obsidian_server.py` + `obsidian_connector.py`):
- `ObsidianConnector`: Vault scanner, parses wikilinks `[[Note]]` and frontmatter

## Critical Implementation Details

### LaTeX Processing (Flashcard Server)
- Claude Desktop display: Keep standard LaTeX (`$...$`, `$$...$$`)
- Anki upload: Convert to MathJax format (`\(...\)`, `\[...\]`)
- Use `FlashcardGenerator.convert_to_anki_mathjax()` for Anki, `preserve_claude_latex()` for display

### Card Flagging (Flashcard Server)
- All cards added or modified automatically receive the purple flag (flag value 7)
- Flagging is best-effort: failures don't break card creation/updates
- Implementation: `add_note()`, `add_notes()`, and `update_note()` auto-call `_set_card_flags()`
- Helper methods: `get_card_ids_from_notes()` converts note IDs → card IDs

### LaTeX Parsing (Math Server)
- Primary: `latex2sympy2.latex2sympy()`
- Fallback: `sympy.parsing.latex.parse_latex()`
- Preprocesses function names (sin, cos, tan, log, exp) to LaTeX commands (`\sin`, etc.)

### Error Handling Patterns
```python
# AnkiConnect errors - must match test expectations
raise Exception(f"AnkiConnect error: {result['error']}")

# Connection errors
raise Exception("Failed to connect to Anki: connection refused")

# Math parsing errors
raise ValueError(f"Failed to parse LaTeX expression: {str(e)}")
```

### Tool Return Format
All tools return consistent structure:
```python
{"success": bool, "data": Any, "message": str, "error": Optional[str]}
```

## Testing

- **Integration tests**: `@pytest.mark.integration` - require external services (Anki)
- **conftest.py fixtures**: `anki_mock_response`, `sample_flashcard_content`, `anki_test_cleanup`
- **Test cleanup**: `conftest.py` auto-cleans test decks matching specific patterns after integration tests

Test files map to servers:
- `test_anki_connectivity.py` → flashcard server AnkiConnector
- `test_math_verification.py` → math server LaTeXParser/SymPyVerifier
- `test_fastmcp_obsidian_server.py` → obsidian server smoke tests
