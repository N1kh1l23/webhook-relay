"""
Week 1 Tests — YOU write the assertions.

Each test tells you what to check. Write the actual assertions yourself.
The `client` fixture gives you an async HTTP client pointed at the test app.

Run with: pytest tests/ -v
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_source(client: AsyncClient):
    """
    POST /sources with {"name": "my-test-source"}
    
    Assert:
    - Response status is 201
    - Response JSON has "id", "name", "token", "inbound_url", "created_at"
    - name matches what you sent
    - inbound_url starts with "/in/"
    - token is a non-empty string
    """
    # YOUR CODE HERE
    #201 error work
    response = await client.post("/sources", json={"name": "my-test-source"})
    assert response.status_code == 201

    #Json paramter check
    data = response.json()
    assert "id" in data
    assert "name" in data
    assert "token" in data
    assert "inbound_url" in data
    assert "created_at" in data

    #Check if name matches
    value = data["name"]
    assert value == "my-test-source"

    #Check if inbound_url starts with 'in'"
    assert data["inbound_url"].startswith("/in")

    #Make sure token is a string that is not empty
    assert isinstance(data["token"], str)
    assert len(data["token"]) != 0


@pytest.mark.asyncio
async def test_receive_webhook(client: AsyncClient):
    """
    1. First create a source (POST /sources)
    2. Extract the token from the response
    3. POST a JSON body to /in/{token}
    4. Assert:
       - Response status is 202
       - Response JSON has "event_id" and "status" == "accepted"
    5. Then GET /sources/{source_id}/events
    6. Assert:
       - Response has 1 event
       - Event body matches what you sent
       - Event status is "pending"
    """
    # YOUR CODE HERE
    #Post created
    response = await client.post("/sources", json={"name": "my-test-recieve-webhook"})

    #Extracting token from response
    data = response.json()
    new_token = data["token"]

    #POST a JSON body to /in/{token}
    webhook_response = await client.post(f"/in/{new_token}", json={"event": "test"})

    #Assertions
    webhook_data = webhook_response.json()
    assert webhook_response.status_code == 202
    assert "event_id" in webhook_data
    assert webhook_data["status"] == "accepted"

    #Get source
    events_response = await client.get(f"/sources/{data['id']}/events")

    #Other assertions
    events_data = events_response.json()
    assert len(events_data) == 1
    assert events_data[0]["body"] == {"event": "test"}
    assert events_data[0]["status"] == "pending"



@pytest.mark.asyncio
async def test_invalid_token_returns_404(client: AsyncClient):
    """
    POST any JSON body to /in/nonexistent-token-12345
    
    Assert:
    - Response status is 404
    """
    # YOUR CODE HERE
    response = await client.post("/in/nonexistent-token-12345", json={"any": "thing"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_events_empty(client: AsyncClient):
    """
    1. Create a source
    2. GET /sources/{source_id}/events without sending any webhooks
    
    Assert:
    - Response status is 200
    - Response is an empty list
    """
    # YOUR CODE HERE
    response = await client.post("/sources", json = {"name": "test-list-events-empty"})
    data = response.json()
    events_response = await client.get(f"/sources/{data['id']}/events")
    events_data = events_response.json()
    assert events_response.status_code == 200
    assert len(events_data) == 0


@pytest.mark.asyncio
async def test_list_events_multiple(client: AsyncClient):
    """
    1. Create a source
    2. Send 3 different webhook payloads to /in/{token}
    3. GET /sources/{source_id}/events
    
    Assert:
    - Response has exactly 3 events
    - Events are ordered by received_at descending (newest first)
    """
    # YOUR CODE HERE
    #Creating source/3 different webhook payloads
    response = await client.post("/sources", json = {"name": "test-list-events-multiple"})
    data = response.json()
    payloads = [{"x": 0}, {"y": 1}, {"z": 2}]
    for x in payloads:
        await client.post(f"/in/{data['token']}", json= x)
    
    #Get sources and assertions
    event_respone = await client.get(f"/sources/{data['id']}/events")
    event_data = event_respone.json()
    assert len(event_data) == 3
    assert event_data[0]["body"] == payloads[-1]


