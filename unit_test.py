import uvicorn
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_user():
    expect = {"user_id": 1}
    body = {
        "username": "111",
        "password": "zcckypsAw012",
        "display_name": "111"
    }

    response = client.post("/user/", json=body)
    assert response.status_code == 201
    assert response.json() == expect

def test_create_event():
    pass

def test_initiate_event():
    pass

def test_join_event():
    pass

def test_communication():
    pass

def test_leave_event():
    pass

def test_dismiss_event():
    pass

def test_end_event():
    pass

def test_payable():
    pass
