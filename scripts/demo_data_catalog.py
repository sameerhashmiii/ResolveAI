"""Immutable catalogs used by the synthetic enterprise data builders."""

DISCLAIMER = "Entirely synthetic demo data. No record represents a real person or system."

DEPARTMENTS = [
    "Finance",
    "People Operations",
    "Sales",
    "Support",
    "Engineering",
    "Legal",
    "Operations",
    "Marketing",
]

FIRST_NAMES = [
    "Avery",
    "Blake",
    "Casey",
    "Devon",
    "Emery",
    "Finley",
    "Gray",
    "Harper",
    "Indigo",
    "Jordan",
    "Kai",
    "Logan",
    "Morgan",
    "Nico",
    "Parker",
    "Quinn",
    "Riley",
    "Sage",
    "Taylor",
    "Winter",
]

LAST_NAMES = [
    "Alder",
    "Birch",
    "Cedar",
    "Dover",
    "Elm",
    "Frost",
    "Grove",
    "Haven",
    "Ivory",
    "Juniper",
    "Keaton",
    "Linden",
    "Meadow",
    "North",
    "Oakley",
    "Pine",
    "Reed",
    "Stone",
    "Vale",
    "Willow",
]

JOB_TITLES = [
    "Analyst",
    "Coordinator",
    "Specialist",
    "Manager",
    "Engineer",
    "Advisor",
    "Associate",
    "Director",
]

STATUSES = ["resolved", "closed", "resolved", "closed", "in_progress"]

CATEGORY_DETAILS = {
    "VPN / Remote Access": (
        "VPN",
        ["connection rejected", "remote session repeatedly disconnects", "gateway sign-in loops"],
        "Network Operations",
    ),
    "Password / MFA": (
        "Active Directory",
        ["MFA prompt repeats", "password change is not accepted", "verification flow stalls"],
        "Identity Operations",
    ),
    "Wi-Fi / Wireless": (
        "Wi-Fi",
        [
            "wireless connection drops",
            "office network cannot be joined",
            "signal is visible but unusable",
        ],
        "Network Operations",
    ),
    "Application Access": (
        "PayrollPro",
        [
            "application page does not load",
            "sign-in returns an access error",
            "workflow stops after login",
        ],
        "Application Support",
    ),
    "Outlook / Email": (
        "Email",
        [
            "messages remain in the outbox",
            "mailbox connection is unavailable",
            "new mail is delayed",
        ],
        "Messaging Operations",
    ),
    "Laptop / Endpoint": (
        "Network",
        [
            "laptop is unusually slow",
            "device does not wake reliably",
            "endpoint loses connectivity",
        ],
        "Endpoint Support",
    ),
    "Network Connectivity": (
        "Network",
        [
            "internal sites time out",
            "connection has intermittent pauses",
            "business services are unreachable",
        ],
        "Network Operations",
    ),
    "Microsoft 365": (
        "Microsoft 365",
        ["suite sign-in fails", "collaboration page times out", "document session will not open"],
        "Messaging Operations",
    ),
    "Account Lockout": (
        "Active Directory",
        [
            "account reports locked",
            "sign-in is refused after verification",
            "session cannot be restored",
        ],
        "Identity Operations",
    ),
    "Software Installation": (
        "Network",
        [
            "approved installer does not complete",
            "software catalog download stalls",
            "installation reports a generic failure",
        ],
        "Endpoint Support",
    ),
    "Printer / Peripheral": (
        "Network",
        ["printer remains offline", "dock is not recognized", "print job stays queued"],
        "Workplace Support",
    ),
    "DNS / Name Resolution": (
        "DNS",
        [
            "service names do not resolve",
            "internal URL intermittently fails",
            "hostname lookup is slow",
        ],
        "Network Operations",
    ),
    "File / Share Access": (
        "Network",
        [
            "shared folder is unavailable",
            "file sync repeatedly retries",
            "team drive cannot be opened",
        ],
        "Storage Operations",
    ),
    "Security Alerts": (
        "Active Directory",
        [
            "unexpected security warning appears",
            "endpoint reports a policy alert",
            "sign-in risk prompt needs review",
        ],
        "Security Operations",
    ),
    "Other": (
        "Network",
        [
            "workstation behavior needs investigation",
            "business workflow is interrupted",
            "service response is inconsistent",
        ],
        "Service Desk",
    ),
}

INCIDENT_PROFILES = [
    (
        "Dallas DNS degradation affecting PayrollPro",
        "DNS",
        "dns_degradation",
        ["Dallas"],
        ["PayrollPro"],
        ["DNS / Name Resolution", "Application Access", "Network Connectivity"],
    ),
    (
        "Remote VPN authentication failures",
        "VPN",
        "vpn_authentication",
        ["Austin", "Denver"],
        [],
        ["VPN / Remote Access", "Password / MFA"],
    ),
    (
        "Microsoft 365 authentication interruption",
        "Microsoft 365",
        "m365_authentication",
        ["New York", "Boston"],
        [],
        ["Microsoft 365", "Outlook / Email"],
    ),
    (
        "Office wireless controller instability",
        "Wi-Fi",
        "wifi_controller",
        ["Chicago"],
        [],
        ["Wi-Fi / Wireless", "Network Connectivity"],
    ),
    (
        "PayrollPro dependency timeout",
        "PayrollPro",
        "application_dependency",
        ["Dallas", "Atlanta"],
        ["PayrollPro"],
        ["Application Access"],
    ),
    (
        "CRM database connection saturation",
        "CRM",
        "crm_database",
        ["San Francisco"],
        ["CRMOne", "Customer360"],
        ["Application Access"],
    ),
    (
        "Regional packet loss",
        "Network",
        "packet_loss",
        ["Seattle", "Phoenix"],
        [],
        ["Network Connectivity", "VPN / Remote Access"],
    ),
    (
        "Secure file storage access interruption",
        "Network",
        "file_storage",
        ["Atlanta", "Chicago"],
        ["SecureFiles"],
        ["File / Share Access"],
    ),
    (
        "Directory authentication delay",
        "Active Directory",
        "directory_latency",
        ["Denver"],
        [],
        ["Account Lockout", "Password / MFA"],
    ),
    (
        "Email transport queue delay",
        "Email",
        "email_queue",
        ["Boston", "New York"],
        [],
        ["Outlook / Email"],
    ),
]

ARTICLE_TEMPLATES = {
    "VPN / Remote Access": (
        "VPN",
        ["gateway rejection", "remote disconnect"],
        ["Gateway Sign-in Verification", "Unstable Remote Sessions", "Remote Device Readiness"],
    ),
    "Password / MFA": (
        "Active Directory",
        ["MFA loop", "credential rejection"],
        ["Repeated MFA Prompts", "Password Change Verification", "Authenticator Enrollment"],
    ),
    "Wi-Fi / Wireless": (
        "Wi-Fi",
        ["SSID join failure", "unstable signal"],
        ["Office SSID Join Checks", "Roaming and Signal Evidence", "Wireless Profile Recovery"],
    ),
    "Application Access": (
        "PayrollPro",
        ["application timeout", "access denied"],
        [
            "Application Sign-in Evidence",
            "Dependency Health Checks",
            "Workflow Access Verification",
        ],
    ),
    "Outlook / Email": (
        "Email",
        ["mail delay", "client disconnected"],
        ["Delayed Message Evidence", "Mailbox Session Checks", "Outbox Recovery"],
    ),
    "Laptop / Endpoint": (
        "Network",
        ["slow endpoint", "device connectivity loss"],
        ["Endpoint Performance Evidence", "Wake and Resume Checks", "Device Network Recovery"],
    ),
    "Network Connectivity": (
        "Network",
        ["intermittent path", "internal timeout"],
        ["Internal Path Verification", "Latency Evidence Collection", "Office Uplink Checks"],
    ),
    "Microsoft 365": (
        "Microsoft 365",
        ["suite login loop", "collaboration timeout"],
        ["Suite Sign-in Verification", "Collaboration Session Checks", "Document Access Evidence"],
    ),
    "Account Lockout": (
        "Active Directory",
        ["locked account", "sign-in refused"],
        ["Lockout Verification", "Session Recovery", "Credential State Checks"],
    ),
    "Software Installation": (
        "Network",
        ["installer failure", "catalog download delay"],
        ["Approved Installer Checks", "Catalog Download Evidence", "Installation Readiness"],
    ),
    "Printer / Peripheral": (
        "Network",
        ["offline printer", "unrecognized dock"],
        ["Printer Queue Checks", "Dock Recognition Evidence", "Peripheral Connection Recovery"],
    ),
    "DNS / Name Resolution": (
        "DNS",
        ["slow hostname lookup", "internal names unavailable"],
        [
            "Internal Hostname Verification",
            "Intermittent Lookup Evidence",
            "Resolver Health Checks",
        ],
    ),
    "File / Share Access": (
        "Network",
        ["share unavailable", "sync retry"],
        ["Shared Folder Access Checks", "File Sync Evidence", "Team Drive Session Recovery"],
    ),
    "Security Alerts": (
        "Active Directory",
        ["policy warning", "sign-in risk prompt"],
        ["Safe Alert Triage", "Sign-in Evidence Review", "Endpoint Policy Verification"],
    ),
    "Other": (
        "Service Desk",
        ["workflow interruption", "unexpected behavior"],
        ["Evidence-led Initial Triage", "Impact Scoping", "Safe Reproduction Checks"],
    ),
}
