# Serialization

unwrappy provides JSON serialization support for integration with task queues and distributed systems like Celery, Temporal, and DBOS.

## Basic Usage

### Using dumps/loads

The simplest way to serialize unwrappy types:

```python
from unwrappy import Ok, Err, Some, NOTHING, dumps, loads

# Serialize Result
encoded = dumps(Ok(42))
# '{"__unwrappy_type__": "Ok", "value": 42}'

encoded = dumps(Err("not found"))
# '{"__unwrappy_type__": "Err", "error": "not found"}'

# Serialize Option
encoded = dumps(Some("hello"))
# '{"__unwrappy_type__": "Some", "value": "hello"}'

encoded = dumps(NOTHING)
# '{"__unwrappy_type__": "Nothing"}'

# Deserialize
decoded = loads(encoded)  # Returns the original type
```

### Using Standard json Module

For more control, use the encoder and decoder directly:

```python
import json
from unwrappy import Ok, ResultEncoder, result_decoder

# Serialize
encoded = json.dumps(Ok(42), cls=ResultEncoder)

# Deserialize
decoded = json.loads(encoded, object_hook=result_decoder)
```

## JSON Format

unwrappy uses a tagged format for serialization:

### Result Types

```json
// Ok
{"__unwrappy_type__": "Ok", "value": <any JSON value>}

// Err
{"__unwrappy_type__": "Err", "error": <any JSON value>}
```

### Option Types

```json
// Some
{"__unwrappy_type__": "Some", "value": <any JSON value>}

// Nothing
{"__unwrappy_type__": "Nothing"}
```

## Nested Serialization

Complex nested structures are handled automatically:

```python
from unwrappy import Ok, Some, dumps, loads

# Nested structures
data = Ok({
    "user": {"name": "Alice", "age": 30},
    "settings": Some({"theme": "dark"})
})

encoded = dumps(data)
decoded = loads(encoded)

# decoded is Ok({"user": {...}, "settings": Some({...})})
```

## LazyResult Limitation

!!! danger "LazyResult/LazyOption cannot be serialized"
    Lazy types contain function references that cannot be converted to JSON.

    ```python
    from unwrappy import LazyResult, dumps

    lazy = LazyResult.ok(42).map(lambda x: x * 2)

    # This raises TypeError!
    dumps(lazy)
    ```

    **Solution**: Always call `.collect()` first:

    ```python
    result = await lazy.collect()
    dumps(result)  # Works!
    ```

## Framework Integration

### Celery

Register a custom serializer for Celery tasks:

```python
from kombu.serialization import register
from unwrappy.serde import dumps, loads

# Register the serializer
register(
    'unwrappy-json',
    dumps,
    loads,
    content_type='application/x-unwrappy-json',
    content_encoding='utf-8'
)

# Configure Celery to use it
app.conf.update(
    task_serializer='unwrappy-json',
    result_serializer='unwrappy-json',
    accept_content=['unwrappy-json'],
)
```

Now your tasks can return Result types:

```python
from unwrappy import Ok, Err, Result

@app.task
def process_data(data: dict) -> Result[dict, str]:
    try:
        processed = transform(data)
        return Ok(processed)
    except ValueError as e:
        return Err(str(e))
```

### Temporal

Create a custom data converter for Temporal workflows:

```python
from temporalio.converter import (
    DataConverter,
    JSONPlainPayloadConverter,
)
from unwrappy.serde import ResultEncoder, result_decoder
import json

class UnwrappyJSONPayloadConverter(JSONPlainPayloadConverter):
    def encode(self, value):
        return json.dumps(value, cls=ResultEncoder).encode()

    def decode(self, data, type_hint=None):
        return json.loads(data.decode(), object_hook=result_decoder)

# Use in your Temporal client
client = await Client.connect(
    "localhost:7233",
    data_converter=DataConverter(
        payload_converters=[UnwrappyJSONPayloadConverter()]
    )
)
```

### DBOS

Create a custom serializer for DBOS workflows:

```python
from dbos import DBOS
from unwrappy.serde import dumps, loads

class UnwrappySerializer:
    def serialize(self, obj) -> str:
        return dumps(obj)

    def deserialize(self, data: str):
        return loads(data)

# Configure DBOS
DBOS.set_serializer(UnwrappySerializer())
```

### FastAPI Response Models

For API responses, convert to dict before returning:

```python
from fastapi import FastAPI
from unwrappy import Ok, Err, Result

app = FastAPI()

@app.get("/users/{user_id}")
def get_user(user_id: int) -> dict:
    result: Result[User, str] = user_service.get(user_id)

    match result:
        case Ok(user):
            return {"status": "ok", "data": user.dict()}
        case Err(error):
            return {"status": "error", "message": error}
```

Or use `unwrap_or_raise` for cleaner code:

```python
from fastapi import HTTPException

@app.get("/users/{user_id}")
def get_user(user_id: int) -> dict:
    user = user_service.get(user_id).unwrap_or_raise(
        lambda e: HTTPException(404, e)
    )
    return user.dict()
```

## Custom Serialization

### Extending for Custom Types

If you have custom types inside Results, ensure they're JSON-serializable:

```python
from dataclasses import dataclass, asdict
from unwrappy import Ok, dumps
import json

@dataclass
class User:
    id: int
    name: str

    def to_dict(self):
        return asdict(self)

# Option 1: Convert before serializing
user = User(1, "Alice")
dumps(Ok(user.to_dict()))

# Option 2: Custom encoder
class CustomEncoder(ResultEncoder):
    def default(self, obj):
        if isinstance(obj, User):
            return obj.to_dict()
        return super().default(obj)

json.dumps(Ok(user), cls=CustomEncoder)
```

### Pydantic Integration

With Pydantic models:

```python
from pydantic import BaseModel
from unwrappy import Ok, dumps

class User(BaseModel):
    id: int
    name: str

user = User(id=1, name="Alice")

# Pydantic models have .model_dump()
dumps(Ok(user.model_dump()))
```

## Error Handling

The decoder gracefully handles non-unwrappy JSON:

```python
from unwrappy import loads

# Regular JSON passes through unchanged
loads('{"name": "Alice"}')  # Returns {"name": "Alice"}

# Only tagged objects become unwrappy types
loads('{"__unwrappy_type__": "Ok", "value": 42}')  # Returns Ok(42)
```

## Best Practices

1. **Always collect LazyResult before serializing**
   ```python
   result = await lazy.collect()
   encoded = dumps(result)
   ```

2. **Use structured errors for better debugging**
   ```python
   @dataclass
   class AppError:
       code: str
       message: str

   # Serializes cleanly
   dumps(Err(AppError("NOT_FOUND", "User not found").__dict__))
   ```

3. **Validate after deserialization**
   ```python
   decoded = loads(data)
   if not isinstance(decoded, (Ok, Err)):
       raise ValueError("Expected Result type")
   ```

4. **Consider versioning for production systems**
   ```python
   encoded = dumps({"version": 1, "result": Ok(data)})
   ```
