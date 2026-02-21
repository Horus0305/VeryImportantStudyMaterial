from .core.config import parse_cors_origins

def test_parse_cors_origins_none():
    assert parse_cors_origins(None) == ["*"]

def test_parse_cors_origins_empty_string():
    assert parse_cors_origins("") == ["*"]

def test_parse_cors_origins_whitespace():
    # "   " is not empty, and strip() != "*", so it parses as list.
    # split(",") gives ["   "], strip() gives "", filtered out -> []
    assert parse_cors_origins("   ") == []

def test_parse_cors_origins_wildcard():
    assert parse_cors_origins("*") == ["*"]
    assert parse_cors_origins(" * ") == ["*"]

def test_parse_cors_origins_single():
    assert parse_cors_origins("http://localhost:3000") == ["http://localhost:3000"]
    assert parse_cors_origins(" http://localhost:3000 ") == ["http://localhost:3000"]

def test_parse_cors_origins_multiple():
    expected = ["http://localhost:3000", "http://example.com"]
    assert parse_cors_origins("http://localhost:3000,http://example.com") == expected
    assert parse_cors_origins(" http://localhost:3000 , http://example.com ") == expected

def test_parse_cors_origins_with_empty_items():
    expected = ["http://localhost:3000", "http://example.com"]
    assert parse_cors_origins("http://localhost:3000,,http://example.com") == expected
    assert parse_cors_origins(",http://localhost:3000, ,http://example.com,") == expected
