# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Data Processing with Result.

This example demonstrates how to use Result types for robust data processing:
- CSV parsing with line-number error tracking
- JSON parsing with safe field extraction
- Data transformation pipelines
- Batch operations with sequence_results and traverse_results

Run with: uv run python examples/data_processing.py
"""

import csv
import json
from dataclasses import dataclass
from io import StringIO
from typing import Any

from unwrappy import Err, Ok, Option, Result, from_nullable, is_err, traverse_results

# =============================================================================
# Domain Models
# =============================================================================


@dataclass
class Product:
    sku: str
    name: str
    price: float
    quantity: int


@dataclass
class ParseError:
    """Error with location information for debugging."""

    message: str
    line: int | None = None
    column: str | None = None

    def __str__(self) -> str:
        location = []
        if self.line is not None:
            location.append(f"line {self.line}")
        if self.column is not None:
            location.append(f"column '{self.column}'")
        if location:
            return f"{', '.join(location)}: {self.message}"
        return self.message


# =============================================================================
# CSV Parsing
# =============================================================================


def parse_float(value: str, column: str, line: int) -> Result[float, ParseError]:
    """Parse a string as float with detailed error context."""
    try:
        return Ok(float(value))
    except ValueError:
        return Err(ParseError(f"invalid number '{value}'", line=line, column=column))


def parse_int(value: str, column: str, line: int) -> Result[int, ParseError]:
    """Parse a string as int with detailed error context."""
    try:
        return Ok(int(value))
    except ValueError:
        return Err(ParseError(f"invalid integer '{value}'", line=line, column=column))


def parse_csv_row(row: dict[str, str], line_num: int) -> Result[Product, ParseError]:
    """Parse a single CSV row into a Product.

    Uses early return pattern for clean, readable validation.
    """
    # Validate required fields exist
    sku = row.get("sku", "").strip()
    name = row.get("name", "").strip()
    price_str = row.get("price", "").strip()
    qty_str = row.get("quantity", "").strip()

    if not sku:
        return Err(ParseError("missing required field", line=line_num, column="sku"))
    if not name:
        return Err(ParseError("missing required field", line=line_num, column="name"))

    # Parse numeric fields
    price_result = parse_float(price_str, "price", line_num)
    if is_err(price_result):
        return price_result

    qty_result = parse_int(qty_str, "quantity", line_num)
    if is_err(qty_result):
        return qty_result

    price = price_result.unwrap()
    quantity = qty_result.unwrap()

    # Validate business rules
    if price < 0:
        return Err(ParseError("price cannot be negative", line=line_num, column="price"))

    return Ok(Product(sku=sku, name=name, price=price, quantity=quantity))


def parse_csv_data(csv_content: str) -> Result[list[Product], ParseError]:
    """Parse CSV content into a list of Products.

    Uses traverse_results to parse all rows and fail on first error.
    """
    reader = csv.DictReader(StringIO(csv_content))

    # Create list of (row, line_number) pairs
    # Line numbers start at 2 (header is line 1)
    rows_with_lines = [(row, i + 2) for i, row in enumerate(reader)]

    # traverse_results: applies function to each item, collects Results
    return traverse_results(rows_with_lines, lambda item: parse_csv_row(item[0], item[1]))


# =============================================================================
# JSON Parsing
# =============================================================================


def safe_json_parse(json_str: str) -> Result[dict[str, Any], ParseError]:
    """Safely parse JSON string."""
    try:
        data = json.loads(json_str)
        if not isinstance(data, dict):
            return Err(ParseError("expected JSON object"))
        return Ok(data)
    except json.JSONDecodeError as e:
        return Err(ParseError(f"invalid JSON: {e.msg}", line=e.lineno))


def get_json_field(data: dict[str, Any], field: str) -> Option[Any]:
    """Get a field from a JSON object, returning Option."""
    return from_nullable(data.get(field))


def get_nested_field(data: dict[str, Any], *path: str) -> Option[Any]:
    """Get a nested field from JSON using a path.

    Example: get_nested_field(data, "user", "address", "city")
    """
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return from_nullable(None)
        current = current.get(key)
        if current is None:
            return from_nullable(None)
    return from_nullable(current)


def parse_api_response(json_str: str) -> Result[list[Product], ParseError]:
    """Parse a JSON API response containing products.

    Expected format:
    {
        "status": "success",
        "data": {
            "products": [
                {"sku": "...", "name": "...", "price": 9.99, "quantity": 10},
                ...
            ]
        }
    }
    """
    return (
        safe_json_parse(json_str)
        .and_then(
            lambda data: get_nested_field(data, "data", "products").ok_or(ParseError("missing 'data.products' field"))
        )
        .and_then(
            lambda products: (
                Err(ParseError("'products' must be an array"))
                if not isinstance(products, list)
                else traverse_results(
                    list(enumerate(products)),
                    lambda item: _parse_product_json(item[1], item[0]),
                )
            )
        )
    )


def _parse_product_json(data: Any, index: int) -> Result[Product, ParseError]:
    """Parse a single product from JSON."""
    if not isinstance(data, dict):
        return Err(ParseError(f"product at index {index} must be an object"))

    sku = data.get("sku")
    name = data.get("name")
    price = data.get("price")
    quantity = data.get("quantity")

    if not isinstance(sku, str) or not sku:
        return Err(ParseError(f"product at index {index}: invalid or missing 'sku'"))
    if not isinstance(name, str) or not name:
        return Err(ParseError(f"product at index {index}: invalid or missing 'name'"))
    if not isinstance(price, (int, float)):
        return Err(ParseError(f"product at index {index}: invalid or missing 'price'"))
    if not isinstance(quantity, int):
        return Err(ParseError(f"product at index {index}: invalid or missing 'quantity'"))

    return Ok(Product(sku=sku, name=name, price=float(price), quantity=quantity))


# =============================================================================
# Data Transformation Pipeline
# =============================================================================


def validate_product(product: Product) -> Result[Product, str]:
    """Validate a product meets business rules."""
    if product.price < 0:
        return Err(f"Product {product.sku}: negative price")
    if product.quantity < 0:
        return Err(f"Product {product.sku}: negative quantity")
    if len(product.name) > 100:
        return Err(f"Product {product.sku}: name too long")
    return Ok(product)


def apply_discount(product: Product, discount_pct: float) -> Product:
    """Apply a discount to a product's price."""
    new_price = round(product.price * (1 - discount_pct / 100), 2)
    return Product(sku=product.sku, name=product.name, price=new_price, quantity=product.quantity)


def filter_in_stock(product: Product) -> bool:
    """Check if product is in stock."""
    return product.quantity > 0


def transform_products(products: list[Product], discount_pct: float) -> Result[list[Product], str]:
    """Pipeline: validate -> filter in-stock -> apply discount.

    Demonstrates chaining operations on a list of products.
    """
    # First, validate all products
    validated = traverse_results(products, validate_product)

    # Then filter and transform
    return validated.map(lambda prods: [apply_discount(p, discount_pct) for p in prods if filter_in_stock(p)])


# =============================================================================
# Demo
# =============================================================================


def main() -> None:
    print("=" * 60)
    print("Data Processing with Result")
    print("=" * 60)

    # CSV Parsing Demo
    print("\n--- CSV Parsing ---\n")

    valid_csv = """sku,name,price,quantity
SKU001,Widget,9.99,100
SKU002,Gadget,19.99,50
SKU003,Gizmo,29.99,25"""

    print("1. Parsing valid CSV:")
    result = parse_csv_data(valid_csv)
    match result:
        case Ok(products):
            for p in products:
                print(f"   {p.sku}: {p.name} - ${p.price} ({p.quantity} in stock)")
        case Err(error):
            print(f"   Error: {error}")

    invalid_csv = """sku,name,price,quantity
SKU001,Widget,9.99,100
SKU002,Gadget,not-a-number,50
SKU003,Gizmo,29.99,25"""

    print("\n2. Parsing CSV with invalid data:")
    result = parse_csv_data(invalid_csv)
    match result:
        case Ok(products):
            print(f"   Parsed {len(products)} products")
        case Err(error):
            print(f"   Error: {error}")

    # JSON Parsing Demo
    print("\n--- JSON Parsing ---\n")

    valid_json = """{
        "status": "success",
        "data": {
            "products": [
                {"sku": "SKU001", "name": "Widget", "price": 9.99, "quantity": 100},
                {"sku": "SKU002", "name": "Gadget", "price": 19.99, "quantity": 50}
            ]
        }
    }"""

    print("3. Parsing valid API response:")
    result = parse_api_response(valid_json)
    match result:
        case Ok(products):
            for p in products:
                print(f"   {p.sku}: {p.name} - ${p.price}")
        case Err(error):
            print(f"   Error: {error}")

    invalid_json = """{
        "status": "success",
        "data": {
            "products": [
                {"sku": "SKU001", "name": "Widget", "price": "free", "quantity": 100}
            ]
        }
    }"""

    print("\n4. Parsing JSON with invalid product:")
    result = parse_api_response(invalid_json)
    match result:
        case Ok(products):
            print(f"   Parsed {len(products)} products")
        case Err(error):
            print(f"   Error: {error}")

    # Nested field extraction with Option
    print("\n--- Optional Field Extraction ---\n")

    data = {"user": {"name": "Alice", "address": {"city": "NYC"}}}

    print("5. Extracting nested fields:")
    city = get_nested_field(data, "user", "address", "city")
    print(f"   City: {city.unwrap_or('unknown')}")

    country = get_nested_field(data, "user", "address", "country")
    print(f"   Country: {country.unwrap_or('unknown')}")

    # Transformation Pipeline Demo
    print("\n--- Transformation Pipeline ---\n")

    products = [
        Product("SKU001", "Widget", 100.0, 10),
        Product("SKU002", "Gadget", 200.0, 0),  # Out of stock
        Product("SKU003", "Gizmo", 150.0, 5),
    ]

    print("6. Transform pipeline (validate -> filter in-stock -> 10% discount):")
    result = transform_products(products, discount_pct=10)
    match result:
        case Ok(transformed):
            for p in transformed:
                print(f"   {p.sku}: {p.name} - ${p.price} ({p.quantity} in stock)")
        case Err(error):
            print(f"   Error: {error}")


if __name__ == "__main__":
    main()
