# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a collection of MCP (Model Context Protocol) servers for learning and educational tasks, built using FastMCP. The project provides four main servers:

1. **Flashcard Server**: Create, manage, and export flashcards with LaTeX support and Anki integration
2. **Zotero Server**: Interact with Zotero libraries via pyzotero for academic reference management
3. **Obsidian Server**: Connect to Obsidian vaults for note management and flashcard extraction
4. **Math Verification Server**: Verify mathematical expressions, proofs, and derivations using SymPy with LaTeX input

## Architecture

### FastMCP Pattern
All servers follow the FastMCP pattern:
- Each server is defined in a single file under `src/mcp_server_learning/`
- FastMCP instance is created with `mcp = FastMCP("Server Name")`
- Tools are defined as Python functions decorated with `@mcp.tool()`
- Main entry point uses `mcp.run()` for execution
- Console scripts are registered in `pyproject.toml` under `[project.scripts]`

### Key Components

**Flashcard Server** (`fastmcp_flashcard_server.py`):
- `AnkiConnector`: Interface to AnkiConnect API for direct Anki uploads
- `FlashcardGenerator`: Converts text to LaTeX flashcards (front-back and cloze deletion)
- `HTMLRenderer`: Generates HTML previews of flashcards
- Handles LaTeX math notation with proper display mode conversion (`$$...$$` → `\[...\]`)

**Math Verification Server** (`fastmcp_math_verification_server.py`):
- `LaTeXParser`: Converts LaTeX math notation to SymPy expressions (uses latex2sympy2 + fallback to SymPy parser)
- `SymPyVerifier`: Core verification engine for expressions, derivatives, integrals, limits
- `ProofStepValidator`: Multi-step proof validation with justifications
- Supports assumptions about variables (e.g., "x is real", "x is positive")

**Zotero Server** (`fastmcp_zotero_server.py`):
- Uses `pyzotero.zotero.Zotero` client for API interactions
- Environment-configured: `ZOTERO_API_KEY`, `ZOTERO_LIBRARY_ID`, `ZOTERO_LIBRARY_TYPE`
- Provides search, item retrieval, note creation, and collection management

**Obsidian Server** (`fastmcp_obsidian_server.py`):
- `ObsidianConnector`: Vault scanner and indexer (in `obsidian_connector.py`)
- Environment-configured: `OBSIDIAN_VAULT_PATH`
- Parses wikilinks `[[Note Name]]`, frontmatter tags, and markdown structure
- Supports backlink analysis and orphaned note detection

## Development Commands

### Setup and Installation
```bash
# Install dependencies
uv sync

# Install in development mode
uv pip install -e .
```

### Running Servers
```bash
# Flashcard server
uv run fastmcp-flashcard-server

# Zotero server (requires env vars)
export ZOTERO_API_KEY=... ZOTERO_LIBRARY_ID=... ZOTERO_LIBRARY_TYPE=user
uv run fastmcp-zotero-server

# Obsidian server (requires env var)
export OBSIDIAN_VAULT_PATH="/path/to/vault"
uv run fastmcp-obsidian-server

# Math verification server
uv run fastmcp-math-server
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_math_verification.py

# Run with markers
uv run pytest -m "not integration"  # Skip integration tests
uv run pytest -m "not slow"         # Skip slow tests

# Run specific test
uv run pytest tests/test_math_verification.py::TestLaTeXParser::test_parse_simple_expression
```

### Code Quality
```bash
# Format code (Black with 100 char line length)
uv run black src/

# Sort imports (isort with Black profile)
uv run isort src/

# Type checking (Python 3.12, strict settings)
uv run mypy src/
```

## Testing Architecture

- **Test Configuration**: `pytest.ini` configures markers, warnings, and pytest behavior
- **Test Fixtures**: `tests/conftest.py` provides shared fixtures and path setup
- **Integration Tests**: Marked with `@pytest.mark.integration` (e.g., Anki connectivity tests)
- **Smoke Tests**: Quick validation tests (e.g., `test_fastmcp_obsidian_server.py`)

Test categories:
- `test_anki_connectivity.py`: Integration tests requiring running Anki instance
- `test_math_verification.py`: Unit tests for LaTeX parsing and SymPy verification
- `test_display_latex.py`, `test_latex_rendering.py`: LaTeX format validation
- `test_fastmcp_obsidian_server.py`: Obsidian server smoke tests

## Important Implementation Details

### LaTeX Processing
- **Display Math Conversion**: The flashcard server converts `$$...$$` to `\[...\]` for Anki compatibility
- **Math Parsing**: Math server uses `latex2sympy2` as primary parser with SymPy's `parse_latex` as fallback
- **Regex Preprocessing**: Function names (sin, cos, tan, log, exp) are converted to LaTeX commands before parsing

### Error Handling Standards
- **AnkiConnect errors**: Raise `Exception(f"AnkiConnect error: {result['error']}")` (matches test expectations in `test_anki_connectivity.py`)
- **Math parsing errors**: Raise `ValueError` with descriptive messages about what failed to parse
- **Zotero errors**: Let pyzotero exceptions propagate naturally

### Environment Variables
Required for certain servers:
- Zotero: `ZOTERO_API_KEY`, `ZOTERO_LIBRARY_ID`, `ZOTERO_LIBRARY_TYPE` (user|group)
- Obsidian: `OBSIDIAN_VAULT_PATH`

Example `.env` structure is in `.env.example`.

## Tool Development Patterns

When adding new tools to any server:

1. Define function with clear type hints
2. Add descriptive docstring with parameter explanations
3. Decorate with `@mcp.tool()` or `@mcp.tool(description="...")`
4. Return structured data (dicts/lists) rather than formatted strings
5. Handle errors gracefully with meaningful messages

Example:
```python
@mcp.tool()
def my_tool(param: str, optional: int = 10) -> Dict[str, Any]:
    """
    Tool description.

    Args:
        param: Description of param
        optional: Description of optional param (default: 10)
    """
    try:
        # Implementation
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

## Dependencies Management

This project uses `uv` for fast, reliable dependency management:
- Dependencies are declared in `pyproject.toml` under `[project.dependencies]`
- Dev dependencies in `[project.optional-dependencies.dev]` and `[dependency-groups.dev]`
- Lock file is `uv.lock` (committed to repo)
- Use `uv add <package>` to add new dependencies
- Use `uv sync` after pulling changes

## Configuration with Claude Desktop

All servers can be registered as MCP servers in Claude Desktop. Example configuration:

```json
{
  "mcpServers": {
    "flashcards": {
      "command": "uv",
      "args": ["run", "fastmcp-flashcard-server"],
      "cwd": "/path/to/mcp-server-learning"
    },
    "math-verification": {
      "command": "uv",
      "args": ["run", "fastmcp-math-server"],
      "cwd": "/path/to/mcp-server-learning"
    }
  }
}
```

For servers requiring environment variables, add `"env": {...}` to the configuration.
