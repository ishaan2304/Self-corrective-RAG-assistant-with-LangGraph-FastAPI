# Path Parameters

FastAPI lets you declare path parameters (variable segments of a URL) using
Python's standard string formatting syntax in the route decorator.

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}
```

## Type Conversion and Validation

Because `item_id` is annotated as `int`, FastAPI parses and validates the
value automatically. If a client requests `/items/abc`, FastAPI returns a
422 Unprocessable Entity response with a clear error message instead of
letting the request reach your function body. This validation is powered
by Pydantic under the hood.

## Order Matters

When you have a fixed path like `/users/me` and a dynamic path like
`/users/{user_id}`, declare the fixed path first. FastAPI matches routes
in the order they are declared, so if `/users/{user_id}` comes first it
will greedily match `/users/me` and treat "me" as a user_id.

## Predefined Values with Enums

You can restrict a path parameter to a fixed set of values by declaring it
as a Python `Enum`. FastAPI validates the incoming value against the enum
members and rejects anything else with a 422 error, and the auto-generated
docs (Swagger UI) render it as a dropdown.

## Path Parameters Containing Paths

By default, path parameters match a single URL segment. To accept a value
that itself contains slashes (like a filesystem path), use the `:path`
converter, e.g. `{file_path:path}`, which tells FastAPI to match the rest
of the URL including slashes.
