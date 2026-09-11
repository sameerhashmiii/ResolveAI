import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest
from app.schemas.tickets import TicketCreate, TicketUpdate


def test_ticket_create_normalizes_and_bounds_input() -> None:
    payload = TicketCreate(
        title="  Printer offline  ",
        description="  Cannot print  ",
        requester_name="  Casey Example  ",
        requester_department="  Finance  ",
    )

    assert payload.title == "Printer offline"
    assert payload.requester_department == "Finance"

    with pytest.raises(ValidationError):
        TicketCreate(
            title="x" * 201,
            description="issue",
            requester_name="Casey",
        )


def test_ticket_update_rejects_null_required_values() -> None:
    with pytest.raises(ValidationError):
        TicketUpdate(title=None)
    with pytest.raises(ValidationError):
        TicketUpdate(status=None)


def test_login_normalizes_email_and_rejects_invalid_value() -> None:
    assert LoginRequest(email=" USER@EXAMPLE.TEST ", password="x").email == "user@example.test"
    with pytest.raises(ValidationError):
        LoginRequest(email="invalid", password="x")
