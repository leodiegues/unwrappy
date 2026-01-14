# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Async Patterns with LazyResult.

This example demonstrates async patterns:
- LazyResult for composing async operations
- Async service composition with error handling
- Side effects with tee() and inspect_err()
- Error recovery with or_else()

Run with: uv run python examples/async_patterns.py
"""

import asyncio
from dataclasses import dataclass

from unwrappy import Err, LazyResult, Ok, Result, is_err, sequence_results

# =============================================================================
# Domain Models
# =============================================================================


@dataclass
class User:
    id: int
    name: str
    email: str


@dataclass
class Post:
    id: int
    author_id: int
    title: str
    likes: int


@dataclass
class UserProfile:
    user: User
    follower_count: int
    post_count: int


# =============================================================================
# Simulated Async Services
# =============================================================================


async def fetch_user(user_id: int) -> Result[User, str]:
    """Simulate fetching a user from an API."""
    await asyncio.sleep(0.01)  # Simulate network delay

    users = {
        1: User(id=1, name="Alice", email="alice@example.com"),
        2: User(id=2, name="Bob", email="bob@example.com"),
    }

    user = users.get(user_id)
    if user is None:
        return Err(f"User {user_id} not found")
    return Ok(user)


async def fetch_follower_count(user_id: int) -> Result[int, str]:
    """Simulate fetching follower count."""
    await asyncio.sleep(0.01)

    counts = {1: 1500, 2: 250}
    return Ok(counts.get(user_id, 0))


async def fetch_post_count(user_id: int) -> Result[int, str]:
    """Simulate fetching post count."""
    await asyncio.sleep(0.01)

    counts = {1: 42, 2: 7}
    return Ok(counts.get(user_id, 0))


# =============================================================================
# LazyResult Patterns
# =============================================================================


async def get_user_profile_sequential(user_id: int) -> Result[UserProfile, str]:
    """Build a user profile by chaining async operations.

    This pattern uses regular async/await with Result.
    Clean but requires explicit handling at each step.
    """
    user_result = await fetch_user(user_id)
    if is_err(user_result):
        return user_result

    user = user_result.unwrap()

    followers_result = await fetch_follower_count(user_id)
    if is_err(followers_result):
        return followers_result

    posts_result = await fetch_post_count(user_id)
    if is_err(posts_result):
        return posts_result

    return Ok(
        UserProfile(
            user=user,
            follower_count=followers_result.unwrap(),
            post_count=posts_result.unwrap(),
        )
    )


async def get_user_profile_lazy(user_id: int) -> Result[UserProfile, str]:
    """Build a user profile by composing async operations.

    For multi-step dependent operations, use async/await with Result.
    LazyResult is best for linear transform chains, not complex branching.
    """
    # Fetch user first
    user_result = await fetch_user(user_id)
    if is_err(user_result):
        return user_result

    user = user_result.unwrap()

    # Fetch related data (could be parallelized with asyncio.gather)
    followers_result = await fetch_follower_count(user_id)
    if is_err(followers_result):
        return followers_result

    posts_result = await fetch_post_count(user_id)
    if is_err(posts_result):
        return posts_result

    return Ok(
        UserProfile(
            user=user,
            follower_count=followers_result.unwrap(),
            post_count=posts_result.unwrap(),
        )
    )


async def fetch_user_with_logging(user_id: int) -> Result[User, str]:
    """Fetch user with side effect logging.

    Demonstrates tee() for success logging and inspect_err() for error logging.
    """
    result = await (
        LazyResult.from_awaitable(fetch_user(user_id))
        .tee(lambda user: print(f"    [LOG] Fetched user: {user.name}"))
        .inspect_err(lambda err: print(f"    [ERROR] {err}"))
    ).collect()

    return result


async def fetch_user_with_fallback(primary_id: int, fallback_id: int) -> Result[User, str]:
    """Try primary user, fall back to another on failure.

    Demonstrates or_else() for error recovery.
    Note: or_else expects a function returning Result, not LazyResult.
    """
    result = await (
        LazyResult.from_awaitable(fetch_user(primary_id))
        .inspect_err(lambda e: print(f"    Primary failed: {e}"))
        .or_else(lambda _: fetch_user(fallback_id))  # Returns awaitable Result
        .tee(lambda u: print(f"    Success: {u.name}"))
    ).collect()

    return result


async def transform_user_name(user_id: int) -> Result[str, str]:
    """Fetch user and transform with sync operations.

    LazyResult handles both sync and async functions in map().
    """
    result = await (
        LazyResult.from_awaitable(fetch_user(user_id))
        .map(lambda user: user.name)  # sync
        .map(lambda name: name.upper())  # sync
        .map(lambda name: f"@{name}")  # sync
    ).collect()

    return result


# =============================================================================
# Parallel Operations
# =============================================================================


async def fetch_multiple_users(user_ids: list[int]) -> list[Result[User, str]]:
    """Fetch multiple users in parallel."""
    tasks = [fetch_user(uid) for uid in user_ids]
    return await asyncio.gather(*tasks)


async def fetch_all_users(user_ids: list[int]) -> Result[list[User], str]:
    """Fetch multiple users, failing if any fails.

    Uses sequence_results to convert list[Result[T, E]] -> Result[list[T], E].
    """
    results = await fetch_multiple_users(user_ids)
    return sequence_results(results)


# =============================================================================
# Before/After Comparison
# =============================================================================

# BEFORE: Manual async error handling
# -----------------------------------
#
# async def get_profile_old(user_id: int) -> UserProfile | None:
#     try:
#         user_resp = await http_client.get(f"/users/{user_id}")
#         user = User(**user_resp.json())
#     except Exception as e:
#         logger.error(f"Failed to fetch user: {e}")
#         return None
#
#     try:
#         followers_resp = await http_client.get(f"/users/{user_id}/followers/count")
#         followers = followers_resp.json()["count"]
#     except Exception:
#         followers = 0  # Default on failure
#
#     try:
#         posts_resp = await http_client.get(f"/users/{user_id}/posts/count")
#         posts = posts_resp.json()["count"]
#     except Exception:
#         posts = 0
#
#     return UserProfile(user=user, follower_count=followers, post_count=posts)
#
# Problems:
# 1. Try/except scattered throughout the code
# 2. Inconsistent error handling (some fail, some default)
# 3. Easy to miss error cases
# 4. Business logic obscured by error handling
#
# AFTER: LazyResult composition (shown above)
# -------------------------------------------
# 1. Errors are explicit in the return type
# 2. Consistent error propagation through the chain
# 3. Type system ensures errors are handled
# 4. Clean, readable pipeline of operations


# =============================================================================
# Demo
# =============================================================================


async def main() -> None:
    print("=" * 60)
    print("Async Patterns with LazyResult")
    print("=" * 60)

    # Basic fetch
    print("\n--- Basic LazyResult ---\n")

    print("1. Simple async fetch (success):")
    result = await LazyResult.from_awaitable(fetch_user(1)).collect()
    match result:
        case Ok(user):
            print(f"   Found: {user.name} ({user.email})")
        case Err(error):
            print(f"   Error: {error}")

    print("\n2. Simple async fetch (failure):")
    result = await LazyResult.from_awaitable(fetch_user(999)).collect()
    match result:
        case Ok(user):
            print(f"   Found: {user.name}")
        case Err(error):
            print(f"   Error: {error}")

    # Composed operations
    print("\n--- Service Composition ---\n")

    print("3. Build user profile (lazy composition):")
    result = await get_user_profile_lazy(1)
    match result:
        case Ok(profile):
            print(f"   User: {profile.user.name}")
            print(f"   Followers: {profile.follower_count}")
            print(f"   Posts: {profile.post_count}")
        case Err(error):
            print(f"   Error: {error}")

    print("\n4. Profile for non-existent user:")
    result = await get_user_profile_lazy(999)
    match result:
        case Ok(profile):
            print(f"   User: {profile.user.name}")
        case Err(error):
            print(f"   Error: {error}")

    # Side effects
    print("\n--- Side Effects (tee/inspect_err) ---\n")

    print("5. Fetch with logging (success):")
    result = await fetch_user_with_logging(1)
    match result:
        case Ok(user):
            print(f"   Result: {user.name}")
        case Err(error):
            print(f"   Result: Error - {error}")

    print("\n6. Fetch with logging (failure):")
    result = await fetch_user_with_logging(999)
    match result:
        case Ok(user):
            print(f"   Result: {user.name}")
        case Err(error):
            print(f"   Result: Error - {error}")

    # Error recovery
    print("\n--- Error Recovery (or_else) ---\n")

    print("7. Fetch with fallback (primary fails):")
    result = await fetch_user_with_fallback(999, 1)
    match result:
        case Ok(user):
            print(f"   Final result: {user.name}")
        case Err(error):
            print(f"   Final result: Error - {error}")

    print("\n8. Fetch with fallback (primary succeeds):")
    result = await fetch_user_with_fallback(1, 2)
    match result:
        case Ok(user):
            print(f"   Final result: {user.name}")
        case Err(error):
            print(f"   Final result: Error - {error}")

    # Sync transformations in async chain
    print("\n--- Sync Transforms in Async Chain ---\n")

    print("9. Transform user name:")
    result = await transform_user_name(1)
    match result:
        case Ok(name):
            print(f"   Transformed: {name}")
        case Err(error):
            print(f"   Error: {error}")

    # Parallel operations
    print("\n--- Parallel Operations ---\n")

    print("10. Fetch multiple users (some fail):")
    results = await fetch_multiple_users([1, 999, 2])
    for uid, result in zip([1, 999, 2], results):
        match result:
            case Ok(user):
                print(f"   User {uid}: {user.name}")
            case Err(error):
                print(f"   User {uid}: {error}")

    print("\n11. Fetch all or fail (valid IDs):")
    result = await fetch_all_users([1, 2])
    match result:
        case Ok(users):
            print(f"   All found: {[u.name for u in users]}")
        case Err(error):
            print(f"   Error: {error}")

    print("\n12. Fetch all or fail (includes invalid):")
    result = await fetch_all_users([1, 999, 2])
    match result:
        case Ok(users):
            print(f"   All found: {[u.name for u in users]}")
        case Err(error):
            print(f"   Error: {error}")


if __name__ == "__main__":
    asyncio.run(main())
