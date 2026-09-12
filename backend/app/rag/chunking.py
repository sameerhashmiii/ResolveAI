import re
from dataclasses import dataclass

from app.rag.embeddings import technical_tokens

HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$", re.MULTILINE)


@dataclass(frozen=True)
class SourceChunk:
    chunk_index: int
    heading: str | None
    content: str
    token_count: int


@dataclass(frozen=True)
class _Section:
    heading: str | None
    content: str


def _sections(markdown: str) -> list[_Section]:
    matches = list(HEADING.finditer(markdown))
    if not matches:
        return [_Section(None, markdown.strip())]
    sections: list[_Section] = []
    prefix = markdown[: matches[0].start()].strip()
    if prefix:
        sections.append(_Section(None, prefix))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        content = markdown[match.start() : end].strip()
        sections.append(_Section(match.group(2).strip(), content))
    return sections


def _bounded(section: _Section, max_chars: int) -> list[_Section]:
    if len(section.content) <= max_chars:
        return [section]
    lines = section.content.splitlines(keepends=True)
    values: list[_Section] = []
    current = ""
    for line in lines:
        pieces = [line[index : index + max_chars] for index in range(0, len(line), max_chars)]
        for piece in pieces:
            if current and len(current) + len(piece) > max_chars:
                values.append(_Section(section.heading if not values else None, current.strip()))
                current = ""
            current += piece
    if current.strip():
        values.append(_Section(section.heading if not values else None, current.strip()))
    return values


def chunk_markdown(
    markdown: str, *, max_chars: int = 1200, max_sections: int = 3
) -> list[SourceChunk]:
    if not markdown.strip():
        raise ValueError("Markdown source must not be empty")
    if max_chars < 100 or max_sections < 1:
        raise ValueError("Invalid chunk bounds")
    sections = [part for section in _sections(markdown) for part in _bounded(section, max_chars)]
    groups: list[list[_Section]] = []
    current: list[_Section] = []
    current_length = 0
    for section in sections:
        separator = 2 if current else 0
        if current and (
            len(current) >= max_sections
            or current_length + separator + len(section.content) > max_chars
        ):
            groups.append(current)
            current = []
            current_length = 0
            separator = 0
        current.append(section)
        current_length += separator + len(section.content)
    if current:
        groups.append(current)
    chunks: list[SourceChunk] = []
    for index, group in enumerate(groups):
        content = "\n\n".join(section.content for section in group)
        count = len(technical_tokens(content))
        if not content or count == 0:
            raise ValueError("Markdown chunk contains no searchable text")
        heading = next((section.heading for section in group if section.heading), None)
        chunks.append(SourceChunk(index, heading, content, count))
    return chunks
