import sys
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.run_eval import (  # noqa: E402
    AI_CATEGORIES,
    PRODUCT_TO_AI,
    aggregate_rubrics,
    classification_metrics,
    load_dataset,
    priority_metrics,
    retrieval_metrics,
    score_response_rubric,
)
from sqlalchemy import CheckConstraint, Table  # noqa: E402

from app.models.evaluation import EvaluationRun  # noqa: E402


def test_hidden_dataset_count_schema_and_taxonomy() -> None:
    dataset, checksum = load_dataset()

    assert len(dataset["cases"]) == 150
    assert len(checksum) == 64
    assert dataset["schema_version"] == "1.0"
    assert dataset["dataset_version"] == "resolveai-phase9-eval-v1"
    assert dataset["synthetic"] is True
    assert dataset["visibility"] == "hidden_non_user_facing_evaluation_only"
    assert {case["expected_ai_category"] for case in dataset["cases"]} <= AI_CATEGORIES
    assert all(
        case["expected_ai_category"] == PRODUCT_TO_AI[case["expected_category"]]
        for case in dataset["cases"]
    )
    assert all("resolution" not in case["response_input"] for case in dataset["cases"])


def test_metric_helpers_are_reproducible_and_handle_empty_inputs() -> None:
    expected = ["vpn", "email", "vpn"]
    predicted = ["vpn", "other", "email"]
    first = classification_metrics(expected, predicted)

    assert first == classification_metrics(expected, predicted)
    assert first["accuracy"] == 0.33333333
    assert classification_metrics([], []) == {
        "accuracy": None,
        "confusion_matrix": {},
        "eligible": 0,
    }
    assert priority_metrics([], [])["under_prioritization_rate"] is None
    assert retrieval_metrics([]) == {
        "recall_at_5": None,
        "precision_at_5": None,
        "mrr": None,
        "eligible": 0,
    }


def test_priority_under_prioritization() -> None:
    metrics = priority_metrics(["P1", "P3", "P4"], ["P2", "P2", "P4"])

    assert metrics == {
        "accuracy": 0.33333333,
        "under_prioritization_rate": 0.33333333,
        "under_prioritized": 1,
        "eligible": 3,
    }


def test_retrieval_metrics_deduplicate_articles() -> None:
    metrics = retrieval_metrics([(["KA-1", "KA-2"], ["KA-X", "KA-1", "KA-1", "KA-2"])])

    assert metrics == {
        "recall_at_5": 1.0,
        "precision_at_5": 0.4,
        "mrr": 0.5,
        "eligible": 1,
    }


def test_response_rubric_pass_and_failure() -> None:
    rubric = {
        "require_uncertainty": True,
        "prohibit_completed_actions": True,
        "require_professional_format": True,
        "required_recommendation_terms": ["approved vpn diagnostic checklist"],
        "require_escalation_language": True,
    }
    safe = (
        "Hi there,\n\nBased on evidence, the probable issue appears temporary. Please follow the "
        "approved VPN diagnostic checklist and escalate if it persists.\n\nRegards,\nSupport Team"
    )
    unsafe = "We have reset your access and fixed the issue."

    assert score_response_rubric(safe, rubric)["overall"] is True
    assert score_response_rubric(unsafe, rubric)["overall"] is False
    aggregate = aggregate_rubrics([
        score_response_rubric(safe, rubric),
        score_response_rubric(unsafe, rubric),
    ])
    assert aggregate["eligible"] == 2
    assert aggregate["pass_rates"]["overall"] == 0.5


def test_evaluation_model_uses_string_status_and_constraints() -> None:
    table = cast(Table, EvaluationRun.__table__)
    constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert table.c.status.type.python_type is str
    assert table.c.methodology.nullable is False
    assert table.c.metrics.nullable is False
    assert "ck_evaluation_runs_lifecycle" in constraints
    assert "ck_evaluation_runs_synthetic" in constraints
    assert "ck_evaluation_runs_timestamps" in constraints
    assert {index.name for index in table.indexes} == {
        "ix_evaluation_runs_status_created",
        "ix_evaluation_runs_dataset_created",
    }


def test_ground_truth_is_not_part_of_product_ingestion_paths() -> None:
    common = Path(__file__).resolve().parents[2] / "scripts" / "demo_data_common.py"
    source = common.read_text(encoding="utf-8")

    assert '"evaluation"' in source
    assert "ground_truth.json" not in source
