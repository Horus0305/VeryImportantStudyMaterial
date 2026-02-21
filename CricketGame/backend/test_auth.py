from fastapi.testclient import TestClient
from backend.main import app
from backend.core.config import ADMIN_SECRET
from backend.data.database import init_db

# Initialize DB for tests
init_db()

client = TestClient(app)

def test_migrate_formats_no_header():
    # Expect 422 because the header is required (Header(...))
    response = client.get("/auth/migrate-formats")
    assert response.status_code == 422

def test_migrate_formats_wrong_header():
    # Expect 403 because the secret is invalid
    response = client.get("/auth/migrate-formats", headers={"X-Admin-Secret": "wrong-secret"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid admin secret"

def test_migrate_formats_correct_header():
    # Expect 200 because the secret matches
    response = client.get("/auth/migrate-formats", headers={"X-Admin-Secret": ADMIN_SECRET})
    assert response.status_code == 200
    data = response.json()
    assert "format_stats_2v2_merged" in data
    assert "duplicate_rows_removed" in data
    assert "match_history_fixed" in data
