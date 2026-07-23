"""Skill Prompt 模板测试.

Tests all 7 skills from src/skills/ and their registration.
Verifies temperature settings, output_schema presence, message building,
and step-to-skill mapping.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

# Import skills to trigger registration
import skills  # noqa: F401
from skills.base import SkillPrompt, SkillRegistry, SkillType


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------

class TestRegistration:
    """Tests for SkillRegistry and skill registration."""

    def test_all_skills_registered(self):
        """All 7 skills should be registered in SkillRegistry."""
        all_skills = SkillRegistry.list_all()
        expected = {
            "planner_task_clarify",
            "planner_research_plan",
            "storm_brainstorm",
            "clear_clarify",
            "researcher_query",
            "extractor_card",
            "checker_validate",
        }
        registered = set(all_skills)
        assert registered == expected, (
            f"Missing: {expected - registered}, Extra: {registered - expected}"
        )

    def test_skill_registry_singleton(self):
        """SkillRegistry should be a singleton."""
        r1 = SkillRegistry()
        r2 = SkillRegistry()
        assert r1 is r2

    def test_skill_registry_get(self):
        """get() should return correct skill or None."""
        assert SkillRegistry.get("planner_task_clarify") is not None
        assert SkillRegistry.get("nonexistent_skill") is None

    def test_skill_registry_get_by_step(self):
        """Step-to-skill mapping should be correct."""
        # Step 1: planner_task_clarify + clear_clarify
        step1 = SkillRegistry.get_by_step(1)
        step1_names = {s.name for s in step1}
        assert "planner_task_clarify" in step1_names
        assert "clear_clarify" in step1_names
        assert len(step1) == 2

        # Step 2: planner_research_plan
        step2 = SkillRegistry.get_by_step(2)
        assert len(step2) == 1
        assert step2[0].name == "planner_research_plan"

        # Step 3: researcher_query
        step3 = SkillRegistry.get_by_step(3)
        assert len(step3) == 1
        assert step3[0].name == "researcher_query"

        # Step 4: extractor_card + storm_brainstorm
        step4 = SkillRegistry.get_by_step(4)
        step4_names = {s.name for s in step4}
        assert "extractor_card" in step4_names
        assert "storm_brainstorm" in step4_names
        assert len(step4) == 2

        # Step 5: checker_validate
        step5 = SkillRegistry.get_by_step(5)
        assert len(step5) == 1
        assert step5[0].name == "checker_validate"

        # Step 6: no LLM skills (Formatter is deterministic)
        step6 = SkillRegistry.get_by_step(6)
        assert len(step6) == 0


# ---------------------------------------------------------------------------
# Temperature tests
# ---------------------------------------------------------------------------

class TestTemperatures:
    """Verify correct temperature settings for each skill."""

    def test_storm_temperature_high(self):
        """Storm (brainstorm) should have temperature 0.9 for creative divergence."""
        storm = SkillRegistry.get("storm_brainstorm")
        assert storm is not None
        assert storm.temperature == 0.9, (
            f"Storm temperature should be 0.9, got {storm.temperature}"
        )

    def test_checker_temperature_zero(self):
        """Checker should have temperature 0.0 for absolute determinism."""
        checker = SkillRegistry.get("checker_validate")
        assert checker is not None
        assert checker.temperature == 0.0, (
            f"Checker temperature should be 0.0, got {checker.temperature}"
        )

    def test_researcher_temperature_low(self):
        """Researcher should have temperature 0.1 for precision."""
        researcher = SkillRegistry.get("researcher_query")
        assert researcher is not None
        assert researcher.temperature == 0.1

    def test_extractor_temperature_low(self):
        """Extractor should have temperature 0.1 for precision extraction."""
        extractor = SkillRegistry.get("extractor_card")
        assert extractor is not None
        assert extractor.temperature == 0.1

    def test_planner_temperature_moderate(self):
        """Planner skills should have temperature 0.3."""
        p1 = SkillRegistry.get("planner_task_clarify")
        p2 = SkillRegistry.get("planner_research_plan")
        assert p1.temperature == 0.3
        assert p2.temperature == 0.3

    def test_clear_temperature_moderate(self):
        """Clear should have temperature 0.3."""
        clear = SkillRegistry.get("clear_clarify")
        assert clear is not None
        assert clear.temperature == 0.3


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestSchemas:
    """Verify output_schema presence on skills that need it."""

    def test_planner_prompts_have_schema(self):
        """Both Planner skills should have output_schema defined."""
        p1 = SkillRegistry.get("planner_task_clarify")
        p2 = SkillRegistry.get("planner_research_plan")

        assert p1 is not None
        assert p2 is not None
        assert p1.output_schema is not None, "planner_task_clarify missing output_schema"
        assert p2.output_schema is not None, "planner_research_plan missing output_schema"

        # Verify schema structure
        assert p1.output_schema["type"] == "object"
        assert "required" in p1.output_schema

        assert p2.output_schema["type"] == "object"
        assert "required" in p2.output_schema
        assert "topics" in p2.output_schema["properties"]

    def test_checker_has_schema(self):
        """Checker should have output_schema defined."""
        checker = SkillRegistry.get("checker_validate")
        assert checker is not None
        assert checker.output_schema is not None

        # Verify key fields
        props = checker.output_schema["properties"]
        assert "card_id" in props
        assert "status" in props
        assert "issues" in props
        assert "summary" in props

    def test_skills_with_output_schema(self):
        """Skills that produce structured JSON should have output_schema."""
        skills_with_schema = {
            "planner_task_clarify",
            "planner_research_plan",
            "clear_clarify",
            "researcher_query",
            "checker_validate",
        }
        for name in skills_with_schema:
            skill = SkillRegistry.get(name)
            assert skill is not None, f"Skill '{name}' not found"
            assert skill.output_schema is not None, (
                f"Skill '{name}' should have output_schema"
            )
            assert skill.output_schema.get("type") == "object"


# ---------------------------------------------------------------------------
# Message building tests
# ---------------------------------------------------------------------------

class TestMessageBuilding:
    """Verify that each skill can build messages correctly."""

    def test_each_skill_builds_messages(self):
        """Every skill should be able to build_messages with template variables."""
        test_context = {
            "user_input": "Write a Harry Potter fan fiction",
            "clarified_requirement": "HP post-war story",
            "project_type": "fanfic",
            "fandom": "Harry Potter",
            "additional_info": "Focus on Snape",
            "requirement": "HP story",
            "card_count": "3",
            "pending_issues": "None",
            "topic_title": "Character backgrounds",
            "topic_description": "Explore main characters",
            "target_layers": "l1_general, l2_technique",
            "keywords": "Harry, Snape",
            "research_notes": "Snape was a double agent...",
            "card_type": "character",
            "private_constraints": "Must align with canon",
            "card_json": '{"name": "Snape", "type": "character"}',
            "existing_cards_context": "No existing cards",
            "existing_direction": "Marauders era",
            "writing_requirement": "HP story",
        }

        for skill_name in SkillRegistry.list_all():
            skill = SkillRegistry.get(skill_name)
            assert skill is not None

            try:
                messages = skill.build_messages(**test_context)
            except KeyError as e:
                # Some skills may need different variable names — that's OK.
                # Try with empty context for those.
                messages = skill.build_messages()

            # Every skill must produce a valid messages list
            assert isinstance(messages, list), f"{skill_name}: messages should be a list"
            assert len(messages) >= 1, f"{skill_name}: messages should not be empty"

            # First message should be "system"
            assert messages[0]["role"] == "system", (
                f"{skill_name}: first message should be system role"
            )
            assert len(messages[0]["content"]) > 0, (
                f"{skill_name}: system prompt should not be empty"
            )

    def test_template_variable_substitution(self):
        """Template variables should be substituted correctly."""
        planner = SkillRegistry.get("planner_task_clarify")
        assert planner is not None

        messages = planner.build_messages(
            user_input="Write a Story",
            fandom="Harry Potter",
        )

        user_msg = messages[-1]["content"]
        assert "Write a Story" in user_msg, "user_input should appear in prompt"


# ---------------------------------------------------------------------------
# Skill type assignments
# ---------------------------------------------------------------------------

class TestSkillTypes:
    """Verify correct SkillType assignment for each skill."""

    def test_skill_type_mapping(self):
        """Each skill should have the correct SkillType."""
        expected_types = {
            "planner_task_clarify": SkillType.PLANNER,
            "planner_research_plan": SkillType.PLANNER,
            "storm_brainstorm": SkillType.STORM,
            "clear_clarify": SkillType.CLEAR,
            "researcher_query": SkillType.RESEARCHER,
            "extractor_card": SkillType.EXTRACTOR,
            "checker_validate": SkillType.CHECKER,
        }

        for name, expected_type in expected_types.items():
            skill = SkillRegistry.get(name)
            assert skill is not None, f"Skill '{name}' not found"
            assert skill.skill_type == expected_type, (
                f"Skill '{name}': expected {expected_type}, got {skill.skill_type}"
            )

    def test_skill_type_enum_values(self):
        """SkillType enum should have all expected values."""
        expected = {"planner", "storm", "clear", "researcher", "extractor", "checker", "formatter"}
        actual = {e.value for e in SkillType}
        assert expected == actual


# ---------------------------------------------------------------------------
# Skill metadata tests
# ---------------------------------------------------------------------------

class TestSkillMetadata:
    """Verify skill metadata (version, format, retry settings)."""

    def test_all_skills_have_version(self):
        """Every skill should have a version string."""
        for name in SkillRegistry.list_all():
            skill = SkillRegistry.get(name)
            assert skill.version, f"Skill '{name}' missing version"
            assert "." in skill.version, f"Skill '{name}' version should be semver-like"

    def test_all_skills_have_max_tokens(self):
        """Every skill should define max_tokens."""
        for name in SkillRegistry.list_all():
            skill = SkillRegistry.get(name)
            assert skill.max_tokens > 0, f"Skill '{name}' max_tokens should be > 0"

    def test_storm_no_retry(self):
        """Storm should have retry_on_failure=False (creative output has no wrong answer)."""
        storm = SkillRegistry.get("storm_brainstorm")
        assert storm is not None
        assert storm.retry_on_failure is False, (
            "Storm should not retry on failure (creative tasks)"
        )

    def test_checker_output_format_json(self):
        """Checker must output JSON format."""
        checker = SkillRegistry.get("checker_validate")
        assert checker is not None
        assert checker.output_format == "json"

    def test_storm_output_format_text(self):
        """Storm should output free text, not JSON."""
        storm = SkillRegistry.get("storm_brainstorm")
        assert storm is not None
        assert storm.output_format == "text"
