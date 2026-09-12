from pathlib import Path

import pytest
from pydantic import ValidationError

from app.demo.corpus import _read_checked, _safe_file, load_operational_corpus
from app.demo.schemas import Manifest, TelemetryRow
from app.rag.embeddings import LocalHashEmbedding


def operational_data_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data"


def test_current_operational_corpus_validates_expected_counts() -> None:
    corpus = load_operational_corpus(operational_data_dir())
    assert corpus.counts == {
        "locations": 10,
        "applications": 15,
        "tickets": 1000,
        "incidents": 25,
        "telemetry": 10800,
        "logs": 2767,
    }
    assert len(LocalHashEmbedding().embed("ticket title and description")) == 384


def test_operational_validation_rejects_malformed_values() -> None:
    with pytest.raises(ValidationError):
        TelemetryRow.model_validate(
            {
                "timestamp": "2026-09-01T00:00:00Z",
                "service": "VPN",
                "location_id": "LOC-001",
                "availability": 101,
                "latency_ms": -1,
                "error_rate": 0,
                "incident_id": None,
            }
        )


def test_operational_paths_reject_traversal_and_ground_truth() -> None:
    root = operational_data_dir()
    with pytest.raises(ValueError, match="escapes"):
        _safe_file(root, "../outside.json")
    with pytest.raises(ValueError, match="forbidden"):
        _safe_file(root, "evaluation/ground_truth.json")


def test_operational_file_checksum_is_mandatory(tmp_path: Path) -> None:
    source = tmp_path / "locations"
    source.mkdir()
    (source / "locations.json").write_text("[]", encoding="utf-8")
    manifest = Manifest.model_validate(
        {
            "actual_counts": {},
            "category_distribution": {},
            "checksums": {"locations/locations.json": "0" * 64},
            "dataset_version": "test-v1",
            "generated_at": "2026-09-01T00:00:00Z",
            "generator": "test",
            "requested_counts": {},
            "schema_version": "3.0",
            "seed": 42,
            "simulation_window": {
                "start": "2026-09-01T00:00:00Z",
                "end": "2026-09-02T00:00:00Z",
            },
            "synthetic_disclaimer": "Synthetic test data",
        }
    )
    with pytest.raises(ValueError, match="checksum mismatch"):
        _read_checked(tmp_path, "locations/locations.json", manifest)
