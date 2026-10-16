from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_correct_password_is_accepted():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)


def test_wrong_password_is_rejected():
    hashed = hash_password("secret123")
    assert not verify_password("wrong_password", hashed)


def test_same_password_gives_different_hashes():
    assert hash_password("secret123") != hash_password("secret123")


def test_get_user_id_from_token():
    access_token = create_access_token(user_id=42)
    user_id = decode_access_token(token=access_token)
    assert user_id is 42


def test_reject_tampered_token():
    access_token = create_access_token(user_id=42)
    tampered = access_token[:-5] + "AAAAA"
    user_id = decode_access_token(token=tampered)
    assert user_id is None
