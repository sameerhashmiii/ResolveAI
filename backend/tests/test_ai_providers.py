import json

import httpx
import pytest
from pydantic import ValidationError

from app.ai.policy import assign_priority
from app.ai.providers import (
    InvalidProviderResponse,
    LocalDemoProvider,
    OpenAICompatibleProvider,
    ProviderUnavailable,
)
from app.ai.schemas import (
    AffectedScope,
    Category,
    PriorityFactors,
    ProviderSignals,
    TicketAnalysisInput,
    Urgency,
)
from app.models.enums import TicketPriority


def ticket(title: str, description: str = "I cannot use this service") -> TicketAnalysisInput:
    return TicketAnalysisInput(
        title=title,
        description=description,
        requester_name="Sam Example",
        location="Dallas",
        device="MacBook Pro",
    )


@pytest.mark.parametrize(
    ("title", "category"),
    [
        ("VPN will not connect", Category.VPN),
        ("MFA code rejected", Category.ACCOUNT_ACCESS),
        ("Password reset needed", Category.PASSWORD),
        ("Wi-Fi disconnecting", Category.WIFI),
        ("Outlook email unavailable", Category.EMAIL),
        ("Phishing message received", Category.SECURITY),
        ("Unclear request", Category.OTHER),
    ],
)
async def test_local_demo_category_rules(title: str, category: Category) -> None:
    result = await LocalDemoProvider().analyze(ticket(title))
    assert result.category == category
    assert result.entities.location == "Dallas"
    assert result.entities.device == "MacBook Pro"


async def test_primary_vpn_case_extracts_entities_and_produces_p2() -> None:
    payload = ticket(
        "VPN issue",
        "VPN connects successfully but PayrollPro and internal applications are unavailable",
    ).model_copy(update={"application": "PayrollPro"})
    result = await LocalDemoProvider().analyze(payload)

    assert result.category == Category.VPN
    assert result.entities.application == "PayrollPro"
    assert result.priority_factors.business_critical is True
    assert assign_priority(result.priority_factors, result.entities.urgency) == TicketPriority.P2


@pytest.mark.parametrize(
    ("factors", "urgency", "expected"),
    [
        (
            (AffectedScope.ORGANIZATION, False, True, False, False, False),
            Urgency.CRITICAL,
            TicketPriority.P1,
        ),
        (
            (AffectedScope.MULTIPLE_USERS, True, False, False, False, False),
            Urgency.HIGH,
            TicketPriority.P2,
        ),
        (
            (AffectedScope.INDIVIDUAL, False, False, False, False, False),
            Urgency.MEDIUM,
            TicketPriority.P3,
        ),
        (
            (AffectedScope.INDIVIDUAL, False, False, False, False, True),
            Urgency.LOW,
            TicketPriority.P4,
        ),
        (
            (AffectedScope.INDIVIDUAL, False, False, False, False, False),
            Urgency.CRITICAL,
            TicketPriority.P3,
        ),
    ],
)
def test_priority_policy_table(
    factors: tuple[AffectedScope, bool, bool, bool, bool, bool],
    urgency: Urgency,
    expected: TicketPriority,
) -> None:
    scope, business, outage, security, workaround, information = factors
    policy = PriorityFactors(
        affected_scope=scope,
        business_critical=business,
        production_outage=outage,
        security_risk=security,
        workaround_available=workaround,
        information_request=information,
    )
    assert assign_priority(policy, urgency) == expected


def valid_signals() -> dict[str, object]:
    return {
        "category": "vpn",
        "category_confidence": 0.91,
        "entities": {
            "user": "Sam Example",
            "location": "Dallas",
            "application": "PayrollPro",
            "device": "MacBook Pro",
            "issue_type": "unavailable",
            "affected_scope": "individual",
            "urgency": "high",
        },
        "priority_factors": {
            "affected_scope": "individual",
            "business_critical": True,
            "production_outage": False,
            "security_risk": False,
            "workaround_available": False,
            "information_request": False,
        },
    }


@pytest.mark.parametrize(
    "mutation",
    [
        {"unexpected": True},
        {"category": "unknown_category"},
        {"category_confidence": 1.1},
    ],
)
def test_provider_schema_is_strict(mutation: dict[str, object]) -> None:
    payload = valid_signals() | mutation
    with pytest.raises(ValidationError):
        ProviderSignals.model_validate(payload)


async def test_openai_compatible_valid_output_and_contract() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(valid_signals())}}]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAICompatibleProvider(
            base_url="https://llm.example/v1",
            api_key="secret",
            model="triage-model",
            timeout=3,
            client=client,
        )
        result = await provider.analyze(ticket("VPN unavailable"))

    assert result.category == Category.VPN
    assert requests[0].url.path == "/v1/chat/completions"
    body = json.loads(requests[0].content)
    assert body["temperature"] == 0
    assert body["response_format"]["type"] == "json_schema"
    assert requests[0].headers["Authorization"] == "Bearer secret"


async def test_openai_compatible_repairs_once() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        content = "not json" if calls == 1 else json.dumps(valid_signals())
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAICompatibleProvider(
            base_url="https://llm.example/v1",
            api_key="secret",
            model="model",
            timeout=3,
            client=client,
        )
        assert (await provider.analyze(ticket("VPN"))).category == Category.VPN
    assert calls == 2


async def test_openai_compatible_rejects_repeated_malformed_output() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "{"}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAICompatibleProvider(
            base_url="https://llm.example",
            api_key="secret",
            model="model",
            timeout=3,
            client=client,
        )
        with pytest.raises(InvalidProviderResponse):
            await provider.analyze(ticket("VPN"))


@pytest.mark.parametrize("exception_type", [httpx.ConnectError, httpx.ReadTimeout])
async def test_openai_compatible_maps_transport_failure_without_network(
    exception_type: type[httpx.RequestError],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception_type("unavailable", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAICompatibleProvider(
            base_url="https://llm.example",
            api_key="secret",
            model="model",
            timeout=3,
            client=client,
        )
        with pytest.raises(ProviderUnavailable):
            await provider.analyze(ticket("VPN"))
