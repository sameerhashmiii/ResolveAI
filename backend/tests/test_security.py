from app.models.enums import Role, role_allows
from app.security import hash_password, hash_session_token, verify_password


def test_password_hashing_and_verification() -> None:
    encoded = hash_password("correct horse battery staple")

    assert encoded.startswith("$argon2")
    assert verify_password(encoded, "correct horse battery staple")
    assert not verify_password(encoded, "wrong")
    assert not verify_password("not-a-hash", "password")


def test_session_hash_is_deterministic_and_not_plaintext() -> None:
    token = "opaque-session-token"

    assert hash_session_token(token) == hash_session_token(token)
    assert hash_session_token(token) != token
    assert len(hash_session_token(token)) == 64


def test_roles_are_ordered() -> None:
    assert role_allows(Role.SUPPORT_ANALYST, Role.SUPPORT_ANALYST)
    assert not role_allows(Role.SUPPORT_ANALYST, Role.MANAGER)
    assert role_allows(Role.MANAGER, Role.SUPPORT_ANALYST)
    assert role_allows(Role.ADMINISTRATOR, Role.MANAGER)
