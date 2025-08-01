# MCP Server Learning

A Model Context Protocol (MCP) server designed to help with learning and educational tasks. Currently includes a comprehensive flashcard generation and management system.

## Features

### Flashcard Server

The flashcard server provides tools for creating, managing, and exporting flashcards in various formats:

- **Multiple Card Types**: Support for front-back cards, cloze deletion cards, and diagram cards
- **LaTeX Support**: Generate LaTeX-formatted flashcards with mathematical notation support
- **Anki Integration**: Direct upload to Anki using AnkiConnect addon
- **HTML Preview**: Generate beautiful HTML previews of your flashcards
- **Diagram Support**: Handle ASCII art, TikZ diagrams, and flowcharts

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# Clone the repository
git clone <repository-url>
cd mcp-server-learning

# Install dependencies
uv sync

# Install in development mode
uv pip install -e .
```

## Usage

### Running the Server

The server can be run directly:

```bash
mcp-server-learning
```

Or using uv:

```bash
uv run mcp-server-learning
```

### Available Tools

#### `create_flashcards`
Convert text content into LaTeX flashcards.

**Parameters:**
- `content` (required): Text content to convert
- `card_type`: "front-back" or "cloze" (default: "front-back")
- `title`: Title for the deck (default: "Flashcards")
- `full_document`: Whether to return complete LaTeX document (default: true)

**Example input formats:**
```
Q: What is the capital of France?
A: Paris

---

What is 2 + 2?
4
```

For cloze cards:
```
The capital of {{France}} is {{Paris}}.
```

#### `create_single_card`
Create a single flashcard.

**Parameters:**
- For front-back cards: `front`, `back`
- For cloze cards: `cloze_text`
- `card_type`: "front-back" or "cloze"

#### `create_diagram_card`
Create a flashcard with a diagram.

**Parameters:**
- `diagram`: The diagram content
- `explanation`: Explanation of the diagram
- `diagram_type`: "ascii", "tikz", or "flowchart"

#### `upload_to_anki`
Upload flashcards directly to Anki.

**Parameters:**
- `content`: Content to convert and upload
- `card_type`: Type of cards to create
- `deck_name`: Anki deck name (default: "MCP Generated Cards")
- `tags`: Array of tags to add
- `anki_api_key`: Optional API key for AnkiConnect

#### `check_anki_connection`
Check connection to Anki and list available decks/models.

#### `preview_cards`
Generate HTML preview of flashcards.

**Parameters:**
- `content`: Content to preview
- `card_type`: Type of cards
- `title`: Preview title
- `tags`: Tags to display

## Anki Integration

To use Anki integration:

1. Install the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) addon in Anki
2. Start Anki with the addon enabled
3. Use the `upload_to_anki` or `check_anki_connection` tools

## Development

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run black src/
uv run isort src/
```

### Type Checking

```bash
uv run mypy src/
```

## Configuration with Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "learning": {
      "command": "uv",
      "args": ["run", "mcp-server-learning"],
      "cwd": "/path/to/mcp-server-learning"
    }
  }
}
```

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Future Features

- Spaced repetition scheduling
- Quiz generation
- Study statistics
- Integration with other learning platforms
- Support for multimedia flashcards
- Collaborative learning features