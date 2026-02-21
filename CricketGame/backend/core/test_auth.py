import pytest
import bcrypt
from backend.core.auth import hash_password, verify_password

def test_hash_password_returns_string():
    """Test that hash_password returns a non-empty string."""
    password = "securePassword123"
    hashed = hash_password(password)
    assert isinstance(hashed, str)
    assert len(hashed) > 0
    assert hashed != password

def test_hash_password_salt():
    """Test that hashing the same password twice produces different hashes (salting)."""
    password = "samePassword"
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    assert hash1 != hash2

def test_verify_password_correct():
    """Test that verify_password returns True for the correct password."""
    password = "mySecretPassword"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True

def test_verify_password_incorrect():
    """Test that verify_password returns False for an incorrect password."""
    password = "mySecretPassword"
    hashed = hash_password(password)
    assert verify_password("wrongPassword", hashed) is False

def test_verify_password_empty_string():
    """Test behavior with empty password strings."""
    password = ""
    hashed = hash_password(password)
    assert verify_password("", hashed) is True
    assert verify_password("notEmpty", hashed) is False

def test_verify_password_invalid_hash_format():
    """Test behavior when the hash is not a valid bcrypt hash."""
    # bcrypt.checkpw raises a ValueError if the hash is invalid
    with pytest.raises(ValueError):
        verify_password("password", "invalidHashString")
