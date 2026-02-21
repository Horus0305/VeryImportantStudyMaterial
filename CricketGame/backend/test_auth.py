from backend.core.auth import decode_token, create_token
from backend.core.config import SECRET_KEY, ALGORITHM
from datetime import datetime, timedelta, timezone
from jose import jwt

def test_decode_token_valid():
    username = "testuser"
    token = create_token(username)
    decoded_username = decode_token(token)
    assert decoded_username == username

def test_decode_token_invalid_garbage():
    token = "invalid.token.string"
    assert decode_token(token) is None

def test_decode_token_invalid_signature():
    username = "testuser"
    # Create a token with a different secret key
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    token = jwt.encode({"sub": username, "exp": expire}, "WRONG_SECRET_KEY", algorithm=ALGORITHM)
    assert decode_token(token) is None

def test_decode_token_expired():
    username = "testuser"
    # Create a token that expired 5 minutes ago
    expire = datetime.now(timezone.utc) - timedelta(minutes=5)
    token = jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
    assert decode_token(token) is None
