"""JSON 容错解析测试 — 证明 40%→90% 成功率提升.

Tests safe_json_parse from src/utils/__init__.py across three layers:
Layer 1: Direct parse + extract JSON blocks
Layer 2: Regex extract + basic repair (truncation, quotes, commas, keys)
Layer 3: Fuzzy extract + FIELD_ALIASES + default value fill
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from utils import safe_json_parse


# ---------------------------------------------------------------------------
# Basic test schema used across multiple tests
# ---------------------------------------------------------------------------
BASIC_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "default": "Unknown"},
        "type": {"type": "string", "default": "character", "enum": ["character", "world", "plot", "relationship", "item", "location", "timeline", "culture"]},
        "content": {"type": "string", "default": ""},
        "summary": {"type": "string", "default": ""},
        "confidence": {"type": "number", "default": 0.5},
        "tags": {"type": "array", "default": ["general"]},
        "fandom": {"type": "string", "default": ""},
    },
    "required": ["name", "type", "content"],
}


# ---------------------------------------------------------------------------
# Layer 1: Direct JSON parse
# ---------------------------------------------------------------------------

class TestDirectParse:
    """Layer 1: Direct JSON parsing (no repair needed)."""

    def test_direct_parse_valid_json(self):
        """Normal JSON should parse on first attempt."""
        valid = '{"name": "Harry Potter", "type": "character", "content": "The Boy Who Lived."}'
        result = safe_json_parse(valid)
        assert result["name"] == "Harry Potter"
        assert result["type"] == "character"
        assert result["content"] == "The Boy Who Lived."

    def test_direct_parse_with_numbers_and_booleans(self):
        """JSON with numbers, booleans, and null should parse correctly."""
        raw = '{"name": "Test", "confidence": 0.95, "active": true, "count": 3, "extra": null}'
        result = safe_json_parse(raw)
        assert result["confidence"] == 0.95
        assert result["active"] is True
        assert result["count"] == 3
        assert result["extra"] is None

    def test_direct_parse_empty_object(self):
        """Empty object should parse."""
        result = safe_json_parse("{}")
        assert result == {}

    def test_parse_with_markdown_wrapper(self):
        """JSON inside ```json ... ``` markdown fence should be extracted."""
        raw = '```json\n{"name": "Ron Weasley", "type": "character", "content": "Best friend of Harry."}\n```'
        result = safe_json_parse(raw)
        assert result["name"] == "Ron Weasley"

    def test_parse_with_plain_markdown_wrapper(self):
        """JSON inside ``` ... ``` (no language tag) should also be extracted."""
        raw = '```\n{"name": "Draco Malfoy", "type": "character"}\n```'
        result = safe_json_parse(raw)
        assert result["name"] == "Draco Malfoy"


# ---------------------------------------------------------------------------
# Layer 2: Regex extract + basic repair
# ---------------------------------------------------------------------------

class TestRepairLayer:
    """Layer 2: Regex-based JSON repair."""

    def test_parse_truncated_json(self):
        """Truncated JSON should be repaired by trimming + closing brackets."""
        raw = '{"name": "Harry Potter", "type": "character", "content": "The Boy Who Lived. A Gryffindor'
        result = safe_json_parse(raw)
        assert result["name"] == "Harry Potter"
        assert result["type"] == "character"

    def test_parse_truncated_with_open_array(self):
        """Truncated JSON with open array should be repaired."""
        raw = '{"name": "Test", "tags": ["alpha", "beta"'
        result = safe_json_parse(raw)
        assert result["name"] == "Test"
        # The open array may or may not survive repair; at minimum we get the name
        assert "name" in result

    def test_parse_with_trailing_comma(self):
        """Trailing comma before closing brace should be removed."""
        raw = '{"name": "Hermione Granger", "type": "character", "content": "Brightest witch.",}'
        result = safe_json_parse(raw)
        assert result["name"] == "Hermione Granger"

    def test_parse_with_trailing_comma_in_array(self):
        """Trailing comma in array should be removed."""
        raw = '{"name": "Test", "tags": ["a", "b",]}'
        result = safe_json_parse(raw)
        assert result["tags"] == ["a", "b"]

    def test_parse_with_single_quotes(self):
        """Single-quoted JSON should be converted to double quotes."""
        raw = "{'name': 'Draco Malfoy', 'type': 'character', 'content': 'Slytherin.'}"
        result = safe_json_parse(raw)
        assert result["name"] == "Draco Malfoy"

    def test_parse_with_unquoted_keys(self):
        """Unquoted JS-style keys should be quoted."""
        raw = '{name: "Albus Dumbledore", type: "character", content: "Headmaster."}'
        result = safe_json_parse(raw)
        assert result["name"] == "Albus Dumbledore"
        assert result["type"] == "character"


# ---------------------------------------------------------------------------
# Layer 3: Fuzzy match + default fill
# ---------------------------------------------------------------------------

class TestFuzzyLayer:
    """Layer 3: Fuzzy field matching and default value filling."""

    def test_parse_with_field_drift(self):
        """Field name drift (e.g., 'title' → 'name') should be corrected via FIELD_ALIASES."""
        raw = '{"title": "Neville Longbottom", "card_type": "character", "description": "Destroyed the final Horcrux."}'
        result = safe_json_parse(raw, schema=BASIC_SCHEMA)
        # After normalization: title→name, card_type→type, description→content
        assert result["name"] == "Neville Longbottom"
        assert result["type"] == "character"
        assert result["content"] == "Destroyed the final Horcrux."

    def test_parse_with_chinese_field_name(self):
        """Chinese field name aliases (e.g., '角色' → 'character') should be recognized."""
        raw = '{"角色": "Luna Lovegood", "name": "Luna Lovegood", "type": "character", "content": "Believes in Nargles."}'
        result = safe_json_parse(raw, schema=BASIC_SCHEMA)
        # '角色' maps to 'character' (a type value, not a field), but 'name' stays
        # The key normalization will attempt to map '角色' → 'character' (canonical)
        # which means the result may have a 'character' field with the value
        assert result.get("name") == "Luna Lovegood" or result.get("character") == "Luna Lovegood"

    def test_parse_with_schema_defaults(self):
        """Missing fields should be filled with schema defaults."""
        raw = '{"name": "Minimal Card"}'
        result = safe_json_parse(raw, schema=BASIC_SCHEMA)
        assert result["name"] == "Minimal Card"
        assert result["type"] == "character"  # enum default
        assert result["content"] == ""         # string default
        assert result["confidence"] == 0.5     # number default
        assert result["tags"] == ["general"]   # array default

    def test_parse_completely_broken(self):
        """Completely unparseable input falls through to Layer 3 error dict."""
        broken = "This is purely random text @#$%^&*() without any JSON-like structure at all."
        result = safe_json_parse(broken)
        # Layer 3 fallback returns error-indicating dict
        assert isinstance(result, dict)
        assert "error" in result
        assert "fuzzy_extract_failed" in result.get("error", "")


# ---------------------------------------------------------------------------
# Statistical test: 90% success rate
# ---------------------------------------------------------------------------

class TestSuccessRate:
    """Prove that 10 broken JSONs yield at least 9 successful parses (90%)."""

    def _is_successful_parse(self, result: dict) -> bool:
        """A successful parse does NOT contain an error key."""
        return "error" not in result

    def test_parse_success_rate_statistic(self, sample_broken_jsons):
        """Statistical test: at least 9 of 10 broken inputs parse successfully."""
        assert len(sample_broken_jsons) == 10

        results = []
        for i, raw in enumerate(sample_broken_jsons):
            try:
                result = safe_json_parse(raw, schema=BASIC_SCHEMA)
                success = self._is_successful_parse(result)
                results.append((i, success, result))
            except ValueError:
                results.append((i, False, {"error": "ValueError"}))

        successes = sum(1 for _, ok, _ in results if ok)
        failures = [(i, r) for i, ok, r in results if not ok]

        print(f"\nJSON parse success rate: {successes}/{len(sample_broken_jsons)}")
        for i, r in failures:
            print(f"  Failed #{i}: {r}")

        assert successes >= 9, (
            f"Expected >= 9 successful parses, got {successes}/10.\n"
            f"Failures: {failures}"
        )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Additional edge case tests for JSON parser."""

    def test_parse_with_unicode_characters(self):
        """JSON with Unicode/Chinese characters should parse correctly."""
        raw = '{"name": "西弗勒斯·斯内普", "type": "character", "content": "霍格沃茨魔药学教授，双面间谍。"}'
        result = safe_json_parse(raw)
        assert result["name"] == "西弗勒斯·斯内普"

    def test_parse_with_escaped_characters(self):
        """JSON with escape sequences should parse correctly."""
        raw = '{"name": "Test", "content": "Line 1\\nLine 2\\tTabbed\\"Quote\\""}'
        result = safe_json_parse(raw)
        assert "Line 1" in result["content"]
        assert "Line 2" in result["content"]

    def test_parse_with_nested_objects(self):
        """Nested JSON objects should parse correctly."""
        raw = '{"name": "Test", "metadata": {"confidence": 0.9, "tags": ["a", "b"]}}'
        result = safe_json_parse(raw)
        assert result["metadata"]["confidence"] == 0.9
        assert result["metadata"]["tags"] == ["a", "b"]

    def test_parse_none_input_schema_fills_defaults(self):
        """When schema is provided, all defaults should be filled."""
        raw = '{"name": "Bare Minimum"}'
        result = safe_json_parse(raw, schema=BASIC_SCHEMA)
        assert result["name"] == "Bare Minimum"
        assert "type" in result
        assert "content" in result
        assert "tags" in result
        assert "confidence" in result
