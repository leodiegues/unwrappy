# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Error Handling Patterns with Result.

This example demonstrates advanced error handling patterns:
- ChainedError for context propagation
- Error recovery with or_else
- Fallback strategies
- Before/After comparison with exceptions

Run with: uv run python examples/error_handling.py
"""

from dataclasses import dataclass
from pathlib import Path

from unwrappy import ChainedError, Err, Ok, Result, is_err

# =============================================================================
# Domain Types
# =============================================================================


@dataclass
class Config:
    """Application configuration."""

    database_url: str
    api_key: str
    max_connections: int
    debug: bool = False


@dataclass
class ConfigError:
    """Configuration error."""

    message: str


# =============================================================================
# Context Chaining with ChainedError
# =============================================================================


def read_file(path: str) -> Result[str, str]:
    """Read a file's contents."""
    try:
        return Ok(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return Err(f"file not found: {path}")
    except PermissionError:
        return Err(f"permission denied: {path}")


def parse_config_value(content: str, key: str) -> Result[str, str]:
    """Parse a key=value from config content."""
    for line in content.strip().split("\n"):
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return Ok(v.strip())
    return Err(f"missing key: {key}")


def parse_int_value(value: str, key: str) -> Result[int, str]:
    """Parse a string as integer."""
    try:
        return Ok(int(value))
    except ValueError:
        return Err(f"invalid integer for {key}: {value}")


def load_config(path: str) -> Result[Config, ChainedError]:
    """Load configuration from a file.

    Demonstrates context chaining: each step adds context to errors.
    Uses early return pattern for clean, readable code.
    """
    content_result = read_file(path).context(f"reading config file '{path}'")
    if is_err(content_result):
        return content_result
    content = content_result.unwrap()

    db_url_result = parse_config_value(content, "database_url").context("parsing database_url")
    if is_err(db_url_result):
        return db_url_result

    api_key_result = parse_config_value(content, "api_key").context("parsing api_key")
    if is_err(api_key_result):
        return api_key_result

    max_conn_result = (
        parse_config_value(content, "max_connections")
        .and_then(lambda mc: parse_int_value(mc, "max_connections"))
        .context("parsing max_connections")
    )
    if is_err(max_conn_result):
        return max_conn_result

    return Ok(
        Config(
            database_url=db_url_result.unwrap(),
            api_key=api_key_result.unwrap(),
            max_connections=max_conn_result.unwrap(),
        )
    )


# =============================================================================
# Error Recovery with or_else
# =============================================================================


def load_from_primary(path: str) -> Result[str, str]:
    """Try to load from primary source."""
    return read_file(path)


def load_from_backup(path: str) -> Result[str, str]:
    """Try to load from backup source."""
    return read_file(path)


def load_default() -> Result[str, str]:
    """Return default content."""
    return Ok("database_url=sqlite:///:memory:\napi_key=dev-key\nmax_connections=5")


def load_with_fallback(primary: str, backup: str) -> Result[str, str]:
    """Load content with fallback chain.

    Demonstrates or_else for error recovery:
    primary -> backup -> default
    """
    return load_from_primary(primary).or_else(lambda _: load_from_backup(backup)).or_else(lambda _: load_default())


def load_with_fallback_logging(primary: str, backup: str) -> Result[str, str]:
    """Load with fallback, logging each attempt.

    Demonstrates inspect_err for side effects on error path.
    """
    return (
        load_from_primary(primary)
        .inspect_err(lambda e: print(f"  Primary failed: {e}"))
        .or_else(lambda _: load_from_backup(backup))
        .inspect_err(lambda e: print(f"  Backup failed: {e}"))
        .or_else(lambda _: load_default())
        .tee(lambda _: print("  Using default config"))
    )


# =============================================================================
# Partial Recovery
# =============================================================================


def parse_optional_int(value: str, default: int) -> int:
    """Parse int with default on failure."""
    try:
        return int(value)
    except ValueError:
        return default


def load_config_with_defaults(path: str) -> Result[Config, ChainedError]:
    """Load config with defaults for optional values.

    Required fields fail if missing; optional fields use defaults.
    Uses early return pattern for clean, readable code.
    """
    content_result = read_file(path).context(f"reading config file '{path}'")
    if is_err(content_result):
        return content_result

    content = content_result.unwrap()

    # Required fields - fail if missing
    db_url_result = parse_config_value(content, "database_url").context("parsing required 'database_url'")
    if is_err(db_url_result):
        return db_url_result

    api_key_result = parse_config_value(content, "api_key").context("parsing required 'api_key'")
    if is_err(api_key_result):
        return api_key_result

    # Optional fields - use defaults on failure
    max_connections = (
        parse_config_value(content, "max_connections").map(lambda v: parse_optional_int(v, 10)).unwrap_or(10)
    )
    debug = parse_config_value(content, "debug").map(lambda v: v.lower() == "true").unwrap_or(False)

    return Ok(
        Config(
            database_url=db_url_result.unwrap(),
            api_key=api_key_result.unwrap(),
            max_connections=max_connections,
            debug=debug,
        )
    )


# =============================================================================
# ChainedError Inspection
# =============================================================================


def inspect_error_chain(error: ChainedError | str) -> None:
    """Demonstrate ChainedError inspection methods."""
    print(f"  Full error: {error}")
    if isinstance(error, ChainedError):
        print(f"  Root cause: {error.root_cause()}")
        print("  Error chain:")
        for i, err in enumerate(error.chain()):
            print(f"    {i}: {err}")
    else:
        print("  (Simple error, no chain)")


# =============================================================================
# Before/After Comparison
# =============================================================================

# BEFORE: Exception-based configuration loading
# ----------------------------------------------
#
# class ConfigError(Exception):
#     pass
#
# class FileReadError(ConfigError):
#     pass
#
# class ParseError(ConfigError):
#     pass
#
# def load_config_old(path: str) -> Config:
#     try:
#         content = Path(path).read_text()
#     except FileNotFoundError:
#         raise FileReadError(f"Config file not found: {path}")
#     except PermissionError:
#         raise FileReadError(f"Cannot read config file: {path}")
#
#     try:
#         db_url = parse_key(content, "database_url")
#     except KeyError:
#         raise ParseError("Missing database_url in config")
#
#     try:
#         api_key = parse_key(content, "api_key")
#     except KeyError:
#         raise ParseError("Missing api_key in config")
#
#     try:
#         max_conn = int(parse_key(content, "max_connections"))
#     except (KeyError, ValueError) as e:
#         raise ParseError(f"Invalid max_connections: {e}")
#
#     return Config(database_url=db_url, api_key=api_key, max_connections=max_conn)
#
# # Using it:
# try:
#     config = load_config_old("/etc/app/config.ini")
# except FileReadError as e:
#     print(f"Could not read config: {e}")
#     config = get_default_config()
# except ParseError as e:
#     print(f"Invalid config: {e}")
#     sys.exit(1)
# except Exception as e:
#     print(f"Unexpected error: {e}")
#     sys.exit(1)
#
# Problems:
# 1. Error context is lost - you know WHAT failed, not WHERE in the chain
# 2. Recovery requires try/except which is verbose
# 3. Easy to miss exceptions - nothing enforces handling
# 4. Nested try/except becomes hard to follow
#
# AFTER: Result-based approach (shown above)
# ------------------------------------------
# 1. ChainedError preserves full context: "parsing api_key: reading config: file not found"
# 2. Recovery with or_else is explicit and composable
# 3. Type system helps ensure errors are handled
# 4. Flat chain of operations instead of nested try/except


# =============================================================================
# Demo
# =============================================================================


def main() -> None:
    print("=" * 60)
    print("Error Handling Patterns with Result")
    print("=" * 60)

    # Context Chaining
    print("\n--- Context Chaining ---\n")

    print("1. Loading config from non-existent file:")
    result = load_config("/nonexistent/config.ini")
    match result:
        case Ok(config):
            print(f"  Loaded: {config}")
        case Err(error):
            inspect_error_chain(error)

    # Create a test config file
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False, encoding="utf-8") as f:
        f.write("database_url=postgres://localhost/db\n")
        f.write("api_key=secret-key-123\n")
        f.write("max_connections=invalid\n")  # This will fail
        config_path = f.name

    print("\n2. Loading config with invalid integer:")
    result = load_config(config_path)
    match result:
        case Ok(config):
            print(f"  Loaded: {config}")
        case Err(error):
            inspect_error_chain(error)

    # Fix the config
    with open(config_path, "w", encoding="utf-8") as f:
        f.write("database_url=postgres://localhost/db\n")
        f.write("api_key=secret-key-123\n")
        f.write("max_connections=20\n")

    print("\n3. Loading valid config:")
    result = load_config(config_path)
    match result:
        case Ok(config):
            print(f"  Loaded: database_url={config.database_url}")
            print(f"          api_key={config.api_key[:10]}...")
            print(f"          max_connections={config.max_connections}")
        case Err(error):
            print(f"  Error: {error}")

    # Error Recovery
    print("\n--- Error Recovery with or_else ---\n")

    print("4. Load with fallback chain (all missing):")
    result = load_with_fallback_logging("/nonexistent/primary.ini", "/nonexistent/backup.ini")
    match result:
        case Ok(content):
            print(f"  Content loaded ({len(content)} chars)")
        case Err(error):
            print(f"  Error: {error}")

    print("\n5. Load with fallback chain (primary exists):")
    result = load_with_fallback(config_path, "/nonexistent/backup.ini")
    match result:
        case Ok(content):
            print(f"  Loaded from primary ({len(content)} chars)")
        case Err(error):
            print(f"  Error: {error}")

    # Config with defaults
    print("\n--- Partial Recovery (Defaults) ---\n")

    # Create minimal config
    with open(config_path, "w", encoding="utf-8") as f:
        f.write("database_url=postgres://localhost/db\n")
        f.write("api_key=secret-key-123\n")
        # max_connections and debug are missing - will use defaults

    print("6. Load config with optional fields defaulted:")
    result = load_config_with_defaults(config_path)
    match result:
        case Ok(config):
            print(f"  database_url: {config.database_url}")
            print(f"  api_key: {config.api_key[:10]}...")
            print(f"  max_connections: {config.max_connections} (default)")
            print(f"  debug: {config.debug} (default)")
        case Err(error):
            print(f"  Error: {error}")

    # Cleanup
    Path(config_path).unlink()


if __name__ == "__main__":
    main()
