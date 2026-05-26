import os
import tempfile
import json
import pytest
from fastapi.testclient import TestClient

# Create a temporary file for policies during testing
temp_rules_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
temp_rules_path = temp_rules_file.name
temp_rules_file.close()

# Set environment variable before importing the app so it initializes with our temp file
os.environ["DASC_RULES_FILE"] = temp_rules_path

from dasc.server import app, declarative_engine

@pytest.fixture(autouse=True)
def cleanup_temp_file():
    # Write empty rules list on setup
    with open(temp_rules_path, "w") as f:
        json.dump({"rules": []}, f)
    declarative_engine.load_rules_from_file(temp_rules_path)
    
    yield
    
    # Clean up file on teardown
    if os.path.exists(temp_rules_path):
        try:
            os.remove(temp_rules_path)
        except OSError:
            pass

def test_get_policies():
    client = TestClient(app)
    headers = {"X-API-KEY": "dasc-dev-key-123"}
    response = client.get("/policies", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"rules": []}

def test_post_policies_valid():
    client = TestClient(app)
    headers = {"X-API-KEY": "dasc-dev-key-123"}
    new_rules = {
        "rules": [
            {
                "name": "Limit Spend",
                "condition": "payload.amount > 500",
                "action": "REJECT",
                "reason": "OVER_LIMIT"
            }
        ]
    }
    response = client.post("/policies", headers=headers, json=new_rules)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert len(response.json()["rules"]) == 1

    # Verify GET returns updated rules
    get_res = client.get("/policies", headers=headers)
    assert len(get_res.json()["rules"]) == 1
    assert get_res.json()["rules"][0]["name"] == "Limit Spend"

def test_post_policies_invalid():
    client = TestClient(app)
    headers = {"X-API-KEY": "dasc-dev-key-123"}
    
    # Missing action field
    bad_rules = {
        "rules": [
            {
                "name": "Limit Spend",
                "condition": "payload.amount > 500",
                "reason": "OVER_LIMIT"
            }
        ]
    }
    response = client.post("/policies", headers=headers, json=bad_rules)
    assert response.status_code == 400

    # Bad action type
    bad_action_rules = {
        "rules": [
            {
                "name": "Limit Spend",
                "condition": "payload.amount > 500",
                "action": "INVALID_ACTION",
                "reason": "OVER_LIMIT"
            }
        ]
    }
    response = client.post("/policies", headers=headers, json=bad_action_rules)
    assert response.status_code == 400

def test_auth_failure():
    client = TestClient(app)
    # Missing header
    response = client.get("/policies")
    assert response.status_code == 403

    # Invalid key
    response = client.get("/policies", headers={"X-API-KEY": "wrong-key"})
    assert response.status_code == 403
