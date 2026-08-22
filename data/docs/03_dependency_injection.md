# Dependency Injection

FastAPI has a powerful but simple Dependency Injection system that lets
you share logic (like database connections, auth checks, or shared query
parameters) across multiple path operations without repeating code.

## Creating a Dependency

A dependency is just a callable — usually a function — that can itself
take parameters the same way a path operation function does.

```python
async def common_params(q: str | None = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}

@app.get("/items/")
async def read_items(commons: dict = Depends(common_params)):
    return commons
```

## Sharing Dependencies Across Routes

Because a dependency is just a function, the same `common_params`
dependency can be reused in many different endpoints, keeping pagination
or filtering logic in one place instead of duplicated across routers.

## Dependencies with yield

For dependencies that need cleanup logic (closing a database session,
releasing a file handle), define the dependency using `yield` instead of
`return`. Code after the `yield` statement runs after the response has
been sent, functioning like a `finally` block.

## Sub-dependencies

Dependencies can themselves depend on other dependencies, forming a tree.
FastAPI resolves the whole tree and, by default, caches the result of a
dependency within a single request so it's not computed twice even if
several other dependencies rely on it.

## Global Dependencies

You can apply a dependency to an entire FastAPI application or to an
entire `APIRouter` by passing a `dependencies` list, which is useful for
things like requiring an API key on every route without adding it to each
function signature individually.
