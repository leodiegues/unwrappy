# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Database Operations with Option and Result.

This example demonstrates how to use Option and Result types for
clean database operations:
- Option for nullable lookups (user might not exist)
- Result for operations that can fail (connection errors, constraints)
- Repository pattern with explicit error handling
- Combining Option and Result in realistic workflows

Run with: uv run python examples/database.py
"""

from dataclasses import dataclass
from typing import Protocol

from unwrappy import (
    NOTHING,
    Err,
    Ok,
    Option,
    Result,
    Some,
    from_nullable,
    sequence_options,
)

# =============================================================================
# Domain Models
# =============================================================================


@dataclass
class User:
    id: int
    email: str
    name: str
    role: str = "user"


@dataclass
class Post:
    id: int
    author_id: int
    title: str
    content: str


@dataclass
class UserProfile:
    """Composite of User and their posts."""

    user: User
    posts: list[Post]
    post_count: int


# =============================================================================
# Database Errors
# =============================================================================


@dataclass
class DatabaseError:
    """Base class for database errors."""

    message: str


@dataclass
class ConnectionError(DatabaseError):
    """Database connection failed."""

    pass


@dataclass
class ConstraintError(DatabaseError):
    """Database constraint violation."""

    constraint: str


# =============================================================================
# Simulated Database
# =============================================================================

USERS: dict[int, User] = {
    1: User(id=1, email="alice@example.com", name="Alice", role="admin"),
    2: User(id=2, email="bob@example.com", name="Bob", role="user"),
    3: User(id=3, email="charlie@example.com", name="Charlie", role="user"),
}

POSTS: dict[int, Post] = {
    1: Post(id=1, author_id=1, title="Hello World", content="My first post!"),
    2: Post(id=2, author_id=1, title="Python Tips", content="Here are some tips..."),
    3: Post(id=3, author_id=2, title="Bob's Blog", content="Welcome to my blog!"),
}


# =============================================================================
# Repository Protocol
# =============================================================================


class UserRepository(Protocol):
    """Repository interface for User operations."""

    def find_by_id(self, user_id: int) -> Option[User]:
        """Find user by ID. Returns NOTHING if not found."""
        ...

    def find_by_email(self, email: str) -> Option[User]:
        """Find user by email. Returns NOTHING if not found."""
        ...

    def find_all_by_role(self, role: str) -> list[User]:
        """Find all users with a given role."""
        ...

    def create(self, user: User) -> Result[User, DatabaseError]:
        """Create a new user. May fail on constraint violations."""
        ...


# =============================================================================
# Repository Implementation
# =============================================================================


class InMemoryUserRepository:
    """In-memory implementation of UserRepository."""

    def __init__(self, users: dict[int, User]):
        self._users = users
        self._next_id = max(users.keys(), default=0) + 1

    def find_by_id(self, user_id: int) -> Option[User]:
        """Find user by ID.

        This is the key pattern: instead of returning User | None,
        we return Option[User] which makes the caller explicitly
        handle both cases.
        """
        return from_nullable(self._users.get(user_id))

    def find_by_email(self, email: str) -> Option[User]:
        """Find user by email."""
        for user in self._users.values():
            if user.email == email:
                return Some(user)
        return NOTHING

    def find_all_by_role(self, role: str) -> list[User]:
        """Find all users with a given role."""
        return [u for u in self._users.values() if u.role == role]

    def create(self, email: str, name: str, role: str = "user") -> Result[User, DatabaseError]:
        """Create a new user.

        Returns Result to handle constraint violations explicitly.
        """
        # Check unique email constraint
        if any(u.email == email for u in self._users.values()):
            return Err(ConstraintError("unique_email", f"Email {email} already exists"))

        user = User(id=self._next_id, email=email, name=name, role=role)
        self._users[user.id] = user
        self._next_id += 1
        return Ok(user)

    def delete(self, user_id: int) -> Option[User]:
        """Delete a user by ID. Returns the deleted user if found."""
        return from_nullable(self._users.pop(user_id, None))


class InMemoryPostRepository:
    """In-memory implementation for Post operations."""

    def __init__(self, posts: dict[int, Post]):
        self._posts = posts

    def find_by_id(self, post_id: int) -> Option[Post]:
        """Find post by ID."""
        return from_nullable(self._posts.get(post_id))

    def find_by_author(self, author_id: int) -> list[Post]:
        """Find all posts by an author."""
        return [p for p in self._posts.values() if p.author_id == author_id]

    def count_by_author(self, author_id: int) -> int:
        """Count posts by an author."""
        return len(self.find_by_author(author_id))


# =============================================================================
# Service Layer - Combining Option and Result
# =============================================================================


def get_user_email(user_repo: InMemoryUserRepository, user_id: int) -> Option[str]:
    """Get user's email if they exist.

    Demonstrates Option chaining: find user -> extract email.
    """
    return user_repo.find_by_id(user_id).map(lambda u: u.email)


def get_user_profile(
    user_repo: InMemoryUserRepository, post_repo: InMemoryPostRepository, user_id: int
) -> Option[UserProfile]:
    """Get a user's complete profile with their posts.

    Demonstrates combining multiple Option operations.
    """
    return user_repo.find_by_id(user_id).map(
        lambda user: UserProfile(
            user=user,
            posts=post_repo.find_by_author(user_id),
            post_count=post_repo.count_by_author(user_id),
        )
    )


def get_post_author_name(
    user_repo: InMemoryUserRepository, post_repo: InMemoryPostRepository, post_id: int
) -> Option[str]:
    """Get the author's name for a post.

    Demonstrates chaining Options: find post -> find author -> get name.
    """
    return (
        post_repo.find_by_id(post_id)
        .and_then(lambda post: user_repo.find_by_id(post.author_id))
        .map(lambda user: user.name)
    )


def create_user_if_not_exists(user_repo: InMemoryUserRepository, email: str, name: str) -> Result[User, DatabaseError]:
    """Create a user only if email doesn't exist.

    Demonstrates converting Option to Result with ok_or.
    """
    # Check if user already exists
    existing = user_repo.find_by_email(email)

    match existing:
        case Some(user):
            return Ok(user)  # Return existing user
        case _:
            return user_repo.create(email, name)


def get_admin_emails(user_repo: InMemoryUserRepository) -> list[str]:
    """Get emails of all admin users.

    Simple mapping without Option - all users have emails.
    """
    return [u.email for u in user_repo.find_all_by_role("admin")]


def find_users_by_ids(user_repo: InMemoryUserRepository, ids: list[int]) -> list[User]:
    """Find multiple users by IDs, returning only those that exist.

    Uses traverse_options to look up each ID and filter out missing.
    """
    options = [user_repo.find_by_id(id) for id in ids]
    # sequence_options: returns Some only if ALL are present
    # We want to return those that exist, so we filter instead
    return [opt.unwrap() for opt in options if opt.is_some()]


def find_all_users_by_ids(user_repo: InMemoryUserRepository, ids: list[int]) -> Option[list[User]]:
    """Find multiple users by IDs, failing if ANY is missing.

    Uses sequence_options - returns NOTHING if any ID not found.
    """
    options = [user_repo.find_by_id(id) for id in ids]
    return sequence_options(options)


# =============================================================================
# Before/After Comparison
# =============================================================================

# BEFORE: None-based approach
# ---------------------------
#
# def get_user_email_old(repo, user_id: int) -> str | None:
#     user = repo.find_by_id(user_id)  # Returns User | None
#     if user is None:
#         return None
#     return user.email
#
# def get_post_author_name_old(user_repo, post_repo, post_id: int) -> str | None:
#     post = post_repo.find_by_id(post_id)
#     if post is None:
#         return None
#     author = user_repo.find_by_id(post.author_id)
#     if author is None:
#         return None
#     return author.name
#
# Problems:
# 1. Easy to forget None checks (NullPointerException-style bugs)
# 2. Nested conditionals become hard to read
# 3. No type-level distinction between "not found" and "has value"
# 4. Caller might accidentally use None value without checking
#
# AFTER: Option-based approach (shown above)
# ------------------------------------------
# 1. Type system enforces handling both cases
# 2. Chaining with map/and_then is clean and readable
# 3. Clear semantic: NOTHING means "not found"
# 4. unwrap_or provides safe defaults


# =============================================================================
# Demo
# =============================================================================


def main() -> None:
    print("=" * 60)
    print("Database Operations with Option and Result")
    print("=" * 60)

    # Initialize repositories
    user_repo = InMemoryUserRepository(USERS.copy())
    post_repo = InMemoryPostRepository(POSTS.copy())

    # Option for lookups
    print("\n--- Option for Lookups ---\n")

    print("1. Find existing user:")
    user_opt = user_repo.find_by_id(1)
    match user_opt:
        case Some(user):
            print(f"   Found: {user.name} ({user.email})")
        case _:
            print("   Not found")

    print("\n2. Find non-existent user:")
    user_opt = user_repo.find_by_id(999)
    match user_opt:
        case Some(user):
            print(f"   Found: {user.name}")
        case _:
            print("   Not found")

    print("\n3. Get user email with Option chain:")
    email = get_user_email(user_repo, 1)
    print(f"   User 1 email: {email.unwrap_or('unknown')}")
    email = get_user_email(user_repo, 999)
    print(f"   User 999 email: {email.unwrap_or('unknown')}")

    # Chaining Options
    print("\n--- Chaining Options ---\n")

    print("4. Get post author name (post -> author -> name):")
    name = get_post_author_name(user_repo, post_repo, 1)
    print(f"   Post 1 author: {name.unwrap_or('unknown')}")
    name = get_post_author_name(user_repo, post_repo, 999)
    print(f"   Post 999 author: {name.unwrap_or('unknown')}")

    print("\n5. Get user profile:")
    profile_opt = get_user_profile(user_repo, post_repo, 1)
    match profile_opt:
        case Some(profile):
            print(f"   {profile.user.name}: {profile.post_count} posts")
            for post in profile.posts:
                print(f"     - {post.title}")
        case _:
            print("   User not found")

    # Result for operations that can fail
    print("\n--- Result for Fallible Operations ---\n")

    print("6. Create user with unique email:")
    result = user_repo.create("dave@example.com", "Dave")
    match result:
        case Ok(user):
            print(f"   Created: {user.name} (id={user.id})")
        case Err(error):
            print(f"   Error: {error.message}")

    print("\n7. Create user with duplicate email:")
    result = user_repo.create("alice@example.com", "Another Alice")
    match result:
        case Ok(user):
            print(f"   Created: {user.name}")
        case Err(error):
            print(f"   Error: {error.message}")

    # Combining Option and Result
    print("\n--- Option to Result Conversion ---\n")

    print("8. Get user or create if not exists:")
    result = create_user_if_not_exists(user_repo, "eve@example.com", "Eve")
    match result:
        case Ok(user):
            print(f"   User: {user.name} (id={user.id})")
        case Err(error):
            print(f"   Error: {error.message}")

    result = create_user_if_not_exists(user_repo, "alice@example.com", "Alice Clone")
    match result:
        case Ok(user):
            print(f"   Existing user: {user.name} (id={user.id})")
        case Err(error):
            print(f"   Error: {error.message}")

    # Batch operations with Option
    print("\n--- Batch Lookups ---\n")

    print("9. Find users by IDs (partial match allowed):")
    users = find_users_by_ids(user_repo, [1, 999, 2])
    print(f"   Found {len(users)} users: {[u.name for u in users]}")

    print("\n10. Find users by IDs (all must exist):")
    users_opt = find_all_users_by_ids(user_repo, [1, 2])
    match users_opt:
        case Some(users):
            print(f"   All found: {[u.name for u in users]}")
        case _:
            print("   Some users not found")

    users_opt = find_all_users_by_ids(user_repo, [1, 999])
    match users_opt:
        case Some(users):
            print(f"   All found: {[u.name for u in users]}")
        case _:
            print("   Some users not found")


if __name__ == "__main__":
    main()
