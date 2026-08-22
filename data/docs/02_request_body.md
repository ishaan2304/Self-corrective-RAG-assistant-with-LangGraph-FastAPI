# Request Body

To send data from a client to your API, declare it as a request body using
a Pydantic model. FastAPI reads the body as JSON, validates the data,
converts it into the declared types, and gives you editor autocompletion.

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool | None = None

@app.post("/items/")
async def create_item(item: Item):
    return item
```

## Combining Path, Query, and Body Parameters

FastAPI is smart enough to figure out where each function parameter comes
from. Parameters that match path variables are taken from the path;
parameters that are Pydantic models are taken from the request body;
singular types (str, int, float, bool) that don't match a path variable
are interpreted as query parameters.

## Request Body + Path Parameters

You can declare path parameters and a request body at the same time.
FastAPI recognizes each by their type and name and pulls data from the
correct place.

## Multiple Body Parameters

If you declare more than one Pydantic model in a single path operation
function, FastAPI expects a JSON body with each parameter's name as a
top-level key, nesting each model's fields under it, rather than merging
all fields into one flat object.

## Field Validation

Beyond type checking, you can add extra validation using Pydantic's
`Field` function, such as `min_length`, `max_length`, `gt`, and `le`, and
FastAPI will include these constraints in the generated OpenAPI schema so
they show up in the interactive docs.
