from app.rag.embeddings import technical_tokens

DOMAIN_EXPANSIONS: tuple[tuple[frozenset[str], tuple[str, ...]], ...] = (
    (frozenset({"vpn", "remote access"}), ("virtual private network", "remote gateway")),
    (frozenset({"dns", "hostname", "name resolution"}), ("domain name", "resolve host")),
    (frozenset({"mfa", "account", "password"}), ("authentication", "sign in", "credential")),
    (frozenset({"wi-fi", "wifi", "wireless"}), ("ssid", "wireless network")),
    (frozenset({"outlook", "email", "mail"}), ("mailbox", "message", "mail client")),
    (frozenset({"application access", "app", "site"}), ("access denied", "application sign in")),
)


def expand_query(query: str) -> str:
    """Append only transparent, fixed support-domain synonyms to a user's query."""
    normalized = " ".join(technical_tokens(query))
    additions: list[str] = []
    for triggers, terms in DOMAIN_EXPANSIONS:
        if any(trigger in normalized for trigger in triggers):
            additions.extend(terms)
    vpn_connected = "vpn" in normalized and any(
        term in normalized for term in ("connected", "connects")
    )
    internal_unavailable = "internal" in normalized and any(
        term in normalized
        for term in ("unavailable", "cannot access", "can t access", "won t open")
    )
    if vpn_connected and internal_unavailable:
        additions.extend(("dns", "hostname", "name resolution", "resolve host"))
    unique = list(dict.fromkeys(additions))
    return query if not unique else f"{query} {' '.join(unique)}"


def category_hints(query: str) -> tuple[str, ...]:
    """Return transparent KB categories directly signaled by the query."""
    normalized = " ".join(technical_tokens(query))
    hints: list[str] = []
    mappings = (
        (("vpn", "remote access"), "VPN / Remote Access"),
        (("dns", "hostname", "name resolution"), "DNS / Name Resolution"),
        (("mfa", "password"), "Password / MFA"),
        (("wi-fi", "wifi", "wireless"), "Wi-Fi / Wireless"),
        (("outlook", "email", "mailbox"), "Outlook / Email"),
        (("application", "app", "payrollpro"), "Application Access"),
    )
    for triggers, category in mappings:
        if any(trigger in normalized for trigger in triggers):
            hints.append(category)
    vpn_connected = "vpn" in normalized and any(
        term in normalized for term in ("connected", "connects")
    )
    internal_unavailable = "internal" in normalized and any(
        term in normalized for term in ("unavailable", "cannot access", "can t access")
    )
    if vpn_connected and internal_unavailable:
        hints.append("DNS / Name Resolution")
    return tuple(dict.fromkeys(hints))
