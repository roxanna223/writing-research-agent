"""确定性组装测试 — 证明 50%→100% 稳定率.

Tests SettingPackage from src/models/setting_package.py.
Assembly is deterministic (no LLM involved), so same input always
produces identical output.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from models.setting_card import SettingCard, CardType, SourceType
from models.setting_package import SettingPackage, CategoryIndex, ExportFormat


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_card(name: str, card_type: CardType = CardType.CHARACTER,
              content: str = "Test content for this card.", **kwargs) -> SettingCard:
    """Create a SettingCard with minimal boilerplate."""
    defaults = {
        "type": card_type,
        "name": name,
        "content": content,
        "source": SourceType.CANON,
        "metadata": {"confidence": 0.9, "tags": ["test"]},
    }
    defaults.update(kwargs)
    return SettingCard(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAddCard:
    """Tests for SettingPackage.add_card()."""

    def test_add_card_increments_count(self):
        """Adding cards should increment card_count."""
        pkg = SettingPackage(title="Test Package")
        assert pkg.card_count == 0

        card = make_card("Card 1")
        pkg.add_card(card)
        assert pkg.card_count == 1

        pkg.add_card(make_card("Card 2"))
        assert pkg.card_count == 2

    def test_add_card_stores_in_cards_dict(self):
        """Added cards should be stored in the cards dict by ID."""
        pkg = SettingPackage(title="Test Package")
        card = make_card("Harry")
        pkg.add_card(card)
        assert card.id in pkg.cards
        assert pkg.cards[card.id] is card

    def test_category_index_auto_update(self):
        """Category index should auto-update when cards are added."""
        pkg = SettingPackage(title="Test Package")

        char_card = make_card("Harry", CardType.CHARACTER)
        world_card = make_card("Hogwarts", CardType.WORLD, "A magical school.")
        location_card = make_card("Diagon Alley", CardType.LOCATION, "Shopping street.")

        pkg.add_card(char_card)
        pkg.add_card(world_card)
        pkg.add_card(location_card)

        idx = pkg.category_index
        assert char_card.id in idx.characters
        assert world_card.id in idx.world_settings
        assert location_card.id in idx.locations

    def test_category_index_total(self):
        """Category index total_cards should match actual card count."""
        pkg = SettingPackage(title="Test Package")
        for i in range(5):
            pkg.add_card(make_card(f"Card {i}", CardType.CHARACTER))
        assert pkg.category_index.total_cards == 5

    def test_get_cards_by_type(self):
        """get_cards_by_type should filter correctly."""
        pkg = SettingPackage(title="Test Package")
        pkg.add_card(make_card("Harry", CardType.CHARACTER))
        pkg.add_card(make_card("Ron", CardType.CHARACTER))
        pkg.add_card(make_card("Hogwarts", CardType.WORLD, "A magical school of Witchcraft and Wizardry."))

        chars = pkg.get_cards_by_type(CardType.CHARACTER)
        worlds = pkg.get_cards_by_type(CardType.WORLD)

        assert len(chars) == 2
        assert len(worlds) == 1
        assert chars[0].name in ("Harry", "Ron")
        assert worlds[0].name == "Hogwarts"


class TestRemoveCard:
    """Tests for SettingPackage.remove_card()."""

    def test_remove_card_updates_indices(self):
        """Removing a card should update the category index."""
        pkg = SettingPackage(title="Test Package")
        card = make_card("Harry", CardType.CHARACTER)
        pkg.add_card(card)
        assert pkg.card_count == 1
        assert card.id in pkg.category_index.characters

        removed = pkg.remove_card(card.id)
        assert removed is card
        assert pkg.card_count == 0
        assert card.id not in pkg.category_index.characters

    def test_remove_nonexistent_card(self):
        """Removing a non-existent card should return None."""
        pkg = SettingPackage(title="Test Package")
        result = pkg.remove_card("nonexistent-id")
        assert result is None

    def test_remove_then_rebuild_indices(self):
        """After removal, indices should be fully rebuilt (no stale refs)."""
        pkg = SettingPackage(title="Test Package")
        card1 = make_card("Card1", CardType.CHARACTER)
        card2 = make_card("Card2", CardType.CHARACTER)
        pkg.add_card(card1)
        pkg.add_card(card2)
        assert pkg.category_index.total_cards == 2

        pkg.remove_card(card1.id)
        assert pkg.category_index.total_cards == 1
        assert card1.id not in pkg.category_index.characters
        assert card2.id in pkg.category_index.characters


class TestDeterministicAssembly:
    """Prove that assembly is 100% deterministic."""

    def _build_identical_packages(self):
        """Build two packages with identical cards in identical order."""
        cards_data = [
            ("Harry Potter", CardType.CHARACTER, "The Boy Who Lived."),
            ("Hogwarts", CardType.WORLD, "School of Witchcraft and Wizardry."),
            ("Gryffindor Sword", CardType.ITEM, "Goblin-made silver sword."),
        ]
        cards = [make_card(name, ctype, content) for name, ctype, content in cards_data]
        return cards

    def test_assembly_deterministic_same_input(self):
        """Same input x 10 runs should produce identical output."""
        cards = self._build_identical_packages()

        results = []
        for _ in range(10):
            pkg = SettingPackage(title="Deterministic Test", description="Same input each time")
            for card in cards:
                # Use the same card objects — card IDs are deterministic
                # because they are generated once at creation time.
                pkg.add_card(card)
            results.append(pkg.to_markdown())

        # All 10 outputs must be identical
        first = results[0]
        for i, result in enumerate(results[1:], 2):
            assert result == first, f"Run {i} produced different output"

    def test_assembly_deterministic_to_json(self):
        """JSON export should be deterministic for structural fields (timestamps and IDs vary)."""
        cards = self._build_identical_packages()

        results = []
        for _ in range(4):
            pkg = SettingPackage(title="Deterministic Test")
            for card in cards:
                pkg.add_card(card)
            exported = pkg.to_json_export()
            # Remove volatile fields which vary by run
            exported.pop("created_at", None)
            exported.pop("id", None)
            for c in exported["cards"]:
                c.get("metadata", {}).pop("created_at", None)
                c.get("metadata", {}).pop("updated_at", None)
            results.append(json.dumps(exported, sort_keys=True))

        first = results[0]
        for i, result in enumerate(results[1:], 2):
            assert result == first, f"Run {i} JSON differs"


class TestExport:
    """Tests for SettingPackage export formats."""

    def test_to_markdown_output(self, sample_package):
        """Markdown export should contain expected content."""
        md = sample_package.to_markdown()

        # Title
        assert "# Harry Potter Setting Package" in md

        # Card names as H2 headings
        assert "## Harry Potter" in md
        assert "## Hermione Granger" in md
        assert "## Severus Snape" in md

        # Card content
        assert "The Boy Who Lived" in md
        assert "Brightest witch" in md
        assert "Potions Master" in md

        # Metadata
        assert "**类型**" in md
        assert "**来源**" in md

    def test_to_markdown_includes_card_count(self):
        """Markdown export should include card count."""
        pkg = SettingPackage(title="Test")
        pkg.add_card(make_card("C1"))
        pkg.add_card(make_card("C2"))
        md = pkg.to_markdown()
        assert "卡片总数: 2" in md

    def test_to_markdown_includes_conflicts(self):
        """Markdown export should include conflict reports."""
        from models.setting_package import ConflictReport

        pkg = SettingPackage(title="Test")
        pkg.conflict_reports = [
            ConflictReport(
                card_id_a="card-1",
                card_id_b="card-2",
                conflict_type="timeline",
                description="Timeline mismatch: card 1 says 1997, card 2 says 1998",
                severity="high",
            )
        ]
        pkg.add_card(make_card("C1"))
        pkg.add_card(make_card("C2"))

        md = pkg.to_markdown()
        assert "冲突报告" in md
        assert "Timeline mismatch" in md

    def test_to_json_export(self, sample_package):
        """JSON export should be parseable and contain expected data."""
        exported = sample_package.to_json_export()

        assert exported["title"] == "Harry Potter Setting Package"
        assert exported["fandom"] == "Harry Potter"
        assert exported["card_count"] == 3
        assert len(exported["cards"]) == 3

        # Each card should have expected fields
        card_names = [c["name"] for c in exported["cards"]]
        assert "Harry Potter" in card_names
        assert "Hermione Granger" in card_names
        assert "Severus Snape" in card_names

        # created_at should be ISO format string
        assert isinstance(exported["created_at"], str)
        assert "T" in exported["created_at"]

    def test_to_json_export_is_reparseable(self):
        """Exported JSON should be re-parseable as valid JSON."""
        pkg = SettingPackage(title="Test Reparse")
        pkg.add_card(make_card("Card A"))
        exported = pkg.to_json_export()

        # Should be serializable
        json_str = json.dumps(exported)
        reparsed = json.loads(json_str)
        assert reparsed["title"] == "Test Reparse"
        assert len(reparsed["cards"]) == 1


class TestEmptyPackage:
    """Tests for edge cases with empty packages."""

    def test_empty_package(self):
        """Empty package should have expected defaults."""
        pkg = SettingPackage(title="Empty")
        assert pkg.card_count == 0
        assert pkg.category_index.total_cards == 0
        assert pkg.cards == {}
        assert pkg.checker_passed is False
        assert pkg.conflict_reports == []

    def test_empty_package_markdown(self):
        """Empty package markdown should not crash."""
        pkg = SettingPackage(title="Empty")
        md = pkg.to_markdown()
        assert "# Empty" in md

    def test_empty_package_json(self):
        """Empty package JSON export should not crash."""
        pkg = SettingPackage(title="Empty")
        exported = pkg.to_json_export()
        assert exported["card_count"] == 0
        assert exported["cards"] == []

    def test_empty_package_get_conflict_free(self):
        """get_conflict_free_cards on empty package should return empty list."""
        pkg = SettingPackage(title="Empty")
        result = pkg.get_conflict_free_cards()
        assert result == []


class TestConflictingCards:
    """Tests for conflict-related operations."""

    def test_get_conflict_free_cards(self):
        """get_conflict_free_cards should exclude conflicted cards."""
        from models.setting_package import ConflictReport

        pkg = SettingPackage(title="Test Conflicts")
        card1 = make_card("C1")
        card2 = make_card("C2")
        card3 = make_card("C3")
        pkg.add_card(card1)
        pkg.add_card(card2)
        pkg.add_card(card3)

        # Mark card1 and card2 as conflicting
        pkg.conflict_reports = [
            ConflictReport(
                card_id_a=card1.id,
                card_id_b=card2.id,
                conflict_type="direct",
                description="Conflict between C1 and C2",
            )
        ]

        conflict_free = pkg.get_conflict_free_cards()
        conflict_free_ids = {c.id for c in conflict_free}

        assert card3.id in conflict_free_ids
        assert card1.id not in conflict_free_ids
        assert card2.id not in conflict_free_ids
