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

def test_create_room_with_passcode():
    from backend.core.auth import create_token
    from backend.core.config import ROOM_CREATION_PASSWORD
    token = create_token("testuser")
    
    # 1. Missing password
    res = client.post(f"/rooms?token={token}")
    assert res.status_code == 422

    # 2. Incorrect password
    res = client.post(f"/rooms?token={token}&password=wrongpassword")
    assert res.status_code == 403
    assert res.json()["detail"] == "Incorrect room creation password"

    # 3. Correct password
    res = client.post(f"/rooms?token={token}&password={ROOM_CREATION_PASSWORD}")
    assert res.status_code == 200
    assert "room_code" in res.json()

