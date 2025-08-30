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

### Running the Servers

FastMCP entrypoints are provided for each server:

```bash
# Flashcards / Anki
uv run fastmcp-flashcard-server

# Zotero
export ZOTERO_API_KEY=... \
       ZOTERO_LIBRARY_ID=... \
       ZOTERO_LIBRARY_TYPE=user   # or group
uv run fastmcp-zotero-server

# Obsidian
export OBSIDIAN_VAULT_PATH="/path/to/your/Obsidian/Vault"
uv run fastmcp-obsidian-server
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

## Zotero MCP Server

A FastMCP server for interacting with Zotero libraries using the pyzotero package.

### Available Tools

#### `search_zotero_items`
Search for items in your Zotero library.

**Parameters:**
- `query` (required): Search terms
- `limit`: Maximum results (default: 50)  
- `item_type`: Filter by type (e.g., 'book', 'journalArticle')

#### `get_zotero_item`
Get detailed information about a specific item.

**Parameters:**
- `item_key` (required): The Zotero item key

#### `get_item_notes`
Get all notes associated with an item.

**Parameters:**
- `item_key` (required): The Zotero item key

#### `list_zotero_collections`
List all collections in the library.

#### `get_collection_items`
Get items from a specific collection.

**Parameters:**
- `collection_key` (required): The collection key
- `limit`: Maximum results (default: 50)

#### `create_zotero_item`
Create a new item in the library.

**Parameters:**
- `item_type` (required): Type of item ('book', 'journalArticle', etc.)
- `title` (required): Item title
- `creators`: Array of creator objects
- `date`: Publication date
- `url`: Item URL
- `abstract`: Abstract/summary
- `tags`: Array of tag strings
- `extra_fields`: Additional type-specific fields

#### `create_item_note`
Add a note to an existing item.

**Parameters:**
- `parent_item_key` (required): Key of the parent item
- `note_content` (required): HTML-formatted note content

#### `add_item_to_collection`
Add an item to a collection.

**Parameters:**
- `item_key` (required): The item key
- `collection_key` (required): The collection key

#### `get_item_templates`
Get templates for creating different item types.

## Obsidian MCP Server

A FastMCP server for interacting with Obsidian vaults and markdown notes.

### Available Tools

#### `get_vault_stats`
Get comprehensive statistics about your Obsidian vault.

#### `list_vault_notes`
List all notes in the vault with optional pagination.

**Parameters:**
- `limit`: Maximum number of notes to return
- `offset`: Number of notes to skip (for pagination)
- `refresh_cache`: Whether to refresh the note cache

#### `search_obsidian_notes`
Search for notes by content, title, or tags.

**Parameters:**
- `query` (required): Search terms
- `search_in`: Fields to search in (content, title, tags)
- `limit`: Maximum number of results

#### `get_obsidian_note`
Get detailed information about a specific note.

**Parameters:**
- `note_name` (required): Name of the note (without .md extension)

#### `get_notes_by_tag`
Get all notes that have a specific tag.

**Parameters:**
- `tag` (required): Tag to search for

#### `get_note_backlinks`
Find all notes that link to a specific note.

**Parameters:**
- `note_name` (required): Name of the note to find backlinks for

#### `get_orphaned_notes`
Find notes that have no incoming or outgoing links.

#### `get_note_links`
Get all wikilinks from a specific note.

**Parameters:**
- `note_name` (required): Name of the note to get links from

#### `extract_note_headers`
Extract structured headers from a note.

**Parameters:**
- `note_name` (required): Name of the note to extract headers from

#### `extract_note_blocks`
Extract content blocks (paragraphs, lists, quotes, code) from a note.

**Parameters:**
- `note_name` (required): Name of the note to extract blocks from
- `block_types`: Types of blocks to extract (paragraph, list, quote, code, header)

#### `get_notes_for_flashcards`
Extract content from notes that is suitable for flashcard generation.

**Parameters:**
- `note_names`: Names of specific notes to process
- `tag_filter`: Only process notes with this tag
- `content_types`: Types of content to extract (headers, definitions, lists, quotes)

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

### Flashcard Server
Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "learning": {
      "command": "uv",
      "args": ["run", "fastmcp-flashcard-server"],
      "cwd": "/path/to/mcp-server-learning"
    }
  }
}
```

### Zotero Server
Configure the Zotero FastMCP server:

```json
{
  "mcpServers": {
    "zotero": {
      "command": "uv",
      "args": ["run", "fastmcp-zotero-server"],
      "cwd": "/path/to/mcp-server-learning",
      "env": {
        "ZOTERO_API_KEY": "your-zotero-api-key",
        "ZOTERO_LIBRARY_ID": "your-library-id", 
        "ZOTERO_LIBRARY_TYPE": "user"
      }
    }
  }
}
```

### Obsidian Server
Configure the Obsidian FastMCP server:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uv",
      "args": ["run", "fastmcp-obsidian-server"],
      "cwd": "/path/to/mcp-server-learning",
      "env": {
        "OBSIDIAN_VAULT_PATH": "/absolute/path/to/your/Obsidian/Vault"
      }
    }
  }
}
```

#### Zotero Environment Variables

You need to set these environment variables for the Zotero server:

- **ZOTERO_API_KEY**: Your Zotero Web API key (get from [zotero.org/settings/keys](https://www.zotero.org/settings/keys))
- **ZOTERO_LIBRARY_ID**: Your Zotero library ID
  - For personal library: Your user ID (find in your Zotero profile URL)
  - For group library: The group ID
- **ZOTERO_LIBRARY_TYPE**: Either "user" for personal library or "group" for group library

#### Getting Your Zotero Credentials

1. **API Key**: Go to [zotero.org/settings/keys](https://www.zotero.org/settings/keys) and create a new private key
2. **User ID**: Go to [zotero.org/settings/keys](https://www.zotero.org/settings/keys) - your user ID is shown at the top
3. **Group ID**: For group libraries, the ID is in the group's URL on zotero.org

### Obsidian Server
For the standalone Obsidian server, add this to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uv",
      "args": ["run", "obsidian-mcp-server"],
      "cwd": "/path/to/mcp-server-learning",
      "env": {
        "OBSIDIAN_VAULT_PATH": "/path/to/your/obsidian/vault"
      }
    }
  }
}
```

#### Obsidian Environment Variable

You need to set this environment variable for the Obsidian server:

- **OBSIDIAN_VAULT_PATH**: Full path to your Obsidian vault directory (the folder containing your .md files and .obsidian folder)

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


## Future Features

- Advanced citation styles (MLA, Chicago, IEEE)
- Batch processing for large collections
- Spaced repetition scheduling integration
- Cross-reference detection between Zotero and Obsidian
- Support for multimedia flashcards
- Export to other flashcard platforms
- Collaborative learning features
