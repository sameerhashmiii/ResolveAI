"""Shared contract definitions for ResolveAI synthetic demo data tooling."""

import hashlib
import json
from pathlib import Path

CATEGORY_COUNTS = {
    "VPN / Remote Access": 120,
    "Password / MFA": 100,
    "Wi-Fi / Wireless": 90,
    "Application Access": 80,
    "Outlook / Email": 70,
    "Laptop / Endpoint": 70,
    "Network Connectivity": 80,
    "Microsoft 365": 60,
    "Account Lockout": 50,
    "Software Installation": 50,
    "Printer / Peripheral": 40,
    "DNS / Name Resolution": 40,
    "File / Share Access": 40,
    "Security Alerts": 30,
    "Other": 80,
}

AI_CATEGORY_BY_PRODUCT_CATEGORY = {
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

APP_NAMES = [
    "FinanceHub",
    "HRConnect",
    "SalesPortal",
    "Customer360",
    "PayrollPro",
    "ServiceDesk",
    "InventoryOne",
    "SecureFiles",
    "ExpenseCenter",
    "BenefitsHub",
    "AnalyticsPortal",
    "ProcurementPro",
    "TimeTrack",
    "EmployeePortal",
    "CRMOne",
]

LOCATION_NAMES = [
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

SERVICES = [
    "VPN",
    "DNS",
    "Wi-Fi",
    "Microsoft 365",
    "Email",
    "Active Directory",
    "PayrollPro",
    "CRM",
    "Network",
]

GENERATED_PATHS = [
    "manifest.json",
    "locations",
    "applications",
    "users",
    "incidents",
    "tickets",
    "knowledge",
    "telemetry",
    "logs",
    "evaluation",
]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for value in values:
            handle.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def read_jsonl(path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def generated_files(root):
    files = []
    for name in GENERATED_PATHS:
        if name == "manifest.json":
            continue
        target = root / name
        if target.is_file():
            files.append(target)
        elif target.is_dir():
            files.extend(path for path in target.rglob("*") if path.is_file())
    return sorted(files)


def relative(path, root):
    return Path(path).relative_to(root).as_posix()
