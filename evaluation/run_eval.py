#!/usr/bin/env python3
"""Run the reproducible Phase 9 hidden synthetic evaluation."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import update  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.ai.policy import assign_priority  # noqa: E402
from app.ai.providers import InvalidProviderResponse, LocalDemoProvider  # noqa: E402
from app.ai.schemas import Category, TicketAnalysisInput  # noqa: E402
from app.models.evaluation import EvaluationRun  # noqa: E402
from app.response_generation.providers import (  # noqa: E402
    LocalResponseProvider,
    validate_response_safety,
)
from app.response_generation.schemas import ResponseGenerationInput  # noqa: E402
from app.services.knowledge import KnowledgeSearchService  # noqa: E402

RUNNER_VERSION = "phase9-v1"
WORKFLOW_VERSION = "local-demo-v1"
DATASET_PATH = ROOT / "data" / "evaluation" / "ground_truth.json"
MANIFEST_PATH = ROOT / "data" / "manifest.json"
TICKETS_PATH = ROOT / "data" / "tickets" / "tickets.jsonl"
AI_CATEGORIES = {item.value for item in Category}
PRODUCT_TO_AI = {
    "VPN / Remote Access": "vpn",
    "Password / MFA": "password",
    "Wi-Fi / Wireless": "wifi",
    "Application Access": "account_access",
    "Outlook / Email": "email",
    "Laptop / Endpoint": "hardware",
    "Network Connectivity": "network",
    "Microsoft 365": "application",
    "Account Lockout": "account_access",
    "Software Installation": "software",
    "Printer / Peripheral": "hardware",
    "DNS / Name Resolution": "network",
    "File / Share Access": "account_access",
    "Security Alerts": "security",
    "Other": "other",
}


def classification_metrics(expected: list[str], predicted: list[str]) -> dict[str, Any]:
    if len(expected) != len(predicted):
        raise ValueError("classification inputs must have equal length")
    confusion: dict[str, dict[str, int]] = {}
    for truth, prediction in zip(expected, predicted, strict=True):
        row = confusion.setdefault(truth, {})
        row[prediction] = row.get(prediction, 0) + 1
    confusion = {
        truth: dict(sorted(predictions.items())) for truth, predictions in sorted(confusion.items())
    }
    return {
        "accuracy": round(
            sum(a == b for a, b in zip(expected, predicted, strict=True)) / len(expected), 8
        )
        if expected
        else None,
        "confusion_matrix": confusion,
        "eligible": len(expected),
    }


def priority_metrics(expected: list[str], predicted: list[str]) -> dict[str, Any]:
    if len(expected) != len(predicted):
        raise ValueError("priority inputs must have equal length")
    rank = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}
    if any(value not in rank for value in expected + predicted):
        raise ValueError("invalid priority")
    total = len(expected)
    correct = sum(a == b for a, b in zip(expected, predicted, strict=True))
    under = sum(rank[b] > rank[a] for a, b in zip(expected, predicted, strict=True))
    return {
        "accuracy": round(correct / total, 8) if total else None,
        "under_prioritization_rate": round(under / total, 8) if total else None,
        "under_prioritized": under,
        "eligible": total,
    }


def retrieval_metrics(
    cases: list[tuple[list[str], list[str]]], *, k: int = 5
) -> dict[str, Any]:
    if k < 1:
        raise ValueError("k must be positive")
    recalls: list[float] = []
    precisions: list[float] = []
    reciprocal_ranks: list[float] = []
    for relevant_values, retrieved_values in cases:
        relevant = set(relevant_values)
        if not relevant:
            continue
        retrieved = list(dict.fromkeys(retrieved_values))[:k]
        hits = relevant.intersection(retrieved)
        recalls.append(len(hits) / len(relevant))
        precisions.append(len(hits) / k)
        reciprocal_ranks.append(
            next(
                (1 / rank for rank, article in enumerate(retrieved, 1) if article in relevant),
                0.0,
            )
        )
    eligible = len(recalls)
    return {
        f"recall_at_{k}": round(sum(recalls) / eligible, 8) if eligible else None,
        f"precision_at_{k}": round(sum(precisions) / eligible, 8) if eligible else None,
        "mrr": round(sum(reciprocal_ranks) / eligible, 8) if eligible else None,
        "eligible": eligible,
    }


def score_response_rubric(body: str, rubric: dict[str, Any]) -> dict[str, bool]:
    normalized = body.casefold()
    try:
        validate_response_safety(body)
        safe = True
    except InvalidProviderResponse:
        safe = False
    results = {
        "uncertainty": (not rubric["require_uncertainty"])
        or any(term in normalized for term in ("appears", "probable", "based on evidence")),
        "no_completed_action_claim": (not rubric["prohibit_completed_actions"]) or safe,
        "recommendation_grounding": all(
            term.casefold() in normalized for term in rubric["required_recommendation_terms"]
        ),
        "escalation_language": (not rubric["require_escalation_language"])
        or "escalat" in normalized,
        "professional_format": (not rubric["require_professional_format"])
        or (normalized.startswith("hi ") and "regards," in normalized),
    }
    results["overall"] = all(results.values())
    return results


def aggregate_rubrics(scores: list[dict[str, bool]]) -> dict[str, Any]:
    if not scores:
        return {"eligible": 0, "pass_rates": {}}
    names = sorted(scores[0])
    return {
        "eligible": len(scores),
        "pass_rates": {
            name: round(sum(score[name] for score in scores) / len(scores), 8) for name in names
        },
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_dataset() -> tuple[dict[str, Any], str]:
    raw = DATASET_PATH.read_bytes()
    checksum = hashlib.sha256(raw).hexdigest()
    dataset = json.loads(raw)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    _require(
        checksum == manifest.get("checksums", {}).get("evaluation/ground_truth.json"),
        "evaluation dataset checksum does not match manifest",
    )
    _require(
        set(dataset)
        == {"schema_version", "dataset_version", "visibility", "synthetic", "incidents", "cases"},
        "evaluation dataset has unexpected top-level fields",
    )
    _require(dataset["schema_version"] == "1.0", "unsupported evaluation schema version")
    _require(
        dataset["dataset_version"] == manifest.get("evaluation_dataset_version"),
        "evaluation dataset version does not match manifest",
    )
    _require(
        dataset["visibility"] == "hidden_non_user_facing_evaluation_only",
        "dataset is not hidden",
    )
    _require(dataset["synthetic"] is True, "dataset must be synthetic")
    _require(
        isinstance(dataset["cases"], list) and len(dataset["cases"]) >= 100,
        "at least 100 cases required",
    )
    _require(isinstance(dataset["incidents"], list), "incidents must be a list")
    incident_keys = {
        "incident_id", "ground_truth_root_cause", "ground_truth_category", "ground_truth_priority"
    }
    for incident in dataset["incidents"]:
        _require(
            isinstance(incident, dict) and set(incident) == incident_keys,
            "invalid incident schema",
        )
        _require(incident["ground_truth_category"] in PRODUCT_TO_AI, "invalid incident category")
        _require(
            incident["ground_truth_priority"] in {"P1", "P2", "P3", "P4"},
            "invalid incident priority",
        )
        _require(
            all(
                isinstance(incident[field], str) and bool(incident[field])
                for field in incident_keys
            ),
            "invalid incident values",
        )
    incident_ids = {incident["incident_id"] for incident in dataset["incidents"]}
    _require(len(incident_ids) == len(dataset["incidents"]), "duplicate evaluation incident")
    case_keys = {
        "ticket_id", "incident_id", "root_cause_key", "expected_category", "expected_ai_category",
        "expected_priority", "relevant_knowledge_article_ids", "response_input", "response_rubric",
    }
    response_keys = {"probable_root_cause", "recommendation", "limitations", "requires_escalation"}
    rubric_keys = {
        "require_uncertainty", "prohibit_completed_actions", "require_professional_format",
        "required_recommendation_terms", "require_escalation_language",
    }
    seen: set[str] = set()
    for case in dataset["cases"]:
        _require(isinstance(case, dict) and set(case) == case_keys, "invalid case schema")
        _require(case["ticket_id"] not in seen, "duplicate evaluation ticket")
        seen.add(case["ticket_id"])
        _require(
            all(
                isinstance(case[field], str) and bool(case[field])
                for field in (
                    "ticket_id",
                    "incident_id",
                    "root_cause_key",
                    "expected_category",
                    "expected_ai_category",
                    "expected_priority",
                )
            ),
            "invalid case values",
        )
        _require(case["incident_id"] in incident_ids, "case references an unknown incident")
        _require(case["expected_category"] in PRODUCT_TO_AI, "invalid product category")
        _require(case["expected_ai_category"] in AI_CATEGORIES, "invalid AI category")
        _require(
            case["expected_ai_category"] == PRODUCT_TO_AI[case["expected_category"]],
            "product and AI taxonomy labels disagree",
        )
        _require(case["expected_priority"] in {"P1", "P2", "P3", "P4"}, "invalid priority")
        _require(
            isinstance(case["relevant_knowledge_article_ids"], list)
            and bool(case["relevant_knowledge_article_ids"]),
            "relevant article IDs required",
        )
        _require(set(case["response_input"]) == response_keys, "invalid response input schema")
        _require(set(case["response_rubric"]) == rubric_keys, "invalid response rubric schema")
        _require(
            isinstance(case["response_input"]["probable_root_cause"], str)
            and isinstance(case["response_input"]["recommendation"], str)
            and isinstance(case["response_input"]["limitations"], list)
            and isinstance(case["response_input"]["requires_escalation"], bool),
            "invalid response input values",
        )
        _require(
            isinstance(case["response_rubric"]["required_recommendation_terms"], list),
            "rubric terms must be a list",
        )
        _require(
            all(
                isinstance(case["response_rubric"][field], bool)
                for field in (
                    "require_uncertainty",
                    "prohibit_completed_actions",
                    "require_professional_format",
                    "require_escalation_language",
                )
            )
            and all(
                isinstance(term, str) and bool(term)
                for term in case["response_rubric"]["required_recommendation_terms"]
            ),
            "invalid response rubric values",
        )
    return dataset, checksum


def _load_tickets() -> dict[str, dict[str, Any]]:
    with TICKETS_PATH.open(encoding="utf-8") as handle:
        rows = (json.loads(line) for line in handle if line.strip())
        return {row["ticket_id"]: row for row in rows}


async def execute(limit: int | None) -> dict[str, Any]:
    dataset, checksum = load_dataset()
    cases = dataset["cases"][:limit]
    tickets = _load_tickets()
    _require(all(case["ticket_id"] in tickets for case in cases), "evaluation ticket is missing")
    database_url = os.environ.get("RESOLVEAI_DATABASE_URL")
    if database_url is None or not database_url:
        raise ValueError("RESOLVEAI_DATABASE_URL is required")
    provider = LocalDemoProvider()
    response_provider = LocalResponseProvider()
    methodology = {
        "classification": "exact match against explicit AI taxonomy label",
        "priority": (
            "production deterministic policy; under-prioritization means a less urgent prediction"
        ),
        "retrieval": (
            "production DB-backed local-hash-v1 hybrid retrieval; top 10 chunks requested, "
            "without ground-truth category filtering, then deduplicated by article for metrics "
            "at k=5"
        ),
        "response": "deterministic safety, uncertainty, grounding, escalation, and format rubric",
        "case_selection": "first N cases in deterministic dataset order",
        "stores_case_artifacts": False,
    }
    engine = create_async_engine(database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    started_at = datetime.now(UTC)
    run = EvaluationRun(
        dataset_version=dataset["dataset_version"], dataset_checksum=checksum,
        runner_version=RUNNER_VERSION, workflow_version=WORKFLOW_VERSION,
        provider=provider.name, model=provider.model, status="running", synthetic=True,
        sample_count=len(cases), methodology=methodology, metrics={}, started_at=started_at,
    )
    async with sessions() as db:
        db.add(run)
        await db.commit()
        run_id = run.id
    try:
        expected_categories: list[str] = []
        predicted_categories: list[str] = []
        expected_priorities: list[str] = []
        predicted_priorities: list[str] = []
        retrieval_cases: list[tuple[list[str], list[str]]] = []
        rubric_scores: list[dict[str, bool]] = []
        async with sessions() as db:
            knowledge = KnowledgeSearchService(db)
            embedding_model = knowledge.embedder.name
            for case in cases:
                ticket = tickets[case["ticket_id"]]
                analysis_input = TicketAnalysisInput(
                    title=ticket["title"], description=ticket["description"],
                    requester_name="Synthetic requester", location=ticket.get("location_name"),
                    device=ticket.get("affected_device"), application=None,
                )
                signals = await provider.analyze(analysis_input)
                priority = assign_priority(signals.priority_factors, signals.entities.urgency)
                search = await knowledge.search(
                    f"{ticket['title']} {ticket['description']}", None, 10
                )
                retrieved = [item.article_id for item in search.items]
                response_input = case["response_input"]
                generated = await response_provider.generate(
                    ResponseGenerationInput(
                        ticket_id=uuid5(NAMESPACE_URL, case["ticket_id"]),
                        requester_name="Synthetic requester", title=ticket["title"],
                        description=ticket["description"], **response_input,
                    )
                )
                expected_categories.append(case["expected_ai_category"])
                predicted_categories.append(signals.category.value)
                expected_priorities.append(case["expected_priority"])
                predicted_priorities.append(priority.value.upper())
                retrieval_cases.append((case["relevant_knowledge_article_ids"], retrieved))
                rubric_scores.append(score_response_rubric(generated.body, case["response_rubric"]))
        metrics = {
            "classification": classification_metrics(expected_categories, predicted_categories),
            "priority": priority_metrics(expected_priorities, predicted_priorities),
            "retrieval": retrieval_metrics(retrieval_cases),
            "response_rubric": aggregate_rubrics(rubric_scores),
        }
        async with sessions() as db:
            await db.execute(
                update(EvaluationRun).where(EvaluationRun.id == run_id).values(
                    status="completed", metrics=metrics, completed_at=datetime.now(UTC)
                )
            )
            await db.commit()
        return {
            "provenance": {
                "dataset_version": dataset["dataset_version"], "dataset_checksum": checksum,
                "schema_version": dataset["schema_version"], "runner_version": RUNNER_VERSION,
                "workflow_version": WORKFLOW_VERSION, "provider": provider.name,
                "model": provider.model, "response_provider": response_provider.name,
                "embedding_model": embedding_model, "synthetic": True,
            },
            "sample_count": len(cases), "methodology": methodology, "metrics": metrics,
        }
    except Exception:
        async with sessions() as db:
            await db.execute(
                update(EvaluationRun).where(EvaluationRun.id == run_id).values(
                    status="failed", error_code="EVALUATION_EXECUTION_FAILED",
                    completed_at=datetime.now(UTC)
                )
            )
            await db.commit()
        raise
    finally:
        await engine.dispose()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    if args.limit is not None and not 1 <= args.limit <= 150:
        parser.error("--limit must be between 1 and 150")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = asyncio.run(execute(args.limit))
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        sys.stdout.write(rendered)
        return 0
    except Exception as exc:
        sys.stderr.write(f"evaluation failed: {type(exc).__name__}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
