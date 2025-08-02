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
- **Zotero Integration**: Generate flashcards from your Zotero research library
- **Obsidian Integration**: Create flashcards from your Obsidian vault notes

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

### Zotero Integration Tools

#### `connect_zotero`
Connect to your Zotero library using Web API or local database.

**Parameters:**
- `api_key`: Zotero Web API key (optional for local access)
- `user_id`: Your Zotero user ID for personal library
- `group_id`: Zotero group ID for group library
- `local_profile_path`: Path to local Zotero profile (optional)
- `prefer_local`: Whether to prefer local database over Web API

#### `search_zotero`
Search items in your connected Zotero library.

**Parameters:**
- `query`: Search terms
- `limit`: Maximum number of results (default: 20)

#### `get_zotero_collections`
List all collections in your Zotero library.

#### `create_flashcards_from_zotero`
Generate flashcards from Zotero items or collections.

**Parameters:**
- `item_keys`: Specific Zotero item keys to use
- `collection_id`: Collection ID to generate cards from
- `card_types`: Types of cards to create (`citation`, `summary`, `definition`)
- `citation_style`: Citation format (`apa`)

### Obsidian Integration Tools

#### `connect_obsidian`
Connect to an Obsidian vault.

**Parameters:**
- `vault_path`: Path to your Obsidian vault directory

#### `search_obsidian`
Search notes in your connected Obsidian vault.

**Parameters:**
- `query`: Search terms
- `search_in`: Fields to search (`content`, `title`, `tags`)
- `limit`: Maximum number of results (default: 20)

#### `get_obsidian_vault_stats`
Get statistics about your Obsidian vault (note count, tags, etc.).

#### `create_flashcards_from_obsidian`
Generate flashcards from Obsidian notes.

**Parameters:**
- `note_names`: Specific note names to process
- `tag_filter`: Only process notes with this tag
- `content_types`: Types of content to extract (`headers`, `definitions`, `lists`, `quotes`)
- `card_type`: Type of flashcards to generate (`front-back`, `cloze`)

## Integration Setup

### Anki Integration

To use Anki integration:

1. Install the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) addon in Anki
2. Start Anki with the addon enabled
3. Use the `upload_to_anki` or `check_anki_connection` tools

### Zotero Integration

To use Zotero integration:

**Option 1: Local Database (Recommended)**
1. Install Zotero desktop application
2. Use `connect_zotero` tool with local access
3. No additional setup required

**Option 2: Web API**
1. Get your Zotero API key from [zotero.org/settings/keys](https://www.zotero.org/settings/keys)
2. Find your user ID from your Zotero profile URL
3. Use `connect_zotero` tool with API credentials

### Obsidian Integration

To use Obsidian integration:

1. Locate your Obsidian vault directory
2. Use `connect_obsidian` tool with the vault path
3. The connector will scan and index your notes automatically

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

## Usage Examples

### Basic Flashcard Creation
```
# Create flashcards from text
create_flashcards(content="Q: What is Python? A: A programming language", card_type="front-back")

# Create cloze deletion cards
create_flashcards(content="Python is a {{programming language}} used for {{web development}}.", card_type="cloze")
```

### Zotero Integration Workflow
```
# Connect to Zotero
connect_zotero(prefer_local=True)

# Search your library
search_zotero(query="machine learning", limit=10)

# Generate citation flashcards
create_flashcards_from_zotero(item_keys=["ITEM123"], card_types=["citation", "summary"])
```

### Obsidian Integration Workflow
```
# Connect to vault
connect_obsidian(vault_path="/path/to/your/vault")

# Search notes
search_obsidian(query="neural networks", search_in=["content", "tags"])

# Generate flashcards from notes
create_flashcards_from_obsidian(tag_filter="study", content_types=["definitions", "headers"])
```

## Future Features

- Advanced citation styles (MLA, Chicago, IEEE)
- Batch processing for large collections
- Spaced repetition scheduling integration
- Cross-reference detection between Zotero and Obsidian
- Support for multimedia flashcards
- Export to other flashcard platforms
- Collaborative learning features