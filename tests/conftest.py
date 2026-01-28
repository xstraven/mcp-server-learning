#!/usr/bin/env python3

import sys
from pathlib import Path

import pytest

# Add the src directory to the Python path for imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may require external services)"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle integration test marking."""
    for item in items:
        # Automatically mark integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)


# Test fixtures
@pytest.fixture
def anki_mock_response():
    """Fixture for mocking Anki Connect responses."""

    def _mock_response(result=None, error=None):
        class MockResponse:
            def __init__(self, result, error):
                self._result = result
                self._error = error

            def json(self):
                return {"result": self._result, "error": self._error}

            def raise_for_status(self):
                pass

        return MockResponse(result, error)

    return _mock_response


@pytest.fixture
def sample_anki_deck_names():
    """Fixture providing sample Anki deck names."""
    return ["Default", "Spanish", "Math", "Programming", "History"]


@pytest.fixture
def sample_anki_model_names():
    """Fixture providing sample Anki model names."""
    return ["Basic", "Basic (and reversed card)", "Cloze", "Basic (optional reversed card)"]


@pytest.fixture
def sample_flashcard_content():
    """Fixture providing sample flashcard content for testing."""
    return {
        "front_back": """Q: What is the capital of France?
A: Paris

Q: What is 2 + 2?
A: 4""",
        "cloze": "The capital of {{France}} is {{Paris}}.",
        "multiple_cloze": """{{Python}} is a programming language.
It was created by {{Guido van Rossum}} in {{1991}}.""",
    }


@pytest.fixture(scope="session", autouse=False)
def anki_test_cleanup(request):
    """Session-scoped fixture for cleaning up Anki test data after tests complete.

    This fixture cleans up test decks and notes created during integration tests.
    It runs after all tests in the session that use it have completed.

    Test decks and notes are identified by:
    - Specific deck name patterns used in tests
    - Tags matching the pattern 'mcp-test-*'
    """
    # Yield control to tests first
    yield

    # Teardown: cleanup after all tests
    from mcp_server_learning.fastmcp_flashcard_server import AnkiConnector

    connector = AnkiConnector()

    # Check if Anki is available
    try:
        connector.check_permission()
    except Exception:
        # Anki not available, skip cleanup
        return

    # Test deck patterns to clean up
    test_deck_patterns = [
        "Display LaTeX Test",
        "Test Deck - Sigmoid",
        "Test Deck - Sigmoid MCP",
        "LaTeX Test - Standard",
        "LaTeX Test - Double",
        "LaTeX Test - MathJax",
        "LaTeX Test - Display",
        "LaTeX Test - Raw",
    ]

    # Clean up notes by tag pattern
    try:
        note_ids = connector.find_notes("tag:re:mcp-test-.*")
        if note_ids:
            connector.delete_notes(note_ids)
    except Exception:
        pass

    # Clean up test decks
    try:
        connector.delete_decks(test_deck_patterns, cards_too=True)
    except Exception:
        pass
