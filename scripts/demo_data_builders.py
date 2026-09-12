"""Deterministic builders for ResolveAI synthetic enterprise data."""

import math
import shutil
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from demo_data_catalog import (
    ARTICLE_TEMPLATES,
    CATEGORY_DETAILS,
    DEPARTMENTS,
    FIRST_NAMES,
    INCIDENT_PROFILES,
    JOB_TITLES,
    LAST_NAMES,
    STATUSES,
)
from demo_data_common import (
    APP_NAMES,
    CATEGORY_COUNTS,
    GENERATED_PATHS,
    LOCATION_NAMES,
    SERVICES,
    write_json,
)


def iso(value):
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def allocate_categories(total):
    base_total = sum(CATEGORY_COUNTS.values())
    raw = {key: total * value / base_total for key, value in CATEGORY_COUNTS.items()}
    result = {key: int(value) for key, value in raw.items()}
    remaining = total - sum(result.values())
    order = sorted(
        raw, key=lambda key: (-(raw[key] - result[key]), list(CATEGORY_COUNTS).index(key))
    )
    for key in order[:remaining]:
        result[key] += 1
    return result


def clean_output(output):
    output.mkdir(parents=True, exist_ok=True)
    for name in GENERATED_PATHS:
        target = output / name
        if target.is_dir():
            shutil.rmtree(str(target))
        elif target.exists():
            target.unlink()


def build_locations():
    rows = []
    for index, city in enumerate(LOCATION_NAMES, 1):
        rows.append(
            {
                "location_id": "LOC-%03d" % index,
                "name": city,
                "infrastructure_notice": "Synthetic office infrastructure; not routable or production-derived.",
                "office_network": "resolve-demo-%02d" % index,
                "subnet": "192.0.2.%d/28" % (index * 16),
                "wifi_ssids": ["ResolveAI-Demo", "ResolveAI-Demo-Guest"],
                "vpn_gateway": "vpn-%s.synthetic.invalid" % city.lower().replace(" ", "-"),
                "dns_servers": [
                    "dns-a-%02d.synthetic.invalid" % index,
                    "dns-b-%02d.synthetic.invalid" % index,
                ],
                "access_patterns": ["office_lan", "corporate_wifi", "synthetic_vpn"],
            }
        )
    return rows


def build_applications(count):
    dependency_map = {
        "PayrollPro": ["DNS", "Active Directory"],
        "CRMOne": ["CRM", "Active Directory"],
        "Customer360": ["CRM", "DNS"],
        "SecureFiles": ["Active Directory", "Network"],
    }
    rows = []
    for index, name in enumerate(APP_NAMES[:count], 1):
        rows.append(
            {
                "application_id": "APP-%03d" % index,
                "name": name,
                "owner": DEPARTMENTS[index % len(DEPARTMENTS)] + " Systems",
                "criticality": (
                    "critical"
                    if name == "PayrollPro"
                    else ["medium", "high", "high", "critical"][index % 4]
                ),
                "environment": "synthetic-production-simulation",
                "normal_availability": round(99.5 + (index % 5) * 0.1, 2),
                "dependencies": dependency_map.get(name, ["DNS", "Active Directory"]),
            }
        )
    return rows


def build_users(count, locations):
    rows = []
    systems = ["Windows 11", "macOS 14", "Ubuntu 24.04"]
    for index in range(1, count + 1):
        department = DEPARTMENTS[(index - 1) % len(DEPARTMENTS)]
        first_name = FIRST_NAMES[(index - 1) % len(FIRST_NAMES)]
        last_name = "%s-S%03d" % (
            LAST_NAMES[((index - 1) // len(FIRST_NAMES)) % len(LAST_NAMES)],
            index,
        )
        location = locations[(index - 1) % len(locations)]
        manager_id = (
            None
            if index <= len(DEPARTMENTS)
            else "USR-%05d" % (((index - 1) % len(DEPARTMENTS)) + 1)
        )
        rows.append(
            {
                "user_id": "USR-%05d" % index,
                "first_name": first_name,
                "last_name": last_name,
                "name": "%s %s" % (first_name, last_name),
                "synthetic_identity": True,
                "department": department,
                "job_title": JOB_TITLES[(index * 3) % len(JOB_TITLES)],
                "location_id": location["location_id"],
                "location": location["name"],
                "manager_id": manager_id,
                "device_id": "SYN-DEV-%05d" % index,
                "operating_system": systems[index % len(systems)],
                "support_tier": ["standard", "standard", "enhanced", "executive"][index % 4],
            }
        )
    return rows


def build_incidents(count, start, locations, applications, users):
    location_by_name = {row["name"]: row["location_id"] for row in locations}
    app_by_name = {row["name"]: row["application_id"] for row in applications}
    users_by_location = defaultdict(list)
    for user in users:
        users_by_location[user["location_id"]].append(user["user_id"])
    rows = []
    for index in range(count):
        title, service, cause, location_names, app_names, categories = INCIDENT_PROFILES[
            index % len(INCIDENT_PROFILES)
        ]
        location_ids = [location_by_name[name] for name in location_names]
        application_ids = [app_by_name[name] for name in app_names if name in app_by_name]
        incident_start = start + timedelta(hours=12 + index * 10)
        incident_end = incident_start + timedelta(hours=6)
        affected_users = []
        for location_id in location_ids:
            affected_users.extend(users_by_location[location_id][:5])
        rows.append(
            {
                "incident_id": "INC-%04d" % (index + 1),
                "title": title + ("" if index < len(INCIDENT_PROFILES) else " %d" % (index + 1)),
                "start_at": iso(incident_start),
                "end_at": iso(incident_end),
                "affected_location_ids": location_ids,
                "affected_user_ids": affected_users,
                "affected_application_ids": application_ids,
                "affected_services": [service],
                "public_summary": "Users reported degraded %s behavior in the listed synthetic offices."
                % service,
                "resolution": "The simulated %s condition was corrected and service health verified."
                % service,
                "related_ticket_ids": [],
                "_ground_truth_root_cause": cause,
                "_ground_truth_category": categories[0],
                "_ground_truth_priority": "P1" if index > 0 and index % 11 == 0 else "P2",
                "_ticket_categories": categories,
            }
        )
    return rows


def build_knowledge(count, output):
    categories = list(CATEGORY_COUNTS)
    index = []
    relevant = defaultdict(list)
    articles_dir = output / "knowledge" / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)
    for number in range(1, count + 1):
        category = categories[(number - 1) % len(categories)]
        system, symptoms, focuses = ARTICLE_TEMPLATES[category]
        article_id = "KA-%04d" % number
        category_round = (number - 1) // len(categories)
        focus = focuses[category_round % len(focuses)]
        scopes = ["Office Workflow", "Remote Workflow", "Multi-user Evidence"]
        title = "%s: %s" % (focus, scopes[(category_round // len(focuses)) % len(scopes)])
        filename = article_id.lower() + ".md"
        troubleshooting_steps = [
            "Confirm the %s symptom, affected synthetic office, and observed time window."
            % symptoms[category_round % len(symptoms)],
            "Compare %s behavior from an approved second synthetic device." % system,
            "Capture safe status and latency evidence before changing the simulated service path.",
        ]
        resolution_variants = [
            "Restore the approved %s access path and verify the original workflow." % system,
            "Refresh the supported %s session, then record before-and-after evidence." % system,
            "Apply the documented synthetic configuration and confirm multi-user recovery.",
        ]
        escalation_variants = [
            "Escalate when two or more synthetic users share the symptom or errors persist.",
            "Escalate with timestamps when availability or latency breaches the simulated target.",
            "Escalate when safe comparison tests indicate a service-wide interruption.",
        ]
        resolution_guidance = resolution_variants[category_round % len(resolution_variants)]
        escalation_criteria = escalation_variants[category_round % len(escalation_variants)]
        metadata = {
            "article_id": article_id,
            "title": title,
            "category": category,
            "symptoms": symptoms,
            "environment": "ResolveAI synthetic enterprise simulation",
            "troubleshooting_steps": troubleshooting_steps,
            "resolution_guidance": resolution_guidance,
            "escalation_criteria": escalation_criteria,
            "related_systems": [system],
            "file": "articles/" + filename,
        }
        index.append(metadata)
        relevant[category].append(article_id)
        numbered_steps = "\n".join(
            "%d. %s" % (position, step) for position, step in enumerate(troubleshooting_steps, 1)
        )
        content = """# {title}

**Article ID:** {article_id}

## Category
{category}

## Symptoms
{symptoms}

## Environment
ResolveAI synthetic enterprise simulation only.

## Troubleshooting Steps
{troubleshooting_steps}

## Resolution Guidance
{resolution_guidance}

## Escalation Criteria
{escalation_criteria}

## Related Systems
{system}
""".format(
            title=title,
            article_id=article_id,
            category=category,
            symptoms="; ".join(symptoms),
            troubleshooting_steps=numbered_steps,
            resolution_guidance=resolution_guidance,
            escalation_criteria=escalation_criteria,
            system=system,
        )
        with (articles_dir / filename).open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    write_json(output / "knowledge" / "index.json", {"synthetic": True, "articles": index})
    return relevant


def build_incident_link_plan(categories, incidents, linked_target):
    """Reserve compatible ticket positions so every incident receives a ticket."""
    available = defaultdict(list)
    for position, category in enumerate(categories):
        available[category].append(position)

    plan = {}
    for incident in incidents:
        choices = [category for category in incident["_ticket_categories"] if available[category]]
        if not choices:
            raise ValueError("ticket count cannot provide a compatible ticket for every incident")
        category = max(choices, key=lambda value: len(available[value]))
        plan[available[category].pop()] = incident

    for position, category in enumerate(categories):
        if len(plan) >= linked_target:
            break
        if position in plan:
            continue
        matches = [incident for incident in incidents if category in incident["_ticket_categories"]]
        if matches:
            plan[position] = matches[position % len(matches)]
    return plan


def resolution_variants(category, system):
    return [
        (
            "Restored the approved %s configuration for the %s workflow and verified recovery."
            % (system, category),
            "configuration_restored",
        ),
        (
            "Recovered the synthetic %s session, repeated the affected workflow, and recorded healthy results."
            % system,
            "service_recovered",
        ),
        (
            "Applied verified %s guidance for %s and confirmed the requester could continue."
            % (category, system),
            "user_guidance",
        ),
    ]


def build_tickets(
    count,
    category_counts,
    incidents,
    users,
    locations,
    applications,
    relevant_articles,
    rng,
    simulation_start,
):
    location_by_id = {row["location_id"]: row for row in locations}
    users_by_location = defaultdict(list)
    for user in users:
        users_by_location[user["location_id"]].append(user)
    app_by_name = {row["name"]: row["application_id"] for row in applications}
    app_ids = [row["application_id"] for row in applications]
    linked_target = max(len(incidents), min(150, count // 4))
    categories = []
    for category, amount in category_counts.items():
        categories.extend([category] * amount)
    # Interleave categories deterministically instead of emitting category-sized blocks.
    rng.shuffle(categories)
    link_plan = build_incident_link_plan(categories, incidents, linked_target)
    application_names = {row["application_id"]: row["name"] for row in applications}
    rows = []
    category_occurrences = defaultdict(int)
    for index, category in enumerate(categories, 1):
        category_occurrence = category_occurrences[category]
        category_occurrences[category] += 1
        service, phrases, team = CATEGORY_DETAILS[category]
        incident = link_plan.get(index - 1)
        if incident:
            location_id = incident["affected_location_ids"][
                index % len(incident["affected_location_ids"])
            ]
            pool = users_by_location[location_id]
            user = pool[index % min(5, len(pool))]
            start = datetime.strptime(incident["start_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            created = start + timedelta(minutes=5 + (index * 17) % 300)
            incident_id = incident["incident_id"]
            affected_app = (
                incident["affected_application_ids"][0]
                if incident["affected_application_ids"]
                else None
            )
        else:
            user = users[(index * 37) % len(users)]
            location_id = user["location_id"]
            created = simulation_start + timedelta(
                hours=(index * 7) % (24 * 14), minutes=index % 60
            )
            incident_id = None
            affected_app = None
        if affected_app is None and category == "Application Access" and incident_id is None:
            affected_app = app_ids[index % len(app_ids)]
        if affected_app is None and service == "PayrollPro" and "PayrollPro" in app_by_name:
            affected_app = app_by_name["PayrollPro"]
        status = STATUSES[category_occurrence % len(STATUSES)]
        resolution_minutes = 20 + (index * 13) % 420
        ticket_id = "TKT-%06d" % index
        article_ids = relevant_articles.get(category, [])
        location_name = location_by_id[location_id]["name"]
        system = application_names.get(affected_app, service)
        symptom = phrases[index % len(phrases)]
        work_mode = ["from the office", "remotely", "in a scheduled workflow"][index % 3]
        timing = ["at shift start", "after a reconnect", "during a routine task", "this morning"][
            index % 4
        ]
        impact = [
            "One workflow is delayed",
            "Repeated attempts are interrupting work",
            "The requester can use other services",
            "The business task cannot be completed",
        ][index % 4]
        title_options = [
            "%s: %s in %s" % (system, symptom.capitalize(), location_name),
            "%s %s - %s" % (location_name, system, symptom),
            "%s issue %s - %s" % (category, work_mode, location_name),
            "%s workflow interrupted in %s" % (system, location_name),
        ]
        description_options = [
            "A synthetic user in %s observed that %s %s while working %s. %s."
            % (location_name, system, symptom, work_mode, impact),
            "From %s, the requester reports %s %s. It was observed %s; %s."
            % (location_name, system, symptom, timing, impact.lower()),
            "The requester noticed %s that %s %s while working %s. %s."
            % (timing, system, symptom, work_mode, impact),
            "%s for a user in %s. They reported that %s %s; the observation was recorded %s."
            % (impact, location_name, system, symptom, timing),
        ]
        resolution, resolution_code = resolution_variants(category, system)[category_occurrence % 3]
        if status == "in_progress":
            resolution = None
            resolution_code = None
            completed_minutes = None
        else:
            completed_minutes = resolution_minutes
        priority = (
            incident["_ground_truth_priority"]
            if incident
            else ["P3", "P3", "P2", "P4", "P2"][index % 5]
        )
        rows.append(
            {
                "ticket_id": ticket_id,
                "created_at": iso(created),
                "updated_at": iso(created + timedelta(minutes=resolution_minutes)),
                "user_id": user["user_id"],
                "location_id": location_id,
                "location_name": location_name,
                "title": title_options[index % len(title_options)],
                "description": description_options[index % len(description_options)],
                "category": category,
                "subcategory": service,
                "priority": priority,
                "status": status,
                "affected_application_id": affected_app,
                "affected_device": user["device_id"],
                "assigned_team": team,
                "resolution": resolution,
                "resolution_code": resolution_code,
                "resolution_time_minutes": completed_minutes,
                "incident_id": incident_id,
                "ai_analysis": None,
                "ai_confidence": None,
                "knowledge_article_ids": article_ids[:2],
                "related_ticket_ids": [],
            }
        )
    by_incident = defaultdict(list)
    for row in rows:
        if row["incident_id"]:
            by_incident[row["incident_id"]].append(row)
    incident_by_id = {row["incident_id"]: row for row in incidents}
    for incident_id, related in by_incident.items():
        ids = [row["ticket_id"] for row in related]
        incident_by_id[incident_id]["related_ticket_ids"] = ids
        for position, row in enumerate(related):
            peers = []
            if position > 0:
                peers.append(ids[position - 1])
            if position + 1 < len(ids):
                peers.append(ids[position + 1])
            row["related_ticket_ids"] = peers
    return rows


def build_telemetry_and_logs(start, incidents, locations):
    incident_windows = []
    for incident in incidents:
        incident_windows.append(
            (
                datetime.strptime(incident["start_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc
                ),
                datetime.strptime(incident["end_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc
                ),
                incident,
            )
        )
    telemetry = []
    logs = []
    latest_end = max(end for _, end, _ in incident_windows)
    slot_count = max(120, math.ceil((latest_end - start).total_seconds() / (3 * 3600)) + 1)
    for slot in range(slot_count):
        timestamp = start + timedelta(hours=3 * slot)
        for service_index, service in enumerate(SERVICES):
            for location_index, location in enumerate(locations):
                incident = next(
                    (
                        row
                        for begin, end, row in incident_windows
                        if begin <= timestamp <= end
                        and service in row["affected_services"]
                        and location["location_id"] in row["affected_location_ids"]
                    ),
                    None,
                )
                if incident:
                    availability = round(82.0 + ((slot + location_index) % 10), 2)
                    latency = 650 + ((slot * 29 + service_index * 17) % 700)
                    error_rate = round(6.0 + ((slot + service_index) % 14), 2)
                    incident_id = incident["incident_id"]
                else:
                    availability = round(99.91 + ((slot + service_index) % 8) / 100, 2)
                    latency = 18 + ((slot * 7 + location_index * 11 + service_index) % 75)
                    error_rate = round(((slot + service_index + location_index) % 9) / 10, 2)
                    incident_id = None
                telemetry.append(
                    {
                        "timestamp": iso(timestamp),
                        "service": service,
                        "location_id": location["location_id"],
                        "availability": availability,
                        "latency_ms": latency,
                        "error_rate": error_rate,
                        "incident_id": incident_id,
                    }
                )
                if slot % 4 == 0 or incident:
                    severity = "ERROR" if incident else "INFO"
                    signature = incident_log_signature(service, incident)
                    host_service = service.lower().replace(" ", "-").replace("-365", "365")
                    logs.append(
                        {
                            "host": "syn-%s-%02d.invalid" % (host_service, location_index + 1),
                            "timestamp": iso(timestamp),
                            "severity": severity,
                            "service": service,
                            "location_id": location["location_id"],
                            "message": signature,
                            "incident_id": incident_id,
                        }
                    )
    return telemetry, logs


def incident_log_signature(service, incident):
    if incident is None:
        return "synthetic health check successful"
    if incident["incident_id"] == "INC-0001" and service == "DNS":
        return (
            "failed to resolve payrollpro.internal.synthetic.invalid; "
            "synthetic resolver request timed out"
        )
    signatures = {
        "VPN": "synthetic VPN gateway rejected an authentication exchange",
        "DNS": "lookup for service.internal.synthetic.invalid exceeded the safe timeout",
        "Wi-Fi": "synthetic wireless controller reported repeated client reassociation",
        "Microsoft 365": "synthetic Microsoft 365 token validation request failed",
        "Email": "synthetic email transport queue exceeded its delivery threshold",
        "Active Directory": "synthetic directory authentication response exceeded its threshold",
        "PayrollPro": "synthetic PayrollPro dependency request returned a timeout",
        "CRM": "synthetic CRM connection pool rejected an application request",
        "Network": "synthetic network path reported elevated loss and latency",
    }
    return signatures[service]


def build_ground_truth(incidents, tickets, relevant_articles):
    from demo_data_common import AI_CATEGORY_BY_PRODUCT_CATEGORY

    incident_by_id = {row["incident_id"]: row for row in incidents}
    incident_truth = [
        {
            "incident_id": incident["incident_id"],
            "ground_truth_root_cause": incident["_ground_truth_root_cause"],
            "ground_truth_category": incident["_ground_truth_category"],
            "ground_truth_priority": incident["_ground_truth_priority"],
        }
        for incident in incidents
    ]
    cases = []
    for ticket in tickets:
        if not ticket["incident_id"]:
            continue
        incident = incident_by_id[ticket["incident_id"]]
        cases.append(
            {
                "ticket_id": ticket["ticket_id"],
                "incident_id": incident["incident_id"],
                "root_cause_key": incident["_ground_truth_root_cause"],
                "expected_category": ticket["category"],
                "expected_ai_category": AI_CATEGORY_BY_PRODUCT_CATEGORY[ticket["category"]],
                "expected_priority": ticket["priority"],
                "relevant_knowledge_article_ids": relevant_articles.get(ticket["category"], [])[:3],
                "response_input": {
                    "probable_root_cause": incident["_ground_truth_root_cause"].replace("_", " "),
                    "recommendation": (
                        "Please follow the approved %s diagnostic checklist and contact support "
                        "if the issue persists." % ticket["category"].lower()
                    ),
                    "limitations": ["This assessment uses synthetic evidence only"],
                    "requires_escalation": ticket["priority"] == "P1",
                },
                "response_rubric": {
                    "require_uncertainty": True,
                    "prohibit_completed_actions": True,
                    "require_professional_format": True,
                    "required_recommendation_terms": [
                        "approved %s diagnostic checklist" % ticket["category"].lower()
                    ],
                    "require_escalation_language": ticket["priority"] == "P1",
                },
            }
        )
    return {
        "schema_version": "1.0",
        "dataset_version": "resolveai-phase9-eval-v1",
        "visibility": "hidden_non_user_facing_evaluation_only",
        "synthetic": True,
        "incidents": incident_truth,
        "cases": cases,
    }
