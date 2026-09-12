import math

import pytest

from app.rag.embeddings import LocalHashEmbedding
from app.rag.expansion import category_hints, expand_query


def test_local_hash_embedding_is_deterministic_finite_and_normalized() -> None:
    embedder = LocalHashEmbedding()
    first = embedder.embed("VPN gateway cannot resolve intranet.example.test")
    second = embedder.embed("VPN gateway cannot resolve intranet.example.test")

    assert embedder.name == "local-hash-v1"
    assert len(first) == embedder.dimension == 384
    assert first == second
    assert all(math.isfinite(value) for value in first)
    assert math.sqrt(sum(value * value for value in first)) == pytest.approx(1.0)
    assert first != embedder.embed("Outlook mailbox is disconnected")
    assert embedder.embed("") == [0.0] * 384


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("VPN fails", "remote gateway"),
        ("hostname lookup fails", "domain name"),
        ("MFA account locked", "authentication"),
        ("Wi-Fi is unstable", "ssid"),
        ("Outlook email delayed", "mailbox"),
        ("application access denied", "application sign in"),
    ],
)
def test_query_expansion_has_transparent_domain_mappings(query: str, expected: str) -> None:
    assert expected in expand_query(query)


def test_connected_vpn_internal_site_scenario_adds_dns_guidance() -> None:
    expanded = expand_query("VPN connects but internal site is unavailable")
    assert "dns" in expanded
    assert "hostname" in expanded
    assert "name resolution" in expanded
    assert category_hints("VPN connects but internal site is unavailable") == (
        "VPN / Remote Access",
        "DNS / Name Resolution",
    )


def test_unrelated_query_is_not_expanded() -> None:
    query = "Laptop battery replacement"
    assert expand_query(query) == query
