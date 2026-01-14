# /// script
# requires-python = ">=3.10"
# dependencies = ["fastapi", "uvicorn", "pydantic", "httpx"]
# ///
"""Web API Error Handling with Result and Option.

This example demonstrates how to use Result and Option types for clean,
type-safe error handling in web APIs with FastAPI.

Key patterns:
- Result for operations that can fail (validation, not found errors)
- Option for optional lookups where absence is normal
- Domain error types that map to HTTP status codes
- Service layer returning Result/Option instead of raising exceptions
- Converting errors to FastAPI's HTTPException at route boundaries

Run with: uv run --script --with-editable . examples/web_api.py
Run as server: uv run --script --with-editable . examples/web_api.py --serve
"""

import sys
from dataclasses import dataclass

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from unwrappy import NOTHING, Err, Ok, Option, Result, Some, is_err, is_some, sequence_results

# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="Unwrappy Web API Example",
    description="Demonstrates Result-based error handling with FastAPI",
)

# =============================================================================
# Domain Models
# =============================================================================


@dataclass
class User:
    """User domain model."""

    id: int
    email: str
    name: str
    is_active: bool = True


class CreateUserRequest(BaseModel):
    """Request body for creating a user."""

    email: str
    name: str


# =============================================================================
# Domain Errors
# =============================================================================


@dataclass
class ValidationError:
    """Input validation failed."""

    field: str
    message: str


@dataclass
class NotFoundError:
    """Resource not found."""

    resource: str
    id: int | str


@dataclass
class ConflictError:
    """Resource already exists."""

    message: str


@dataclass
class InternalError:
    """Internal server error."""

    message: str


# Union of all domain errors
DomainError = ValidationError | NotFoundError | ConflictError | InternalError


# =============================================================================
# HTTP Error Mapping
# =============================================================================


@dataclass
class HTTPError:
    """Represents an HTTP error response."""

    status_code: int
    detail: str


def to_http_error(error: DomainError) -> HTTPError:
    """Map domain errors to HTTP status codes.

    This is the boundary where domain errors become HTTP responses.
    Keep this mapping in one place for consistency.
    """
    match error:
        case ValidationError(field, message):
            return HTTPError(422, f"{field}: {message}")
        case NotFoundError(resource, id):
            return HTTPError(404, f"{resource} with id={id} not found")
        case ConflictError(message):
            return HTTPError(409, message)
        case InternalError(message):
            return HTTPError(500, message)


# =============================================================================
# Validation Functions
# =============================================================================


def validate_email(email: str) -> Result[str, ValidationError]:
    """Validate email format."""
    if not email:
        return Err(ValidationError("email", "email is required"))
    if "@" not in email:
        return Err(ValidationError("email", "invalid email format"))
    if len(email) > 254:
        return Err(ValidationError("email", "email too long"))
    return Ok(email.lower().strip())


def validate_name(name: str) -> Result[str, ValidationError]:
    """Validate user name."""
    if not name:
        return Err(ValidationError("name", "name is required"))
    if len(name) < 2:
        return Err(ValidationError("name", "name must be at least 2 characters"))
    if len(name) > 100:
        return Err(ValidationError("name", "name too long"))
    return Ok(name.strip())


def validate_user_id(user_id: int) -> Result[int, ValidationError]:
    """Validate user ID."""
    if user_id <= 0:
        return Err(ValidationError("user_id", "must be positive"))
    return Ok(user_id)


def validate_create_user_request(
    request: CreateUserRequest,
) -> Result[CreateUserRequest, ValidationError]:
    """Validate entire create user request.

    Uses sequence_results to collect validation results.
    Fails fast on first error (use separate error collection for all errors).
    """
    # Validate each field and combine results
    email_result = validate_email(request.email)
    name_result = validate_name(request.name)

    # sequence_results: list[Result[T, E]] -> Result[list[T], E]
    # Fails on first error, or returns Ok with all values
    return sequence_results([email_result, name_result]).map(
        lambda values: CreateUserRequest(email=values[0], name=values[1])
    )


# =============================================================================
# Simulated Database
# =============================================================================

USERS_DB: dict[int, User] = {
    1: User(id=1, email="alice@example.com", name="Alice"),
    2: User(id=2, email="bob@example.com", name="Bob"),
}
NEXT_ID = 3


# =============================================================================
# Service Layer (Returns Result, never raises)
# =============================================================================


def find_user_by_id(user_id: int) -> Result[User, DomainError]:
    """Find user by ID.

    Returns Result instead of raising exceptions or returning None.
    The caller explicitly handles both success and error cases.
    """
    user = USERS_DB.get(user_id)
    if user is None:
        return Err(NotFoundError("User", user_id))
    return Ok(user)


def find_user_by_email(email: str) -> Option[User]:
    """Find user by email.

    Returns Option because absence is expected/normal when checking
    for duplicates. Compare with find_user_by_id which returns Result
    because absence there is an error (404).
    """
    for user in USERS_DB.values():
        if user.email == email:
            return Some(user)
    return NOTHING


def create_user(request: CreateUserRequest) -> Result[User, DomainError]:
    """Create a new user.

    Validates input, checks for conflicts, and creates the user.
    All errors are returned as Result, never raised.
    """
    global NEXT_ID

    # First validate the request
    validated = validate_create_user_request(request)
    if is_err(validated):
        return validated

    # Check if email already exists (Option pattern - absence is normal)
    if is_some(find_user_by_email(request.email)):
        return Err(ConflictError(f"User with email {request.email} already exists"))

    # Create the user
    user = User(id=NEXT_ID, email=request.email, name=request.name)
    USERS_DB[user.id] = user
    NEXT_ID += 1
    return Ok(user)


def update_user_email(user_id: int, new_email: str) -> Result[User, DomainError]:
    """Update a user's email.

    Uses early return pattern for clean, readable validation chain.
    """
    # Validate user_id
    id_result = validate_user_id(user_id)
    if is_err(id_result):
        return id_result

    # Find user
    user_result = find_user_by_id(id_result.unwrap())
    if is_err(user_result):
        return user_result
    user = user_result.unwrap()

    # Validate new email
    email_result = validate_email(new_email)
    if is_err(email_result):
        return email_result
    email = email_result.unwrap()

    # Check for conflicts
    if any(u.email == email and u.id != user.id for u in USERS_DB.values()):
        return Err(ConflictError(f"Email {email} is already in use"))

    # Update and return
    user.email = email
    return Ok(user)


# =============================================================================
# FastAPI Routes (The "controller" layer)
# =============================================================================


@app.get("/users/{user_id}")
def get_user(user_id: int) -> dict:
    """Get a user by ID.

    Demonstrates Result-based error handling with FastAPI's HTTPException.
    The service layer returns Result, which we convert to HTTP responses.
    """
    result = validate_user_id(user_id).and_then(find_user_by_id)

    match result:
        case Ok(user):
            return {"id": user.id, "email": user.email, "name": user.name}
        case Err(error):
            http_error = to_http_error(error)
            raise HTTPException(
                status_code=http_error.status_code,
                detail=http_error.detail,
            )


@app.post("/users", status_code=201)
def create_user_endpoint(request: CreateUserRequest) -> dict:
    """Create a new user.

    FastAPI automatically validates the request body using Pydantic.
    Our service layer provides additional domain validation via Result.
    """
    result = create_user(request)

    match result:
        case Ok(user):
            return {"id": user.id, "email": user.email, "name": user.name}
        case Err(error):
            http_error = to_http_error(error)
            raise HTTPException(
                status_code=http_error.status_code,
                detail=http_error.detail,
            )


class UpdateEmailRequest(BaseModel):
    """Request body for updating email."""

    new_email: str


@app.patch("/users/{user_id}/email")
def update_email(user_id: int, request: UpdateEmailRequest) -> dict:
    """Update a user's email.

    Demonstrates combining path parameters with request body validation.
    """
    result = update_user_email(user_id, request.new_email)

    match result:
        case Ok(user):
            return {"id": user.id, "email": user.email, "name": user.name}
        case Err(error):
            http_error = to_http_error(error)
            raise HTTPException(
                status_code=http_error.status_code,
                detail=http_error.detail,
            )


# =============================================================================
# Before/After Comparison
# =============================================================================

# BEFORE: Exception-based approach
# --------------------------------
#
# class UserNotFoundException(Exception):
#     pass
#
# class ValidationException(Exception):
#     pass
#
# def get_user_old(user_id: int) -> User:
#     if user_id <= 0:
#         raise ValidationException("user_id must be positive")
#     user = USERS_DB.get(user_id)
#     if user is None:
#         raise UserNotFoundException(f"User {user_id} not found")
#     return user
#
# # Handler has to know about all possible exceptions
# def handle_get_user_old(user_id: int) -> tuple[int, dict]:
#     try:
#         user = get_user_old(user_id)
#         return (200, {"id": user.id, "email": user.email, "name": user.name})
#     except ValidationException as e:
#         return (422, {"detail": str(e)})
#     except UserNotFoundException as e:
#         return (404, {"detail": str(e)})
#     except Exception as e:
#         return (500, {"detail": "Internal server error"})
#
# Problems with exception-based approach:
# 1. No type safety - caller might miss an exception type
# 2. Control flow is hidden - exceptions jump up the stack
# 3. Easy to forget to handle errors
# 4. Hard to compose operations
#
# AFTER: Result-based approach (shown above)
# ------------------------------------------
# 1. Type-safe - Result[User, DomainError] makes errors explicit
# 2. Control flow is visible - errors flow through the chain
# 3. Compiler helps ensure errors are handled (with match)
# 4. Easy to compose with map, and_then, etc.


# =============================================================================
# Demo
# =============================================================================


def demo() -> None:
    """Run demo using FastAPI TestClient to show real HTTP interactions."""
    client = TestClient(app)

    print("=" * 60)
    print("Web API Error Handling with Result + FastAPI")
    print("=" * 60)

    # Success cases
    print("\n1. GET /users/1 - Get existing user:")
    response = client.get("/users/1")
    print(f"   Status: {response.status_code}, Body: {response.json()}")

    print("\n2. POST /users - Create new user:")
    response = client.post("/users", json={"email": "charlie@example.com", "name": "Charlie"})
    print(f"   Status: {response.status_code}, Body: {response.json()}")

    # Error cases - these raise HTTPException which TestClient captures
    print("\n3. GET /users/999 - Get non-existent user (404):")
    response = client.get("/users/999")
    print(f"   Status: {response.status_code}, Body: {response.json()}")

    print("\n4. POST /users - Create with invalid email (422):")
    response = client.post("/users", json={"email": "invalid-email", "name": "Dave"})
    print(f"   Status: {response.status_code}, Body: {response.json()}")

    print("\n5. POST /users - Create with existing email (409):")
    response = client.post("/users", json={"email": "alice@example.com", "name": "Alice2"})
    print(f"   Status: {response.status_code}, Body: {response.json()}")

    print("\n6. PATCH /users/-1/email - Invalid user_id (422):")
    response = client.patch("/users/-1/email", json={"new_email": "new@example.com"})
    print(f"   Status: {response.status_code}, Body: {response.json()}")

    print("\n7. PATCH /users/1/email - Conflicting email (409):")
    response = client.patch("/users/1/email", json={"new_email": "bob@example.com"})
    print(f"   Status: {response.status_code}, Body: {response.json()}")

    print("\n8. PATCH /users/1/email - Successful update:")
    response = client.patch("/users/1/email", json={"new_email": "alice.new@example.com"})
    print(f"   Status: {response.status_code}, Body: {response.json()}")


if __name__ == "__main__":
    if "--serve" in sys.argv:
        print("Starting FastAPI server at http://localhost:8000")
        print("API docs available at http://localhost:8000/docs")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        demo()
