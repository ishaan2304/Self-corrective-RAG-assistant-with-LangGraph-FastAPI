# Testing FastAPI Applications

FastAPI is built on Starlette, which ships a `TestClient` based on the
`httpx` library, letting you write tests using standard tools like pytest
without running a real server.

```python
from fastapi.testclient import TestClient
from myapp import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}
```

## Testing Path and Query Parameters

You pass path and query parameters directly in the URL string you give to
the test client's HTTP methods, exactly as a real client would construct
the request.

## Testing Request Bodies

For POST, PUT, and PATCH requests, pass a Python dict as the `json`
argument to the client call, and it will be serialized to JSON and sent
as the request body, matching how a real client would send data.

## Overriding Dependencies in Tests

FastAPI apps expose a `dependency_overrides` dictionary. During testing,
you can replace a real dependency (such as one that hits a live database)
with a fake or in-memory version by mapping the original dependency
function to a substitute, without changing any application code.

## Async Tests

If your path operations are `async def` and you need to test them with an
async client instead of the synchronous `TestClient`, `httpx.AsyncClient`
combined with `pytest-asyncio` lets you await requests directly inside
async test functions.
