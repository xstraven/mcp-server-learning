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
