"""Shared fixtures for all tests."""

import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from models.setting_card import SettingCard, CardType, SourceType, CardMetadata
from models.setting_package import SettingPackage
from rag.knowledge_base import KnowledgeBase, KnowledgeChunk, KnowledgeLayer


@pytest.fixture
def sample_cards():
    """Return 3 sample SettingCards (Harry Potter characters)."""
    card1 = SettingCard(
        type=CardType.CHARACTER,
        name="Harry Potter",
        content="The Boy Who Lived, protagonist of the series. A Gryffindor student at Hogwarts School of Witchcraft and Wizardry. Known for his lightning-bolt scar and his defeat of Lord Voldemort during the Battle of Hogwarts.",
        summary="The Boy Who Lived",
        source=SourceType.CANON,
        metadata={
            "confidence": 0.95,
            "tags": ["Gryffindor", "protagonist", "student"],
            "fandom": "Harry Potter",
        },
    )
    card2 = SettingCard(
        type=CardType.CHARACTER,
        name="Hermione Granger",
        content="Brightest witch of her age. A Gryffindor student and one of Harry's best friends. Known for her intelligence, logical thinking, and extensive knowledge of magic.",
        summary="Brightest witch of her age",
        source=SourceType.CANON,
        metadata={
            "confidence": 0.95,
            "tags": ["Gryffindor", "muggle-born", "student"],
            "fandom": "Harry Potter",
        },
    )
    card3 = SettingCard(
        type=CardType.CHARACTER,
        name="Severus Snape",
        content="Hogwarts Potions Master and Head of Slytherin House. A complex character who served as a double agent during both wizarding wars. Deeply in love with Lily Potter. Skilled in Occlumency and Dark Arts.",
        summary="Potions Master and double agent",
        source=SourceType.CANON,
        metadata={
            "confidence": 0.90,
            "tags": ["Slytherin", "professor", "spy"],
            "fandom": "Harry Potter",
        },
    )
    return [card1, card2, card3]


@pytest.fixture
def sample_package(sample_cards):
    """Return a SettingPackage containing sample cards."""
    pkg = SettingPackage(
        title="Harry Potter Setting Package",
        description="A comprehensive setting collection for Harry Potter fan fiction",
        fandom="Harry Potter",
    )
    for card in sample_cards:
        pkg.add_card(card)
    return pkg


@pytest.fixture
def mock_llm_client():
    """Return a fake LLMClient that never calls any API."""
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock()
    client.config = MagicMock()
    client.config.provider = "anthropic"
    client.config.model = "claude-sonnet-5"
    client.config.default_temperature = 0.3
    client.config.default_max_tokens = 2048
    client.config.default_top_p = 0.95
    client.generate = AsyncMock(return_value='{"result": "ok"}')
    client.generate_structured = AsyncMock(return_value='{"result": "ok"}')
    client.stats = {"calls": 0, "provider": "anthropic", "model": "claude-sonnet-5"}
    return client


@pytest.fixture
def sample_broken_jsons():
    """Return 10 broken JSON strings simulating LLM output failures.

    Includes: truncation, markdown wrappers, trailing commas, single quotes,
    unquoted keys, field drift, and mixed issues.
    At least 9 of these should be recoverable by safe_json_parse.
    """
    return [
        # 1. JSON truncation (LLM output cut off mid-string)
        '{"name": "Harry Potter", "type": "character", "content": "The Boy Who Lived. A Gryffindor student at Hogwarts',
        # 2. Markdown code fence wrap
        '```json\n{"name": "Ron Weasley", "type": "character", "content": "Harry\'s loyal best friend from the Weasley family."}\n```',
        # 3. Trailing comma before closing brace
        '{"name": "Hermione Granger", "type": "character", "content": "Brightest witch of her age.",}',
        # 4. Single-quoted JSON
        "{'name': 'Draco Malfoy', 'type': 'character', 'content': 'Slytherin rival and antagonist.'}",
        # 5. Unquoted keys (JavaScript-style object literal)
        '{name: "Albus Dumbledore", type: "character", content: "Headmaster of Hogwarts and powerful wizard."}',
        # 6. Field drift: "title" instead of "name", "description" instead of "content"
        '{"title": "Neville Longbottom", "card_type": "character", "description": "Gryffindor student who destroyed the final Horcrux."}',
        # 7. Valid JSON with extra whitespace and newlines
        '{\n  "name": "Luna Lovegood",\n  "type": "character",\n  "content": "Ravenclaw student who believes in Nargles.",\n  "confidence": 0.85\n}',
        # 8. Trailing comma in array
        '{"name": "Ginny Weasley", "type": "character", "content": "Youngest Weasley sibling.", "tags": ["Gryffindor", "Quidditch",]}',
        # 9. Truncated JSON (missing closing brace)
        '{"name": "Sirius Black", "type": "character", "content": "Harry\'s godfather who escaped from Azkaban.',
        # 10. Nested truncation (metadata object incomplete)
        '{"name": "Remus Lupin", "type": "character", "content": "Werewolf and former DADA professor.", "metadata": {"confidence": 0.8, "tags": ["Marauder", "Order of the Phoenix"',
    ]


@pytest.fixture
def kb_with_seed_data():
    """Return a KnowledgeBase pre-populated with seed data."""
    kb = KnowledgeBase()
    chunks = [
        KnowledgeChunk(
            layer=KnowledgeLayer.L3_PRIVATE,
            content="Harry Potter is a Gryffindor student at Hogwarts. He is 17 years old during the Battle of Hogwarts in 1998.",
            source_title="HP Canon - Characters",
            keywords=["Harry", "Potter", "Gryffindor", "age"],
            project_id="hp-project",
        ),
        KnowledgeChunk(
            layer=KnowledgeLayer.L3_PRIVATE,
            content="Severus Snape died on May 2, 1998 during the Battle of Hogwarts. He was 38 years old at time of death.",
            source_title="HP Canon - Timeline",
            keywords=["Snape", "death", "timeline", "Battle of Hogwarts"],
            project_id="hp-project",
        ),
        KnowledgeChunk(
            layer=KnowledgeLayer.L3_PRIVATE,
            content="The Battle of Hogwarts took place on May 2, 1998. Voldemort was defeated by Harry Potter.",
            source_title="HP Canon - Events",
            keywords=["Battle", "Hogwarts", "Voldemort", "defeat"],
            project_id="hp-project",
        ),
        KnowledgeChunk(
            layer=KnowledgeLayer.L1_GENERAL,
            content="Hogwarts School of Witchcraft and Wizardry is a British boarding school for magical education founded in the 10th century.",
            source_title="Wizarding World Encyclopedia",
            keywords=["Hogwarts", "school", "education", "history"],
        ),
        KnowledgeChunk(
            layer=KnowledgeLayer.L1_GENERAL,
            content="The four Hogwarts houses are Gryffindor, Hufflepuff, Ravenclaw, and Slytherin. Each was founded by one of the four founders.",
            source_title="Wizarding World Encyclopedia",
            keywords=["Hogwarts", "houses", "founders"],
        ),
    ]
    kb.add_chunks(chunks)
    return kb
