#!/usr/bin/env python3

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml


class ObsidianMarkdownParser:
    """Parser for Obsidian markdown files with frontmatter, links, and tags."""

    @staticmethod
    def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
        """Parse YAML frontmatter from markdown content."""
        if not content.startswith("---"):
            return {}, content

        try:
            parts = content.split("---", 2)
            if len(parts) < 3:
                return {}, content

            frontmatter_yaml = parts[1].strip()
            body = parts[2].lstrip("\n")

            frontmatter = yaml.safe_load(frontmatter_yaml) if frontmatter_yaml else {}
            return frontmatter or {}, body

        except yaml.YAMLError:
            return {}, content

    @staticmethod
    def extract_wikilinks(content: str) -> List[Dict[str, str]]:
        """Extract [[wikilinks]] from content."""
        pattern = r"\[\[([^\]]+)\]\]"
        matches = re.finditer(pattern, content)

        links = []
        for match in matches:
            full_link = match.group(1)

            # Handle display text: [[link|display]]
            if "|" in full_link:
                link, display = full_link.split("|", 1)
            else:
                link = display = full_link

            # Handle headers: [[link#header]]
            if "#" in link:
                link, header = link.split("#", 1)
            else:
                header = None

            links.append(
                {
                    "target": link.strip(),
                    "display": display.strip(),
                    "header": header.strip() if header else None,
                    "full_match": match.group(0),
                }
            )

        return links

    @staticmethod
    def extract_tags(content: str, frontmatter: Dict[str, Any] = None) -> Set[str]:
        """Extract tags from content and frontmatter."""
        tags = set()

        # Tags from frontmatter
        if frontmatter:
            fm_tags = frontmatter.get("tags", [])
            if isinstance(fm_tags, str):
                fm_tags = [fm_tags]
            elif isinstance(fm_tags, list):
                fm_tags = [str(tag) for tag in fm_tags]
            tags.update(fm_tags)

        # Inline tags (#tag)
        inline_pattern = r"(?:^|\s)#([a-zA-Z0-9/_-]+)"
        inline_matches = re.finditer(inline_pattern, content, re.MULTILINE)
        for match in inline_matches:
            tags.add(match.group(1))

        return tags

    @staticmethod
    def extract_headers(content: str) -> List[Dict[str, Any]]:
        """Extract headers from markdown content."""
        headers = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            header_match = re.match(r"^(#{1,6})\s+(.+)", line)
            if header_match:
                level = len(header_match.group(1))
                text = header_match.group(2).strip()

                headers.append(
                    {
                        "level": level,
                        "text": text,
                        "line_number": i + 1,
                        "anchor": ObsidianMarkdownParser._create_anchor(text),
                    }
                )

        return headers

    @staticmethod
    def _create_anchor(text: str) -> str:
        """Create Obsidian-style anchor from header text."""
        # Remove markdown formatting
        clean_text = re.sub(r"[*_`]", "", text)
        # Convert to lowercase and replace spaces/special chars with hyphens
        anchor = re.sub(r"[^\w\s-]", "", clean_text.lower())
        anchor = re.sub(r"[-\s]+", "-", anchor)
        return anchor.strip("-")

    @staticmethod
    def extract_blocks(content: str) -> List[Dict[str, Any]]:
        """Extract content blocks (paragraphs, lists, code blocks, etc.)."""
        blocks = []
        lines = content.split("\n")
        current_block = []
        current_type = None
        in_code_block = False
        code_lang = None

        for i, line in enumerate(lines):
            if line.strip().startswith("```"):
                if not in_code_block:
                    # Start of code block
                    if current_block:
                        blocks.append(
                            {
                                "type": current_type or "paragraph",
                                "content": "\n".join(current_block),
                                "start_line": i - len(current_block) + 1,
                                "end_line": i,
                            }
                        )
                        current_block = []

                    in_code_block = True
                    code_lang = line.strip()[3:].strip() or "text"
                    current_type = "code"
                else:
                    # End of code block
                    blocks.append(
                        {
                            "type": "code",
                            "content": "\n".join(current_block),
                            "language": code_lang,
                            "start_line": i - len(current_block),
                            "end_line": i + 1,
                        }
                    )
                    current_block = []
                    in_code_block = False
                    current_type = None
                continue

            if in_code_block:
                current_block.append(line)
                continue

            if line.strip() == "":
                if current_block:
                    blocks.append(
                        {
                            "type": current_type or "paragraph",
                            "content": "\n".join(current_block),
                            "start_line": i - len(current_block) + 1,
                            "end_line": i,
                        }
                    )
                    current_block = []
                    current_type = None
            else:
                if re.match(r"^\s*[-*+]\s", line):
                    block_type = "list"
                elif re.match(r"^\s*\d+\.\s", line):
                    block_type = "numbered_list"
                elif re.match(r"^\s*>\s", line):
                    block_type = "quote"
                elif re.match(r"^#{1,6}\s", line):
                    block_type = "header"
                else:
                    block_type = "paragraph"

                if current_type != block_type and current_block:
                    blocks.append(
                        {
                            "type": current_type,
                            "content": "\n".join(current_block),
                            "start_line": i - len(current_block) + 1,
                            "end_line": i,
                        }
                    )
                    current_block = []

                current_type = block_type
                current_block.append(line)

        # Add final block
        if current_block:
            blocks.append(
                {
                    "type": current_type or "paragraph",
                    "content": "\n".join(current_block),
                    "start_line": len(lines) - len(current_block) + 1,
                    "end_line": len(lines),
                }
            )

        return blocks


class ObsidianVaultScanner:
    """Scanner for Obsidian vault structure and content."""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        if not self.vault_path.exists():
            raise FileNotFoundError(f"Vault path does not exist: {vault_path}")

        self.obsidian_folder = self.vault_path / ".obsidian"
        self.parser = ObsidianMarkdownParser()

    def get_all_notes(self) -> List[Dict[str, Any]]:
        """Get all markdown notes in the vault."""
        notes = []

        for md_file in self.vault_path.rglob("*.md"):
            # Skip files in .obsidian directory
            if ".obsidian" in md_file.parts:
                continue

            try:
                note_data = self.parse_note(md_file)
                notes.append(note_data)
            except Exception as e:
                print(f"Error parsing {md_file}: {e}")
                continue

        return notes

    def parse_note(self, file_path: Path) -> Dict[str, Any]:
        """Parse a single note file."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        frontmatter, body = self.parser.parse_frontmatter(content)

        # Get file stats
        stat = file_path.stat()

        note_data = {
            "path": str(file_path.relative_to(self.vault_path)),
            "absolute_path": str(file_path),
            "name": file_path.stem,
            "title": frontmatter.get("title", file_path.stem),
            "content": body,
            "full_content": content,
            "frontmatter": frontmatter,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "tags": list(self.parser.extract_tags(content, frontmatter)),
            "wikilinks": self.parser.extract_wikilinks(content),
            "headers": self.parser.extract_headers(body),
            "blocks": self.parser.extract_blocks(body),
        }

        # Add hash for change detection
        note_data["content_hash"] = hashlib.md5(content.encode()).hexdigest()

        return note_data

    def search_notes(self, query: str, search_in: List[str] = None) -> List[Dict[str, Any]]:
        """Search notes by content, title, or tags."""
        if search_in is None:
            search_in = ["content", "title", "tags"]

        query_lower = query.lower()
        matching_notes = []

        for note in self.get_all_notes():
            matches = False

            if "content" in search_in and query_lower in note["content"].lower():
                matches = True

            if "title" in search_in and query_lower in note["title"].lower():
                matches = True

            if "tags" in search_in:
                for tag in note["tags"]:
                    if query_lower in tag.lower():
                        matches = True
                        break

            if matches:
                matching_notes.append(note)

        return matching_notes

    def get_notes_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Get all notes with a specific tag."""
        tag_lower = tag.lower()
        matching_notes = []

        for note in self.get_all_notes():
            for note_tag in note["tags"]:
                if note_tag.lower() == tag_lower:
                    matching_notes.append(note)
                    break

        return matching_notes

    def get_note_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific note by its name (without extension)."""
        for note in self.get_all_notes():
            if note["name"].lower() == name.lower():
                return note
        return None

    def get_vault_stats(self) -> Dict[str, Any]:
        """Get statistics about the vault."""
        notes = self.get_all_notes()

        total_notes = len(notes)
        total_size = sum(note["size"] for note in notes)

        # Collect all tags
        all_tags = set()
        for note in notes:
            all_tags.update(note["tags"])

        # Count note types based on frontmatter
        note_types = {}
        for note in notes:
            note_type = note["frontmatter"].get("type", "note")
            note_types[note_type] = note_types.get(note_type, 0) + 1

        return {
            "total_notes": total_notes,
            "total_size_bytes": total_size,
            "total_tags": len(all_tags),
            "all_tags": sorted(list(all_tags)),
            "note_types": note_types,
            "vault_path": str(self.vault_path),
        }

    def get_backlinks(self, note_name: str) -> List[Dict[str, Any]]:
        """Find all notes that link to the specified note."""
        backlinks = []

        for note in self.get_all_notes():
            for link in note["wikilinks"]:
                if link["target"].lower() == note_name.lower():
                    backlinks.append(
                        {
                            "source_note": note["name"],
                            "source_path": note["path"],
                            "link_text": link["display"],
                            "header": link["header"],
                        }
                    )

        return backlinks

    def get_orphaned_notes(self) -> List[Dict[str, Any]]:
        """Find notes that have no incoming or outgoing links."""
        all_notes = self.get_all_notes()
        linked_notes = set()

        # Collect all linked note names
        for note in all_notes:
            for link in note["wikilinks"]:
                linked_notes.add(link["target"].lower())

        orphaned = []
        for note in all_notes:
            # Check if note has outgoing links
            has_outgoing = len(note["wikilinks"]) > 0

            # Check if note has incoming links
            has_incoming = note["name"].lower() in linked_notes

            if not has_outgoing and not has_incoming:
                orphaned.append(note)

        return orphaned


class ObsidianTemplateEngine:
    """Engine for processing Obsidian templates and variables."""

    @staticmethod
    def process_template_variables(content: str, variables: Dict[str, Any] = None) -> str:
        """Process template variables in content."""
        if variables is None:
            variables = {}

        # Default variables
        now = datetime.now()
        default_vars = {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "datetime": now.strftime("%Y-%m-%d %H:%M"),
            "title": variables.get("title", "Untitled"),
        }

        # Merge with provided variables
        all_vars = {**default_vars, **variables}

        # Replace template variables ({{variable}} format)
        template_pattern = r"\{\{([^}]+)\}\}"

        def replace_var(match):
            var_name = match.group(1).strip()
            return str(all_vars.get(var_name, match.group(0)))

        return re.sub(template_pattern, replace_var, content)

    @staticmethod
    def extract_template_variables(content: str) -> Set[str]:
        """Extract all template variables from content."""
        pattern = r"\{\{([^}]+)\}\}"
        matches = re.finditer(pattern, content)
        return {match.group(1).strip() for match in matches}


class ObsidianConnector:
    """Main connector class for Obsidian vault integration."""

    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        self.scanner = ObsidianVaultScanner(vault_path)
        self.template_engine = ObsidianTemplateEngine()
        self._note_cache = {}
        self._cache_timestamp = None

    def get_notes(
        self, limit: int = None, offset: int = 0, refresh_cache: bool = False
    ) -> List[Dict[str, Any]]:
        """Get notes with optional pagination."""
        if refresh_cache or not self._note_cache:
            self._refresh_note_cache()

        notes = list(self._note_cache.values())

        # Sort by modification date (newest first)
        notes.sort(key=lambda x: x["modified"], reverse=True)

        # Apply pagination
        start_idx = offset
        end_idx = offset + limit if limit else None

        return notes[start_idx:end_idx]

    def search_notes(
        self, query: str, search_in: List[str] = None, limit: int = None
    ) -> List[Dict[str, Any]]:
        """Search notes with optional result limiting."""
        results = self.scanner.search_notes(query, search_in)

        if limit:
            results = results[:limit]

        return results

    def get_note_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific note by name."""
        return self.scanner.get_note_by_name(name)

    def get_notes_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Get all notes with a specific tag."""
        return self.scanner.get_notes_by_tag(tag)

    def get_vault_stats(self) -> Dict[str, Any]:
        """Get comprehensive vault statistics."""
        return self.scanner.get_vault_stats()

    def extract_content_for_flashcards(
        self, note: Dict[str, Any], content_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract content suitable for flashcard generation."""
        if content_types is None:
            content_types = ["headers", "definitions", "lists", "quotes"]

        flashcard_content = []

        # Extract headers as potential question/answer pairs
        if "headers" in content_types:
            for header in note["headers"]:
                if header["level"] <= 3:  # Only H1-H3 headers
                    flashcard_content.append(
                        {
                            "type": "header",
                            "question": f"What is covered under: {header['text']}?",
                            "context": header["text"],
                            "source_note": note["name"],
                            "source_line": header["line_number"],
                        }
                    )

        # Extract definition-like content
        if "definitions" in content_types:
            for block in note["blocks"]:
                if block["type"] == "paragraph":
                    content = block["content"]
                    # Look for definition patterns
                    if re.search(
                        r"\b(is|are|means|refers to|defined as)\b", content, re.IGNORECASE
                    ):
                        # Try to split into term and definition
                        sentences = content.split(".")
                        for sentence in sentences:
                            if re.search(
                                r"\b(is|are|means|refers to|defined as)\b", sentence, re.IGNORECASE
                            ):
                                flashcard_content.append(
                                    {
                                        "type": "definition",
                                        "content": sentence.strip(),
                                        "source_note": note["name"],
                                        "source_line": block["start_line"],
                                    }
                                )

        # Extract list items
        if "lists" in content_types:
            for block in note["blocks"]:
                if block["type"] in ["list", "numbered_list"]:
                    lines = block["content"].split("\n")
                    for line in lines:
                        if line.strip():
                            clean_line = re.sub(r"^\s*[-*+\d.]\s*", "", line)
                            if len(clean_line.split()) > 3:  # Only meaningful list items
                                flashcard_content.append(
                                    {
                                        "type": "list_item",
                                        "content": clean_line,
                                        "source_note": note["name"],
                                        "context": f"Item from list in {note['name']}",
                                    }
                                )

        # Extract quotes
        if "quotes" in content_types:
            for block in note["blocks"]:
                if block["type"] == "quote":
                    clean_quote = re.sub(r"^\s*>\s*", "", block["content"], flags=re.MULTILINE)
                    flashcard_content.append(
                        {
                            "type": "quote",
                            "content": clean_quote,
                            "source_note": note["name"],
                            "source_line": block["start_line"],
                        }
                    )

        return flashcard_content

    def _refresh_note_cache(self):
        """Refresh the internal note cache."""
        notes = self.scanner.get_all_notes()
        self._note_cache = {note["name"]: note for note in notes}
        self._cache_timestamp = datetime.now()

    def is_available(self) -> bool:
        """Check if the vault is accessible."""
        return self.scanner.vault_path.exists()
