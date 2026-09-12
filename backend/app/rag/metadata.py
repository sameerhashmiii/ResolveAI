import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ArticleMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    article_id: str = Field(min_length=1, max_length=50)
    category: str = Field(min_length=1, max_length=100)
    environment: str = Field(min_length=1)
    escalation_criteria: str = Field(min_length=1)
    file: str = Field(min_length=1, max_length=500)
    related_systems: list[str] = Field(min_length=1)
    resolution_guidance: str = Field(min_length=1)
    symptoms: list[str] = Field(min_length=1)
    title: str = Field(min_length=1, max_length=300)
    troubleshooting_steps: list[str] = Field(min_length=1)

    @field_validator(
        "article_id",
        "category",
        "environment",
        "escalation_criteria",
        "file",
        "resolution_guidance",
        "title",
    )
    @classmethod
    def reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("related_systems", "symptoms", "troubleshooting_steps")
    @classmethod
    def reject_blank_items(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("items must not be blank")
        return values


class KnowledgeIndex(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    articles: list[ArticleMetadata] = Field(min_length=1)
    synthetic: bool = True

    @field_validator("articles")
    @classmethod
    def reject_duplicates(cls, articles: list[ArticleMetadata]) -> list[ArticleMetadata]:
        article_ids = [article.article_id for article in articles]
        paths = [article.file for article in articles]
        if len(article_ids) != len(set(article_ids)):
            raise ValueError("duplicate article_id")
        if len(paths) != len(set(paths)):
            raise ValueError("duplicate source path")
        return articles


def load_index(data_dir: Path) -> KnowledgeIndex:
    try:
        value: Any = json.loads((data_dir / "index.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Knowledge index could not be read") from exc
    return KnowledgeIndex.model_validate(value)


def resolve_source(data_dir: Path, source_path: str) -> Path:
    relative = Path(source_path)
    if relative.is_absolute():
        raise ValueError("Absolute knowledge source paths are not allowed")
    root = data_dir.resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root) or candidate == root:
        raise ValueError("Knowledge source path escapes the data directory")
    if not candidate.is_file():
        raise ValueError("Knowledge source file is missing")
    return candidate


def manifest_details(data_dir: Path) -> tuple[str, dict[str, str]]:
    manifest_path = data_dir.parent / "manifest.json"
    if not manifest_path.is_file():
        return "resolveai-phase3-v1", {}
    try:
        raw: Any = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise TypeError
        version = raw.get("dataset_version", "resolveai-phase3-v1")
        checksums = raw.get("checksums", {})
        if not isinstance(version, str) or not isinstance(checksums, dict):
            raise TypeError
        if not all(
            isinstance(key, str) and isinstance(value, str) for key, value in checksums.items()
        ):
            raise TypeError
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError("Dataset manifest is invalid") from exc
    return version, checksums
