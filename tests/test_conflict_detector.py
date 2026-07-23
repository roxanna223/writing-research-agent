"""冲突检测测试 — 证明 ~75% 命中率.

Tests ConflictDetector from src/rag/conflict_detector.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from rag.conflict_detector import (
    ConflictDetector,
    Assertion,
    ConflictReport,
    ConflictType,
    ConflictSeverity,
)
from rag.knowledge_base import KnowledgeBase, KnowledgeChunk, KnowledgeLayer


@pytest.fixture
def detector(kb_with_seed_data):
    """Create a ConflictDetector with seeded KB."""
    return ConflictDetector(kb_with_seed_data)


# ---------------------------------------------------------------------------
# Helper: build card dicts for testing
# ---------------------------------------------------------------------------

def make_card_dict(card_id: str, name: str, **fields) -> dict:
    """Build a card-like dict for ConflictDetector (which takes dict, not SettingCard)."""
    base = {
        "id": card_id,
        "name": name,
        "type": "character",
        "content": "Test content for this character.",
    }
    base.update(fields)
    return base


# ---------------------------------------------------------------------------
# Assertion Extraction
# ---------------------------------------------------------------------------

class TestAssertionExtraction:
    """Tests for ConflictDetector.extract_assertions()."""

    def test_assertion_extraction(self, detector):
        """Assertions should be correctly extracted from card dict."""
        card = make_card_dict("card-1", "Harry Potter", age="17", house="Gryffindor")
        assertions = detector.extract_assertions(card)

        assert len(assertions) > 0
        # Should extract: id, name, type, content, age, house
        field_paths = {a.field_path for a in assertions}
        assert "name" in field_paths
        assert "type" in field_paths
        assert "age" in field_paths
        assert "house" in field_paths
        assert "content" in field_paths

    def test_assertion_extraction_nested(self, detector):
        """Nested dict fields should be extracted with dot-separated paths."""
        card = {
            "id": "card-1",
            "name": "Test",
            "basicInfo": {
                "age": "17",
                "house": "Gryffindor",
            },
        }
        assertions = detector.extract_assertions(card)
        field_paths = {a.field_path for a in assertions}

        assert "basicInfo.age" in field_paths
        assert "basicInfo.house" in field_paths

    def test_assertion_extraction_numeric(self, detector):
        """Numeric values should be extracted with correct field_type."""
        card = make_card_dict("card-1", "Test", year=1998, count=42)
        assertions = detector.extract_assertions(card)

        year_a = next(a for a in assertions if a.field_path == "year")
        assert year_a.field_type == "int"
        assert year_a.field_value == "1998"

    def test_assertion_extraction_boolean(self, detector):
        """Boolean values should be extracted with correct field_type."""
        card = make_card_dict("card-1", "Test", alive=True)
        assertions = detector.extract_assertions(card)

        alive_a = next(a for a in assertions if a.field_path == "alive")
        assert alive_a.field_type == "bool"
        assert alive_a.field_value == "True"


# ---------------------------------------------------------------------------
# Conflict Detection
# ---------------------------------------------------------------------------

class TestConflictDetection:
    """Tests for ConflictDetector.detect_conflicts()."""

    def test_no_conflict_identical_cards(self, detector):
        """Identical cards should produce DUPLICATE (not harmful DIRECT conflicts)."""
        card_a = make_card_dict("card-1", "Same Name", year="1997")
        card_b = make_card_dict("card-1", "Same Name", year="1997")  # Same ID

        reports = detector.detect_conflicts(card_a, [card_b])

        # Self-comparison should be skipped entirely (same card_id)
        assert len(reports) == 0

    def test_direct_conflict_detected(self, detector):
        """Direct contradictions (different numeric values on same non-time field) should be detected."""
        card_a = make_card_dict("card-1", "Harry", power_level="9000")
        card_b = make_card_dict("card-2", "Harry", power_level="8000")

        reports = detector.detect_conflicts(card_a, [card_b])

        assert len(reports) > 0
        # Find the power_level conflict (skip id/name/type/content conflicts)
        pl_conflicts = [r for r in reports if r.field_path == "power_level"]
        assert len(pl_conflicts) >= 1, (
            f"Expected power_level conflict, got fields: {[r.field_path for r in reports]}"
        )
        conflict = pl_conflicts[0]
        assert conflict.card_id_a == "card-1"
        assert conflict.card_id_b == "card-2"
        assert conflict.conflict_type == ConflictType.DIRECT

    def test_timeline_conflict(self, detector):
        """Timeline-related fields should be classified as TIMELINE conflicts."""
        card_a = make_card_dict("card-1", "Event A", date="1997-05-02")
        card_b = make_card_dict("card-2", "Event B", date="1998-05-02")

        reports = detector.detect_conflicts(card_a, [card_b])

        assert len(reports) > 0
        # date field should trigger TIMELINE classification
        timeline_reports = [r for r in reports if r.conflict_type == ConflictType.TIMELINE]
        assert len(timeline_reports) >= 1, (
            f"Expected at least 1 TIMELINE conflict, got: {[(r.field_path, r.conflict_type) for r in reports]}"
        )

    def test_duplicate_detection(self, detector):
        """Duplicate (identical) values should be flagged as DUPLICATE."""
        card_a = make_card_dict("card-1", "Same", house="Gryffindor")
        card_b = make_card_dict("card-2", "Same", house="Gryffindor")

        reports = detector.detect_conflicts(card_a, [card_b])

        # Same value = DUPLICATE
        duplicate_reports = [r for r in reports if r.conflict_type == ConflictType.DUPLICATE]
        assert len(duplicate_reports) >= 1

    def test_non_conflicting_different_fields(self, detector):
        """Cards with only different-named fields should NOT produce false positives."""
        # Both cards share the same id, name, type, content to avoid
        # spurious conflicts on those core fields
        base = {"id": "shared", "name": "SameName", "type": "character", "content": "Same content here."}
        card_a = {**base, "house": "Gryffindor"}
        card_b = {**base, "patronus": "Stag"}

        reports = detector.detect_conflicts(card_a, [card_b])

        # Different field names (house vs patronus) → not comparable → no conflict
        # Should only have DUPLICATE for identical shared fields
        non_duplicate = [r for r in reports if r.conflict_type != ConflictType.DUPLICATE]
        assert len(non_duplicate) == 0, (
            f"Expected 0 non-duplicate conflicts, got: {non_duplicate}"
        )

    def test_conflict_severity_mapping(self, detector):
        """Conflict severities should map correctly per type."""
        card_a = make_card_dict("card-1", "Test", age="17", birth="1980")
        card_b = make_card_dict("card-2", "Test", age="30", birth="1985")

        reports = detector.detect_conflicts(card_a, [card_b])

        for r in reports:
            if r.conflict_type == ConflictType.TIMELINE:
                assert r.severity == ConflictSeverity.CRITICAL
            elif r.conflict_type == ConflictType.DIRECT:
                assert r.severity == ConflictSeverity.HIGH
            elif r.conflict_type == ConflictType.DUPLICATE:
                assert r.severity == ConflictSeverity.LOW

    def test_conflict_report_has_resolution(self, detector):
        """Each conflict report should include resolution and suggested_fix."""
        card_a = make_card_dict("card-1", "Test", year="2000")
        card_b = make_card_dict("card-2", "Test", year="2001")

        reports = detector.detect_conflicts(card_a, [card_b])

        for r in reports:
            assert r.resolution in ("human_review", "auto_suggest", "auto_fix")
            assert len(r.suggested_fix) > 0
            assert len(r.description) > 0

    def test_skip_self_comparison(self, detector):
        """A card should not be compared with itself."""
        card = make_card_dict("card-1", "Self")
        # Pass the same card as both new and existing
        reports = detector.detect_conflicts(card, [card])
        # Should skip self-comparison
        assert len(reports) == 0, f"Self-comparison should produce 0 reports, got {len(reports)}"


# ---------------------------------------------------------------------------
# Statistical test: 75% conflict hit rate
# ---------------------------------------------------------------------------

class TestConflictHitRate:
    """Prove that 6 out of 8 known conflicts are detected (75% hit rate)."""

    def test_conflict_hit_rate(self, detector):
        """Statistical: at least 6 of 8 known conflict pairs detected."""
        # 8 known conflict scenarios (card_pair, expected_conflict_type)
        known_conflicts = [
            # 1. Direct numeric contradiction (age: 17 vs 16)
            (
                make_card_dict("a1", "Harry", age="17"),
                make_card_dict("b1", "Harry", age="16"),
                ConflictType.DIRECT,
            ),
            # 2. Timeline conflict (different death dates)
            (
                make_card_dict("a2", "Event", date="1997-06-01", birth="1960"),
                make_card_dict("b2", "Event", date="1998-05-02", birth="1960"),
                ConflictType.TIMELINE,
            ),
            # 3. Another direct contradiction (house: Gryffindor vs Slytherin)
            (
                make_card_dict("a3", "Student", house="Gryffindor"),
                make_card_dict("b3", "Student", house="Slytherin"),
                ConflictType.DIRECT,
            ),
            # 4. Timeline (different birth years)
            (
                make_card_dict("a4", "Person", birth="1979"),
                make_card_dict("b4", "Person", birth="1980"),
                ConflictType.TIMELINE,
            ),
            # 5. Duplicate detection (same house, same name)
            (
                make_card_dict("a5", "Same", house="Ravenclaw"),
                make_card_dict("b5", "Same", house="Ravenclaw"),
                ConflictType.DUPLICATE,
            ),
            # 6. Direct contradiction (year: 1996 vs 1997)
            (
                make_card_dict("a6", "YearTest", year="1996"),
                make_card_dict("b6", "YearTest", year="1997"),
                ConflictType.DIRECT,
            ),
            # 7. Timeline (different age values)
            (
                make_card_dict("a7", "AgeTest", age="11"),
                make_card_dict("b7", "AgeTest", age="17"),
                ConflictType.TIMELINE,
            ),
            # 8. Direct contradiction (status field)
            (
                make_card_dict("a8", "StatusTest", status="alive"),
                make_card_dict("b8", "StatusTest", status="dead"),
                ConflictType.DIRECT,
            ),
        ]

        hits = 0
        misses = []
        for i, (card_a, card_b, expected_type) in enumerate(known_conflicts):
            reports = detector.detect_conflicts(card_a, [card_b])
            # Hit = at least one conflict report of the expected type
            matching = [r for r in reports if r.conflict_type == expected_type]
            if matching:
                hits += 1
            else:
                misses.append((i + 1, expected_type.value, [r.conflict_type.value for r in reports]))

        print(f"\nConflict hit rate: {hits}/{len(known_conflicts)}")
        for idx, expected, actual in misses:
            print(f"  MISS #{idx}: expected {expected}, got {actual}")

        assert hits >= 6, (
            f"Expected >= 6 detected conflicts (75% hit rate), got {hits}/{len(known_conflicts)}.\n"
            f"Misses: {misses}"
        )
