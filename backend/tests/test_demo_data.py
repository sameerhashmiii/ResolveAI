import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATOR = PROJECT_ROOT / "scripts" / "generate_demo_data.py"
VALIDATOR = PROJECT_ROOT / "scripts" / "validate_demo_data.py"


def run_script(script: Path, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *(str(arg) for arg in args)],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def relative_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_demo_data_generation_validation_and_reproducibility(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    arguments = (
        "--tickets",
        120,
        "--users",
        40,
        "--incidents",
        8,
        "--knowledge-articles",
        30,
        "--applications",
        15,
        "--seed",
        42,
    )

    generated = run_script(GENERATOR, *arguments, "--output-dir", first)
    assert generated.returncode == 0, generated.stderr
    validated = run_script(VALIDATOR, "--data-dir", first)
    assert validated.returncode == 0, validated.stdout + validated.stderr
    assert "RESULT: PASS" in validated.stdout

    manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    users = read_jsonl(first / "users" / "users.jsonl")
    tickets = read_jsonl(first / "tickets" / "tickets.jsonl")
    incidents = json.loads((first / "incidents" / "incidents.json").read_text(encoding="utf-8"))
    ground_truth = json.loads(
        (first / "evaluation" / "ground_truth.json").read_text(encoding="utf-8")
    )
    locations = json.loads((first / "locations" / "locations.json").read_text(encoding="utf-8"))

    assert manifest["actual_counts"]["tickets"] == 120
    assert manifest["actual_counts"]["users"] == 40
    assert manifest["actual_counts"]["incidents"] == 8
    assert manifest["actual_counts"]["knowledge_articles"] == 30
    assert len(users) == 40
    assert all(user["first_name"] and user["last_name"] and user["location"] for user in users)
    assert len(tickets) == 120
    assert all(
        ticket["ai_analysis"] is None and ticket["ai_confidence"] is None for ticket in tickets
    )
    assert [location["name"] for location in locations] == [
        "Dallas",
        "Austin",
        "New York",
        "Chicago",
        "Atlanta",
        "Seattle",
        "Denver",
        "Phoenix",
        "Boston",
        "San Francisco",
    ]
    assert all(all("root_cause" not in key for key in incident) for incident in incidents)

    primary = next(incident for incident in incidents if incident["incident_id"] == "INC-0001")
    linked = [ticket for ticket in tickets if ticket["incident_id"] == primary["incident_id"]]
    assert linked
    assert len({ticket["category"] for ticket in linked}) >= 2
    assert all(ticket["location_id"] in primary["affected_location_ids"] for ticket in linked)
    primary_truth = next(
        truth for truth in ground_truth["incidents"] if truth["incident_id"] == "INC-0001"
    )
    assert primary_truth["ground_truth_priority"] == "P2"
    assert {case["ticket_id"] for case in ground_truth["cases"]} == {
        ticket["ticket_id"] for ticket in tickets if ticket["incident_id"] is not None
    }
    assert ground_truth["visibility"] == "hidden_non_user_facing_evaluation_only"
    assert {truth["incident_id"] for truth in ground_truth["incidents"]} == {
        incident["incident_id"] for incident in incidents
    }
    hidden_causes = {truth["ground_truth_root_cause"] for truth in ground_truth["incidents"]}
    normal_content = json.dumps(incidents) + json.dumps(tickets)
    assert all(cause not in normal_content for cause in hidden_causes)
    logs = read_jsonl(first / "logs" / "logs.jsonl")
    assert any(
        log["incident_id"] == "INC-0001"
        and "failed to resolve payrollpro.internal.synthetic.invalid" in str(log["message"])
        for log in logs
    )

    regenerated = run_script(GENERATOR, *arguments, "--output-dir", second)
    assert regenerated.returncode == 0, regenerated.stderr
    assert relative_bytes(first) == relative_bytes(second)
    second_manifest = json.loads((second / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["checksums"] == second_manifest["checksums"]

    tickets[0]["user_id"] = "USR-CORRUPTED"
    ticket_path = first / "tickets" / "tickets.jsonl"
    ticket_path.write_text(
        "".join(
            json.dumps(ticket, sort_keys=True, separators=(",", ":")) + "\n" for ticket in tickets
        ),
        encoding="utf-8",
    )
    rejected = run_script(VALIDATOR, "--data-dir", first)
    assert rejected.returncode == 1
    assert "FAIL  All SHA-256 checksums match" in rejected.stdout
    assert (
        "FAIL  Ticket fields, timestamps, AI nulls, and foreign keys are valid" in rejected.stdout
    )
    assert "RESULT: FAIL" in rejected.stdout
