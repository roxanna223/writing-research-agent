"""工作流状态机测试 — 6步状态机.

Tests WorkflowState from src/workflow/state.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from workflow.state import (
    WorkflowState,
    WorkflowStep,
    StepStatus,
    StepResult,
)


# ---------------------------------------------------------------------------
# Initial state tests
# ---------------------------------------------------------------------------

class TestInitialState:
    """Tests for initial WorkflowState."""

    def test_initial_state(self):
        """Fresh WorkflowState should have correct defaults."""
        state = WorkflowState()

        assert state.current_step == WorkflowStep.STEP1_CLARIFY
        assert state.workflow_status == "pending"
        assert state.user_input == ""
        assert state.clarified_requirement == ""
        assert state.generated_cards == []
        assert state.max_step_reentry == 3

    def test_initial_state_has_all_step_results(self):
        """All 6 steps should have an initialized StepResult."""
        state = WorkflowState()

        for step in WorkflowStep:
            assert step in state.step_results
            assert state.step_results[step].step == step
            assert state.step_results[step].status == StepStatus.PENDING

    def test_initial_state_entry_counts(self):
        """All steps should start with entry_count = 0."""
        state = WorkflowState()

        for step in WorkflowStep:
            assert state.step_entry_count[step] == 0

    def test_initial_state_with_session_id(self):
        """State should accept custom session_id."""
        state = WorkflowState(session_id="session-abc", project_id="project-xyz")
        assert state.session_id == "session-abc"
        assert state.project_id == "project-xyz"


# ---------------------------------------------------------------------------
# Step advancement tests
# ---------------------------------------------------------------------------

class TestStepAdvancement:
    """Tests for step transitions."""

    def test_advance_through_steps(self):
        """Sequential advancement through all 6 steps."""
        state = WorkflowState()

        step_order = list(WorkflowStep)
        for i, step in enumerate(step_order):
            state.advance_to(step)
            assert state.current_step == step
            assert state.workflow_status == "pending"  # still running
            # Entry count should increment each time we enter
            assert state.step_entry_count[step] == 1

    def test_advance_skips_intermediate_steps(self):
        """Advancing directly to a later step should work."""
        state = WorkflowState()
        state.advance_to(WorkflowStep.STEP3_RESEARCH)
        assert state.current_step == WorkflowStep.STEP3_RESEARCH

    def test_advance_tracks_entry_count(self):
        """Re-entering the same step should increment entry count."""
        state = WorkflowState()
        state.advance_to(WorkflowStep.STEP2_PLAN)
        assert state.step_entry_count[WorkflowStep.STEP2_PLAN] == 1

        # Go somewhere else and come back
        state.advance_to(WorkflowStep.STEP3_RESEARCH)
        state.advance_to(WorkflowStep.STEP2_PLAN)
        assert state.step_entry_count[WorkflowStep.STEP2_PLAN] == 2


# ---------------------------------------------------------------------------
# Step reversion tests
# ---------------------------------------------------------------------------

class TestStepReversion:
    """Tests for goto_previous()."""

    def test_goto_previous(self):
        """Should move back one step."""
        state = WorkflowState()
        state.advance_to(WorkflowStep.STEP4_EXTRACT)
        assert state.current_step == WorkflowStep.STEP4_EXTRACT

        prev = state.goto_previous()
        assert prev == WorkflowStep.STEP3_RESEARCH
        assert state.current_step == WorkflowStep.STEP3_RESEARCH

    def test_goto_previous_from_first_step(self):
        """Cannot go back from first step — should return None."""
        state = WorkflowState()
        assert state.current_step == WorkflowStep.STEP1_CLARIFY

        prev = state.goto_previous()
        assert prev is None
        assert state.current_step == WorkflowStep.STEP1_CLARIFY

    def test_goto_previous_increments_entry(self):
        """Going back counts as re-entry."""
        state = WorkflowState()
        state.advance_to(WorkflowStep.STEP5_CHECK)
        state.goto_previous()  # back to STEP4
        assert state.current_step == WorkflowStep.STEP4_EXTRACT


# ---------------------------------------------------------------------------
# Re-entry limit tests
# ---------------------------------------------------------------------------

class TestMaxReentry:
    """Tests for step re-entry limits to prevent infinite loops."""

    def test_max_reentry_prevents_loop(self):
        """Exceeding max_step_reentry should set workflow to failed."""
        state = WorkflowState(max_step_reentry=2)

        # Enter step 2 twice (allowed)
        state.advance_to(WorkflowStep.STEP2_PLAN)
        state.advance_to(WorkflowStep.STEP1_CLARIFY)
        state.advance_to(WorkflowStep.STEP2_PLAN)  # entry count = 2
        assert state.workflow_status == "pending"

        # Third entry should trigger limit
        state.advance_to(WorkflowStep.STEP1_CLARIFY)
        state.advance_to(WorkflowStep.STEP2_PLAN)  # entry count would be 3, exceeds 2
        assert state.workflow_status == "failed"
        assert "重入次数超限" in state.abort_reason

    def test_max_reentry_default(self):
        """Default max_step_reentry should be 3."""
        state = WorkflowState()
        assert state.max_step_reentry == 3

    def test_reentry_limit_per_step(self):
        """Each step has its own entry counter."""
        state = WorkflowState(max_step_reentry=1)

        # Enter step 2 once (allowed)
        state.advance_to(WorkflowStep.STEP2_PLAN)
        assert state.workflow_status == "pending"

        # Re-enter step 2 should fail
        state.advance_to(WorkflowStep.STEP1_CLARIFY)
        state.advance_to(WorkflowStep.STEP2_PLAN)
        assert state.workflow_status == "failed"


# ---------------------------------------------------------------------------
# Progress tracking tests
# ---------------------------------------------------------------------------

class TestProgressTracking:
    """Tests for progress tracking."""

    def test_progress_tracking(self):
        """Progress should correctly reflect completed steps."""
        state = WorkflowState()

        # Initially: 0/6
        progress = state.progress
        assert progress["completed_steps"] == 0
        assert progress["total_steps"] == 6
        assert progress["percentage"] == 0.0

        # Mark some steps as completed
        state.step_results[WorkflowStep.STEP1_CLARIFY].status = StepStatus.COMPLETED
        state.step_results[WorkflowStep.STEP2_PLAN].status = StepStatus.COMPLETED

        progress = state.progress
        assert progress["completed_steps"] == 2
        assert progress["percentage"] == pytest.approx(33.3, 0.1)

    def test_progress_includes_current_step(self):
        """Progress should include current step info."""
        state = WorkflowState()
        state.advance_to(WorkflowStep.STEP3_RESEARCH)

        progress = state.progress
        assert progress["current_step"] == "step3_research"
        assert progress["workflow_status"] == "pending"

    def test_progress_with_failed_steps(self):
        """Failed steps should not count as completed."""
        state = WorkflowState()
        state.step_results[WorkflowStep.STEP1_CLARIFY].status = StepStatus.COMPLETED
        state.step_results[WorkflowStep.STEP2_PLAN].status = StepStatus.FAILED

        progress = state.progress
        assert progress["completed_steps"] == 1  # Only step 1


# ---------------------------------------------------------------------------
# StepResult tests
# ---------------------------------------------------------------------------

class TestStepResult:
    """Tests for individual StepResult."""

    def test_step_result_initial(self):
        """New StepResult should have PENDING status."""
        sr = StepResult(step=WorkflowStep.STEP1_CLARIFY)
        assert sr.status == StepStatus.PENDING
        assert sr.retries == 0
        assert sr.errors == []

    def test_step_result_records_timing(self):
        """StepResult should track start and completion times."""
        from datetime import datetime

        sr = StepResult(step=WorkflowStep.STEP4_EXTRACT)
        sr.started_at = datetime(2024, 1, 1, 10, 0, 0)
        sr.completed_at = datetime(2024, 1, 1, 10, 5, 0)

        assert sr.started_at is not None
        assert sr.completed_at is not None
        assert sr.completed_at > sr.started_at

    def test_step_result_to_dict(self):
        """to_dict should serialize correctly."""
        from datetime import datetime

        sr = StepResult(
            step=WorkflowStep.STEP5_CHECK,
            status=StepStatus.COMPLETED,
            started_at=datetime(2024, 6, 15, 12, 0, 0),
            completed_at=datetime(2024, 6, 15, 12, 0, 30),
            errors=["Warning: minor issue"],
            retries=1,
        )

        d = sr.to_dict()
        assert d["step"] == "step5_check"
        assert d["status"] == "completed"
        assert d["started_at"] == "2024-06-15T12:00:00"
        assert d["completed_at"] == "2024-06-15T12:00:30"
        assert len(d["errors"]) == 1
        assert d["retries"] == 1

    def test_step_result_with_output(self):
        """StepResult should store arbitrary output."""
        sr = StepResult(step=WorkflowStep.STEP4_EXTRACT)
        sr.output = [{"name": "Card 1"}, {"name": "Card 2"}]
        assert len(sr.output) == 2


# ---------------------------------------------------------------------------
# Integration: full workflow simulation
# ---------------------------------------------------------------------------

class TestWorkflowSimulation:
    """Simulate a complete workflow run."""

    def test_full_six_step_flow(self):
        """Simulate running through all 6 steps."""
        state = WorkflowState(
            session_id="test-session",
            project_id="hp-fanfic",
            user_input="Write a Harry Potter story about Snape",
        )

        # Step 1: Clarify
        state.advance_to(WorkflowStep.STEP1_CLARIFY)
        state.clarified_requirement = "Post-war HP story about Snape's redemption"
        sr1 = state.step_results[WorkflowStep.STEP1_CLARIFY]
        sr1.status = StepStatus.COMPLETED
        sr1.output = {"project_type": "fanfic", "fandom": "Harry Potter"}

        # Step 2: Plan
        state.advance_to(WorkflowStep.STEP2_PLAN)
        sr2 = state.step_results[WorkflowStep.STEP2_PLAN]
        sr2.status = StepStatus.COMPLETED

        # Step 3: Research
        state.advance_to(WorkflowStep.STEP3_RESEARCH)
        sr3 = state.step_results[WorkflowStep.STEP3_RESEARCH]
        sr3.status = StepStatus.COMPLETED

        # Step 4: Extract
        state.advance_to(WorkflowStep.STEP4_EXTRACT)
        state.generated_cards = [{"name": "Snape", "type": "character"}]
        sr4 = state.step_results[WorkflowStep.STEP4_EXTRACT]
        sr4.status = StepStatus.COMPLETED

        # Step 5: Check
        state.advance_to(WorkflowStep.STEP5_CHECK)
        state.approved_cards = state.generated_cards
        state.consistency_score = 0.95
        sr5 = state.step_results[WorkflowStep.STEP5_CHECK]
        sr5.status = StepStatus.COMPLETED

        # Step 6: Assemble
        state.advance_to(WorkflowStep.STEP6_ASSEMBLE)
        sr6 = state.step_results[WorkflowStep.STEP6_ASSEMBLE]
        sr6.status = StepStatus.COMPLETED

        # Verify final state
        progress = state.progress
        assert progress["completed_steps"] == 6
        assert progress["percentage"] == 100.0
        assert state.clarified_requirement != ""
        assert len(state.generated_cards) == 1
        assert state.consistency_score == 0.95

    def test_workflow_with_revision_cycle(self):
        """Simulate a revision cycle (go back from Step5 to Step4)."""
        state = WorkflowState()

        # Advance to Step 5
        for step in list(WorkflowStep)[:5]:
            state.advance_to(step)

        assert state.current_step == WorkflowStep.STEP5_CHECK

        # Checker finds issues, go back to Step 4
        state.goto_previous()
        assert state.current_step == WorkflowStep.STEP4_EXTRACT

        # Fix and re-advance
        state.advance_to(WorkflowStep.STEP5_CHECK)
        assert state.current_step == WorkflowStep.STEP5_CHECK
