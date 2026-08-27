from __future__ import annotations

from typing import Any


class SchemaValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_json_schema(value: Any, schema: dict[str, Any]) -> None:
    """Validate the JSON Schema subset used by this project without dependencies."""
    errors: list[str] = []
    _validate(value, schema, "$", errors)
    if errors:
        raise SchemaValidationError(errors)


def _validate(
    value: Any, schema: dict[str, Any], path: str, errors: list[str]
) -> None:
    if "anyOf" in schema:
        for candidate in schema["anyOf"]:
            candidate_errors: list[str] = []
            _validate(value, candidate, path, candidate_errors)
            if not candidate_errors:
                return
        errors.append(f"{path}: does not match any allowed schema")
        return

    expected = schema.get("type")
    type_valid = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }
    if expected and not type_valid.get(expected, True):
        errors.append(f"{path}: expected {expected}")
        return

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value is not in enum")
    if isinstance(value, str) and len(value) < int(schema.get("minLength", 0)):
        errors.append(f"{path}: string is too short")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: value is below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: value is above maximum")

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}.{key}: required property is missing")
        properties = schema.get("properties", {})
        for key, item in value.items():
            if key in properties:
                _validate(item, properties[key], f"{path}.{key}", errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}.{key}: additional property is not allowed")

    if isinstance(value, list):
        if len(value) < int(schema.get("minItems", 0)):
            errors.append(f"{path}: array has too few items")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                _validate(item, item_schema, f"{path}[{index}]", errors)
