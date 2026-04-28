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
    pass


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
    pass


@pytest.mark.asyncio
async def test_invalid_token_returns_404(client: AsyncClient):
    """
    POST any JSON body to /in/nonexistent-token-12345
    
    Assert:
    - Response status is 404
    """
    # YOUR CODE HERE
    pass


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
    pass


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
    pass
