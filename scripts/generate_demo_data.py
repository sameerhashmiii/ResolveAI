#!/usr/bin/env python3
"""Generate deterministic, wholly synthetic enterprise support demo data."""

import argparse
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from demo_data_builders import (
    allocate_categories,
    build_applications,
    build_ground_truth,
    build_incidents,
    build_knowledge,
    build_locations,
    build_telemetry_and_logs,
    build_tickets,
    build_users,
    clean_output,
    iso,
)
from demo_data_catalog import DISCLAIMER
from demo_data_common import (
    APP_NAMES,
    checksum,
    generated_files,
    relative,
    write_json,
    write_jsonl,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickets", type=int, default=1000)
    parser.add_argument("--users", type=int, default=250)
    parser.add_argument("--incidents", type=int, default=25)
    parser.add_argument("--knowledge-articles", type=int, default=100)
    parser.add_argument("--applications", type=int, default=15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
    )
    args = parser.parse_args(argv)
    if args.users < 10:
        parser.error("--users must be at least 10 so every default location has a user")
    if args.incidents < 1 or args.incidents > 100:
        parser.error("--incidents must be between 1 and 100")
    if args.tickets < args.incidents * 4:
        parser.error(
            "--tickets must be at least four times --incidents so every incident "
            "has a category-compatible ticket"
        )
    if args.knowledge_articles < 15:
        parser.error("--knowledge-articles must be at least 15 to cover every ticket category")
    if args.applications < 5 or args.applications > len(APP_NAMES):
        parser.error(
            "--applications must be between 5 and %d so the primary PayrollPro "
            "scenario is valid" % len(APP_NAMES)
        )
    return args


def main(argv=None):
    args = parse_args(argv)
    rng = random.Random(args.seed)
    output = args.output_dir.resolve()
    project_root = Path(__file__).resolve().parents[1]
    if output in {project_root, project_root.parent, Path.home(), Path(output.anchor)}:
        raise SystemExit("Refusing to generate into a source, home, or filesystem root directory")
    clean_output(output)
    simulation_start = datetime(2026, 9, 1, tzinfo=timezone.utc) + timedelta(days=args.seed % 3)
    locations = build_locations()
    applications = build_applications(args.applications)
    users = build_users(args.users, locations)
    incidents = build_incidents(args.incidents, simulation_start, locations, applications, users)
    relevant_articles = build_knowledge(args.knowledge_articles, output)
    distribution = allocate_categories(args.tickets)
    tickets = build_tickets(
        args.tickets,
        distribution,
        incidents,
        users,
        locations,
        applications,
        relevant_articles,
        rng,
        simulation_start,
    )
    telemetry, logs = build_telemetry_and_logs(simulation_start, incidents, locations)
    ground_truth = build_ground_truth(incidents, tickets, relevant_articles)

    write_json(output / "locations" / "locations.json", locations)
    write_json(output / "applications" / "applications.json", applications)
    write_jsonl(output / "users" / "users.jsonl", users)
    public_incidents = [
        {key: value for key, value in incident.items() if not key.startswith("_")}
        for incident in incidents
    ]
    write_json(output / "incidents" / "incidents.json", public_incidents)
    write_jsonl(output / "tickets" / "tickets.jsonl", tickets)
    write_jsonl(output / "telemetry" / "telemetry.jsonl", telemetry)
    write_jsonl(output / "logs" / "logs.jsonl", logs)
    write_json(output / "evaluation" / "ground_truth.json", ground_truth)

    actual = {
        "locations": len(locations),
        "applications": len(applications),
        "users": len(users),
        "incidents": len(incidents),
        "tickets": len(tickets),
        "knowledge_articles": args.knowledge_articles,
        "telemetry_records": len(telemetry),
        "log_records": len(logs),
        "ground_truth_cases": len(ground_truth["cases"]),
    }
    files = {relative(path, output): checksum(path) for path in generated_files(output)}
    manifest = {
        "schema_version": "3.0",
        "dataset_version": "resolveai-phase3-v1",
        "evaluation_dataset_version": ground_truth["dataset_version"],
        "evaluation_schema_version": ground_truth["schema_version"],
        "seed": args.seed,
        "generated_at": iso(simulation_start - timedelta(days=1)),
        "simulation_window": {
            "start": iso(simulation_start),
            "end": telemetry[-1]["timestamp"],
        },
        "generator": "scripts/generate_demo_data.py",
        "synthetic_disclaimer": DISCLAIMER,
        "requested_counts": {
            "locations": 10,
            "applications": args.applications,
            "users": args.users,
            "incidents": args.incidents,
            "tickets": args.tickets,
            "knowledge_articles": args.knowledge_articles,
        },
        "actual_counts": actual,
        "category_distribution": distribution,
        "checksums": files,
    }
    write_json(output / "manifest.json", manifest)
    print(
        "Generated %d synthetic tickets and %d telemetry records in %s"
        % (len(tickets), len(telemetry), output)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
