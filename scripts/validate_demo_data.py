#!/usr/bin/env python3
"""Validate ResolveAI synthetic demo data and print a readable PASS/FAIL report."""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from demo_data_common import (
    AI_CATEGORY_BY_PRODUCT_CATEGORY,
    CATEGORY_COUNTS,
    LOCATION_NAMES,
    SERVICES,
    checksum,
    generated_files,
    read_jsonl,
    relative,
)

PRIORITIES = {"P1", "P2", "P3", "P4"}
STATUSES = {"new", "open", "in_progress", "resolved", "closed"}
ARTICLE_SECTIONS = [
    "## Category",
    "## Symptoms",
    "## Environment",
    "## Troubleshooting Steps",
    "## Resolution Guidance",
    "## Escalation Criteria",
    "## Related Systems",
]
RESOLUTION_CODE_MARKERS = {
    "configuration_restored": "configuration",
    "service_recovered": "recovered",
    "user_guidance": "guidance",
}


def parse_time(value):
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return parsed


class Report:
    def __init__(self):
        self.failures = []

    def check(self, label, condition, detail=""):
        if condition:
            print("PASS  " + label)
        else:
            message = label + ((": " + detail) if detail else "")
            self.failures.append(message)
            print("FAIL  " + message)


def unique(values):
    values = list(values)
    return len(values) == len(set(values))


def load_data(root):
    with (root / "manifest.json").open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    with (root / "locations" / "locations.json").open(encoding="utf-8") as handle:
        locations = json.load(handle)
    with (root / "applications" / "applications.json").open(encoding="utf-8") as handle:
        applications = json.load(handle)
    with (root / "incidents" / "incidents.json").open(encoding="utf-8") as handle:
        incidents = json.load(handle)
    with (root / "knowledge" / "index.json").open(encoding="utf-8") as handle:
        knowledge = json.load(handle)
    with (root / "evaluation" / "ground_truth.json").open(encoding="utf-8") as handle:
        ground_truth = json.load(handle)
    return {
        "manifest": manifest,
        "locations": locations,
        "applications": applications,
        "users": read_jsonl(root / "users" / "users.jsonl"),
        "incidents": incidents,
        "tickets": read_jsonl(root / "tickets" / "tickets.jsonl"),
        "knowledge": knowledge,
        "telemetry": read_jsonl(root / "telemetry" / "telemetry.jsonl"),
        "logs": read_jsonl(root / "logs" / "logs.jsonl"),
        "ground_truth": ground_truth,
    }


def validate(root):
    report = Report()
    try:
        data = load_data(root)
    except (OSError, ValueError, KeyError, TypeError) as error:
        report.check("Required files are readable", False, str(error))
        return report

    manifest = data["manifest"]
    requested = manifest.get("requested_counts", {})
    print("ResolveAI Phase 3 Synthetic Data Validation")
    print("Data directory: %s" % root)
    print("Requested counts: " + ", ".join("%s=%s" % item for item in sorted(requested.items())))
    print("")

    expected_files = manifest.get("checksums", {})
    actual_paths = {relative(path, root): path for path in generated_files(root)}
    report.check(
        "Manifest schema and synthetic disclaimer",
        manifest.get("schema_version") == "3.0"
        and "synthetic" in manifest.get("synthetic_disclaimer", "").lower(),
    )
    report.check(
        "Manifest lists every generated file",
        set(expected_files) == set(actual_paths),
        "file list differs",
    )
    bad_hashes = [
        name
        for name, expected in expected_files.items()
        if name not in actual_paths or checksum(actual_paths[name]) != expected
    ]
    report.check("All SHA-256 checksums match", not bad_hashes, ", ".join(bad_hashes[:5]))

    locations = data["locations"]
    applications = data["applications"]
    users = data["users"]
    incidents = data["incidents"]
    tickets = data["tickets"]
    articles = data["knowledge"].get("articles", [])
    telemetry = data["telemetry"]
    logs = data["logs"]
    cases = data["ground_truth"].get("cases", [])
    incident_truth = data["ground_truth"].get("incidents", [])
    computed_counts = {
        "locations": len(locations),
        "applications": len(applications),
        "users": len(users),
        "incidents": len(incidents),
        "tickets": len(tickets),
        "knowledge_articles": len(articles),
        "telemetry_records": len(telemetry),
        "log_records": len(logs),
        "ground_truth_cases": len(cases),
    }
    for label in (
        "users",
        "tickets",
        "incidents",
        "knowledge_articles",
        "applications",
        "telemetry_records",
        "log_records",
        "ground_truth_cases",
    ):
        print("%-24s %d" % (label.replace("_", " ").title() + ":", computed_counts[label]))
    print("")
    report.check(
        "Requested entity counts match files",
        all(computed_counts.get(key) == value for key, value in requested.items()),
        str(computed_counts),
    )
    report.check(
        "Manifest actual counts match files", manifest.get("actual_counts") == computed_counts
    )
    actual_distribution = dict(Counter(ticket.get("category") for ticket in tickets))
    report.check(
        "Ticket category distribution is exact",
        actual_distribution == manifest.get("category_distribution"),
    )
    if requested.get("tickets") == 1000:
        report.check("Default category contract is exact", actual_distribution == CATEGORY_COUNTS)

    location_ids = {row.get("location_id") for row in locations}
    application_ids = {row.get("application_id") for row in applications}
    user_ids = {row.get("user_id") for row in users}
    incident_ids = {row.get("incident_id") for row in incidents}
    ticket_ids = {row.get("ticket_id") for row in tickets}
    article_ids = {row.get("article_id") for row in articles}
    report.check(
        "Location IDs and requested cities are exact",
        unique(row.get("location_id") for row in locations)
        and [row.get("name") for row in locations] == LOCATION_NAMES,
    )
    report.check(
        "All entity IDs are unique",
        all(
            [
                unique(row.get("application_id") for row in applications),
                unique(row.get("user_id") for row in users),
                unique(row.get("incident_id") for row in incidents),
                unique(row.get("ticket_id") for row in tickets),
                unique(row.get("article_id") for row in articles),
            ]
        ),
    )
    report.check(
        "Infrastructure is explicitly synthetic",
        all(
            "synthetic" in row.get("infrastructure_notice", "").lower()
            and row.get("vpn_gateway", "").endswith(".invalid")
            for row in locations
        ),
    )
    location_names_by_id = {row.get("location_id"): row.get("name") for row in locations}
    report.check(
        "User identity, location, and manager references are valid",
        all(
            row.get("first_name")
            and row.get("last_name")
            and row.get("name") == "%s %s" % (row["first_name"], row["last_name"])
            and row.get("location_id") in location_ids
            and row.get("location") == location_names_by_id[row["location_id"]]
            and (row.get("manager_id") is None or row.get("manager_id") in user_ids)
            and row.get("manager_id") != row.get("user_id")
            for row in users
        ),
    )
    report.check(
        "Application dependencies reference known services",
        all(set(row.get("dependencies", [])) <= set(SERVICES) for row in applications),
    )

    incident_by_id = {row["incident_id"]: row for row in incidents if "incident_id" in row}
    user_locations = {
        row["user_id"]: row["location_id"]
        for row in users
        if "user_id" in row and "location_id" in row
    }
    incident_valid = True
    try:
        incident_valid = all(
            parse_time(row["start_at"]) < parse_time(row["end_at"])
            and set(row.get("affected_location_ids", [])) <= location_ids
            and set(row.get("affected_user_ids", [])) <= user_ids
            and set(row.get("affected_application_ids", [])) <= application_ids
            and set(row.get("affected_services", [])) <= set(SERVICES)
            and set(row.get("related_ticket_ids", [])) <= ticket_ids
            and all(
                user_locations[user_id] in row["affected_location_ids"]
                for user_id in row.get("affected_user_ids", [])
            )
            for row in incidents
        )
    except (KeyError, TypeError, ValueError):
        incident_valid = False
    report.check("Incident windows and references are valid", incident_valid)
    report.check(
        "Public incidents contain no private root-cause fields",
        all(all("root_cause" not in key.lower() for key in incident) for incident in incidents),
    )
    primary = next((row for row in incidents if row.get("incident_id") == "INC-0001"), {})
    dallas_id = next(
        (row.get("location_id") for row in locations if row.get("name") == "Dallas"), None
    )
    payroll_id = next(
        (row.get("application_id") for row in applications if row.get("name") == "PayrollPro"), None
    )
    report.check(
        "Primary Dallas DNS and PayrollPro scenario exists",
        dallas_id in primary.get("affected_location_ids", [])
        and payroll_id in primary.get("affected_application_ids", [])
        and "DNS" in primary.get("affected_services", []),
    )

    ticket_fk_valid = True
    linked_ticket_ids = set()
    location_names = {row["location_id"]: row["name"] for row in locations}
    try:
        for ticket in tickets:
            ticket_fk_valid = (
                ticket_fk_valid
                and ticket["user_id"] in user_ids
                and ticket["location_id"] in location_ids
                and user_locations[ticket["user_id"]] == ticket["location_id"]
                and ticket.get("location_name") == location_names.get(ticket["location_id"])
                and ticket.get("affected_application_id") in application_ids | {None}
                and ticket.get("incident_id") in incident_ids | {None}
                and set(ticket.get("knowledge_article_ids", [])) <= article_ids
                and ticket.get("category") in CATEGORY_COUNTS
                and ticket.get("priority") in PRIORITIES
                and ticket.get("status") in STATUSES
                and parse_time(ticket["created_at"]) <= parse_time(ticket["updated_at"])
                and ticket.get("ai_analysis") is None
                and ticket.get("ai_confidence") is None
            )
            if ticket["status"] in {"resolved", "closed"}:
                code = ticket.get("resolution_code")
                ticket_fk_valid = (
                    ticket_fk_valid
                    and bool(ticket.get("resolution"))
                    and code in RESOLUTION_CODE_MARKERS
                    and ticket.get("resolution_time_minutes", 0) > 0
                    and RESOLUTION_CODE_MARKERS[code] in ticket["resolution"].lower()
                )
            elif ticket["status"] == "in_progress":
                ticket_fk_valid = ticket_fk_valid and all(
                    ticket.get(field) is None
                    for field in (
                        "resolution",
                        "resolution_code",
                        "resolution_time_minutes",
                    )
                )
            related = ticket.get("related_ticket_ids", [])
            ticket_fk_valid = (
                ticket_fk_valid
                and set(related) <= ticket_ids
                and ticket["ticket_id"] not in related
            )
            if ticket.get("incident_id"):
                linked_ticket_ids.add(ticket["ticket_id"])
                incident = incident_by_id[ticket["incident_id"]]
                ticket_fk_valid = (
                    ticket_fk_valid
                    and ticket["location_id"] in incident["affected_location_ids"]
                    and ticket["user_id"] in incident["affected_user_ids"]
                    and parse_time(incident["start_at"])
                    <= parse_time(ticket["created_at"])
                    <= parse_time(incident["end_at"])
                )
                if ticket.get("affected_application_id"):
                    ticket_fk_valid = (
                        ticket_fk_valid
                        and ticket["affected_application_id"]
                        in incident["affected_application_ids"]
                    )
    except (KeyError, TypeError, ValueError):
        ticket_fk_valid = False
    report.check("Ticket fields, timestamps, AI nulls, and foreign keys are valid", ticket_fk_valid)
    ticket_by_id = {row["ticket_id"]: row for row in tickets if "ticket_id" in row}
    symmetric = all(
        ticket["ticket_id"] in ticket_by_id[peer].get("related_ticket_ids", [])
        and ticket.get("incident_id") is not None
        and ticket.get("incident_id") == ticket_by_id[peer].get("incident_id")
        for ticket in tickets
        for peer in ticket.get("related_ticket_ids", [])
        if peer in ticket_by_id
    )
    report.check(
        "Related ticket links are meaningful and symmetric", symmetric and bool(linked_ticket_ids)
    )
    incident_links_exact = all(
        bool(row.get("related_ticket_ids"))
        and set(row["related_ticket_ids"])
        == {
            ticket["ticket_id"]
            for ticket in tickets
            if ticket.get("incident_id") == row.get("incident_id")
        }
        for row in incidents
    )
    report.check("Incident related-ticket relationships match tickets", incident_links_exact)
    opening_styles = {
        ticket.get("description", "").split(" ", 1)[0]
        for ticket in tickets
        if ticket.get("description")
    }
    wording_varied = (
        len({ticket.get("title") for ticket in tickets})
        >= min(len(tickets), max(3, len(tickets) // 3))
        and len({ticket.get("description") for ticket in tickets})
        >= min(len(tickets), max(3, len(tickets) // 3))
        and len(opening_styles) >= 3
    )
    report.check(
        "Ticket titles, descriptions, and resolutions are meaningfully varied", wording_varied
    )
    resolution_family_coverage = all(
        len(
            {
                ticket.get("resolution_code")
                for ticket in tickets
                if ticket.get("category") == category and ticket.get("resolution_code") is not None
            }
        )
        >= 3
        for category, amount in actual_distribution.items()
        if amount >= 3
    )
    report.check(
        "Each represented category has multiple consistent resolution families",
        resolution_family_coverage,
    )

    knowledge_ok = data["knowledge"].get("synthetic") is True
    indexed_files = set()
    article_contents = []
    for article in articles:
        path = root / "knowledge" / article.get("file", "")
        indexed_files.add(path)
        try:
            content = path.read_text(encoding="utf-8")
            article_contents.append(content)
            knowledge_ok = (
                knowledge_ok and article["article_id"] in content and article["title"] in content
            )
            knowledge_ok = knowledge_ok and all(section in content for section in ARTICLE_SECTIONS)
            knowledge_ok = knowledge_ok and all(
                key in article
                for key in (
                    "category",
                    "symptoms",
                    "environment",
                    "troubleshooting_steps",
                    "resolution_guidance",
                    "escalation_criteria",
                    "related_systems",
                )
            )
        except (OSError, KeyError, TypeError):
            knowledge_ok = False
    actual_article_files = set((root / "knowledge" / "articles").glob("*.md"))
    report.check(
        "Knowledge index, files, metadata, and required sections agree",
        knowledge_ok and indexed_files == actual_article_files,
    )
    knowledge_varied = (
        all("pattern " not in article.get("title", "").lower() for article in articles)
        and len({article.get("title") for article in articles}) == len(articles)
        and len({tuple(article.get("troubleshooting_steps", [])) for article in articles})
        >= min(len(articles), 6)
        and len({article.get("resolution_guidance") for article in articles})
        >= min(len(articles), 6)
    )
    report.check("Knowledge focus topics and guidance are meaningfully varied", knowledge_varied)
    scenario_articles = {
        article["article_id"]
        for article in articles
        if article.get("category") in {"DNS / Name Resolution", "VPN / Remote Access"}
    }
    report.check("Dallas DNS/VPN knowledge coverage exists", len(scenario_articles) >= 2)

    telemetry_ok = True
    incident_telemetry = set()
    normal_seen = False
    try:
        for row in telemetry:
            telemetry_ok = (
                telemetry_ok and row["location_id"] in location_ids and row["service"] in SERVICES
            )
            parse_time(row["timestamp"])
            if row.get("incident_id"):
                incident = incident_by_id[row["incident_id"]]
                incident_telemetry.add(row["incident_id"])
                telemetry_ok = (
                    telemetry_ok
                    and row["location_id"] in incident["affected_location_ids"]
                    and row["service"] in incident["affected_services"]
                )
                telemetry_ok = telemetry_ok and parse_time(incident["start_at"]) <= parse_time(
                    row["timestamp"]
                ) <= parse_time(incident["end_at"])
                telemetry_ok = telemetry_ok and row["error_rate"] > 5
            else:
                normal_seen = True
                telemetry_ok = telemetry_ok and row["error_rate"] < 1
    except (KeyError, TypeError, ValueError):
        telemetry_ok = False
    report.check(
        "Telemetry baselines, spikes, windows, locations, and services correlate",
        telemetry_ok and normal_seen and incident_telemetry == incident_ids,
    )

    logs_ok = True
    incident_logs = set()
    try:
        for row in logs:
            logs_ok = (
                logs_ok
                and row["location_id"] in location_ids
                and row["service"] in SERVICES
                and row["host"].endswith(".invalid")
            )
            parse_time(row["timestamp"])
            if row.get("incident_id"):
                incident = incident_by_id[row["incident_id"]]
                incident_logs.add(row["incident_id"])
                logs_ok = (
                    logs_ok
                    and row["location_id"] in incident["affected_location_ids"]
                    and row["service"] in incident["affected_services"]
                )
                logs_ok = logs_ok and parse_time(incident["start_at"]) <= parse_time(
                    row["timestamp"]
                ) <= parse_time(incident["end_at"])
    except (KeyError, TypeError, ValueError):
        logs_ok = False
    report.check(
        "Synthetic-safe logs correlate to every incident window",
        logs_ok and incident_logs == incident_ids,
    )
    primary_dns_signature = any(
        row.get("incident_id") == "INC-0001"
        and row.get("service") == "DNS"
        and "failed to resolve payrollpro.internal.synthetic.invalid"
        in row.get("message", "").lower()
        for row in logs
    )
    report.check(
        "Primary Dallas DNS logs contain a safe PayrollPro signature", primary_dns_signature
    )

    ground_truth_ok = (
        data["ground_truth"].get("visibility") == "hidden_non_user_facing_evaluation_only"
        and data["ground_truth"].get("schema_version") == "1.0"
        and data["ground_truth"].get("dataset_version")
        == manifest.get("evaluation_dataset_version")
        and manifest.get("evaluation_schema_version") == "1.0"
        and data["ground_truth"].get("synthetic") is True
    )
    truth_ids = [row.get("incident_id") for row in incident_truth]
    hidden_truth_by_id = {row["incident_id"]: row for row in incident_truth if "incident_id" in row}
    ground_truth_ok = (
        ground_truth_ok
        and unique(truth_ids)
        and set(truth_ids) == incident_ids
        and all(
            row.get("ground_truth_root_cause")
            and row.get("ground_truth_category") in CATEGORY_COUNTS
            and row.get("ground_truth_priority") in PRIORITIES
            for row in incident_truth
        )
    )
    case_ticket_ids = set()
    try:
        for case in cases:
            case_ticket_ids.add(case["ticket_id"])
            ticket = ticket_by_id[case["ticket_id"]]
            hidden_incident = hidden_truth_by_id[case["incident_id"]]
            ground_truth_ok = (
                ground_truth_ok
                and case["ticket_id"] in linked_ticket_ids
                and ticket["incident_id"] == case["incident_id"]
                and case["expected_category"] == ticket["category"]
                and case["expected_ai_category"]
                == AI_CATEGORY_BY_PRODUCT_CATEGORY[ticket["category"]]
                and case["expected_priority"] == ticket["priority"]
                and case["root_cause_key"] == hidden_incident["ground_truth_root_cause"]
                and set(case["relevant_knowledge_article_ids"]) <= article_ids
                and set(case) == {
                    "ticket_id",
                    "incident_id",
                    "root_cause_key",
                    "expected_category",
                    "expected_ai_category",
                    "expected_priority",
                    "relevant_knowledge_article_ids",
                    "response_input",
                    "response_rubric",
                }
                and set(case["response_input"]) == {
                    "probable_root_cause",
                    "recommendation",
                    "limitations",
                    "requires_escalation",
                }
                and set(case["response_rubric"]) == {
                    "require_uncertainty",
                    "prohibit_completed_actions",
                    "require_professional_format",
                    "required_recommendation_terms",
                    "require_escalation_language",
                }
            )
    except (KeyError, TypeError):
        ground_truth_ok = False
    report.check(
        "Hidden incident and ticket ground truth is complete and consistent",
        ground_truth_ok and case_ticket_ids == linked_ticket_ids and bool(cases),
    )
    exposed_text = (
        json.dumps(tickets).lower()
        + json.dumps(incidents).lower()
        + json.dumps(data["knowledge"]).lower()
        + "\n".join(article_contents).lower()
    )
    roots_hidden = ground_truth_ok and all(
        row.get("ground_truth_root_cause", "").lower() not in exposed_text for row in incident_truth
    )
    report.check("Ground-truth root-cause keys are absent from user-facing text", roots_hidden)
    all_incidents_covered = all(
        incident.get("related_ticket_ids")
        and incident["incident_id"] in incident_telemetry
        and incident["incident_id"] in incident_logs
        and incident["incident_id"] in hidden_truth_by_id
        for incident in incidents
    )
    report.check(
        "Every incident has tickets, telemetry, logs, and hidden ground truth",
        all_incidents_covered,
    )

    print("")
    if report.failures:
        print(
            "RESULT: FAIL (%d check%s failed)"
            % (len(report.failures), "" if len(report.failures) == 1 else "s")
        )
    else:
        print(
            "RESULT: PASS (%d tickets, %d incidents, %d knowledge articles)"
            % (len(tickets), len(incidents), len(articles))
        )
    return report


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data"
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    report = validate(args.data_dir.resolve())
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
