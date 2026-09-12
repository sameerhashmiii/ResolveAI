import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.rag.chunking import chunk_markdown
from app.rag.metadata import KnowledgeIndex, load_index, resolve_source

SOURCE = """# VPN and DNS Guide

**Article ID:** KA-TEST

## Category
VPN / Remote Access

## Symptoms
VPN connects but the internal hostname does not open.

## Troubleshooting Steps
1. Resolve the internal hostname.
2. Compare the DNS server assigned by VPN.

## Resolution Guidance
Restore the approved name-resolution path.

## Escalation Criteria
Escalate when multiple users are affected.
"""


def test_chunking_preserves_headings_bounds_order_and_source_text() -> None:
    chunks = chunk_markdown(SOURCE, max_chars=220, max_sections=2)

    assert 2 <= len(chunks) <= 4
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert chunks[0].heading == "VPN and DNS Guide"
    assert any("## Troubleshooting Steps" in chunk.content for chunk in chunks)
    assert all(chunk.token_count > 0 and len(chunk.content) <= 220 for chunk in chunks)
    sections = [part.strip() for part in SOURCE.split("\n\n")]
    assert all(all(part in SOURCE for part in chunk.content.split("\n\n")) for chunk in chunks)
    assert all(section in "\n\n".join(chunk.content for chunk in chunks) for section in sections)


def _metadata(file: str = "articles/test.md") -> dict[str, object]:
    return {
        "article_id": "KA-TEST",
        "category": "VPN / Remote Access",
        "environment": "Synthetic",
        "escalation_criteria": "Escalate safely",
        "file": file,
        "related_systems": ["VPN"],
        "resolution_guidance": "Resolve safely",
        "symptoms": ["failure"],
        "title": "VPN and DNS Guide",
        "troubleshooting_steps": ["Check status"],
    }


def test_metadata_is_strict_and_rejects_duplicates() -> None:
    with pytest.raises(ValidationError):
        KnowledgeIndex.model_validate({"articles": [{**_metadata(), "unexpected": True}]})
    with pytest.raises(ValidationError):
        KnowledgeIndex.model_validate({"articles": [_metadata(), _metadata()]})


def test_path_resolution_rejects_traversal_and_missing_files(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="escapes"):
        resolve_source(tmp_path, "../secret.md")
    with pytest.raises(ValueError, match="missing"):
        resolve_source(tmp_path, "articles/missing.md")


def test_load_index_rejects_duplicate_source_paths(tmp_path: Path) -> None:
    (tmp_path / "index.json").write_text(
        json.dumps({"articles": [_metadata(), {**_metadata(), "article_id": "KA-OTHER"}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="duplicate source path"):
        load_index(tmp_path)
