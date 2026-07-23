"""工作流图构建 — LangGraph 真实实现 + SimpleWorkflowRunner fallback.

状态流转:
    STEP1 → STEP2 → STEP3 → STEP4 → STEP5 → STEP6 → END
                ↑                 ↑  ↑
                └─── REJECT>30% ──┘  │
                └─── FLAG/REJECT ────┘
"""

from typing import Literal, Optional

from .state import WorkflowState, WorkflowStep, StepStatus, StepResult
from .steps import (
    step1_clarify,
    step2_plan,
    step3_research,
    step4_extract,
    step5_check,
    step6_assemble,
)


def build_workflow_graph():
    """构建工作流执行器.

    优先加载 LangGraph，不可用时降级为 SimpleWorkflowRunner.
    """
    try:
        import langgraph
        return LangGraphWorkflowRunner()
    except ImportError:
        return SimpleWorkflowRunner()


def route_after_check(state: WorkflowState) -> Literal["step6", "step4", "step2"]:
    """Step5 → 决策路由."""
    step5 = state.step_results.get(WorkflowStep.STEP5_CHECK)
    if step5 is None or step5.status != StepStatus.COMPLETED:
        return "step4"

    total = state.card_generation_stats.get("total", 0)
    rejected = len(state.rejected_cards)
    flagged = len(state.flagged_cards)

    if total > 0 and rejected / total > 0.3:
        return "step2"      # >30% reject → 重新规划
    if flagged > 0 or rejected > 0:
        return "step4"       # 有需要修复的 → 重新提取
    return "step6"           # 全部通过 → 组装


class LangGraphWorkflowRunner:
    """基于 LangGraph StateGraph 的工作流执行器."""

    def __init__(self):
        self.graph = self._build()

    def _build(self):
        from langgraph.graph import StateGraph, END

        workflow = StateGraph(WorkflowState)

        workflow.add_node("step1", step1_clarify)
        workflow.add_node("step2", step2_plan)
        workflow.add_node("step3", step3_research)
        workflow.add_node("step4", step4_extract)
        workflow.add_node("step5", step5_check)
        workflow.add_node("step6", step6_assemble)

        workflow.set_entry_point("step1")
        workflow.add_edge("step1", "step2")
        workflow.add_edge("step2", "step3")
        workflow.add_edge("step3", "step4")
        workflow.add_edge("step4", "step5")
        workflow.add_conditional_edges(
            "step5",
            route_after_check,
            {"step6": "step6", "step4": "step4", "step2": "step2"},
        )
        workflow.add_edge("step6", END)

        return workflow.compile()

    async def run(self, state: WorkflowState) -> WorkflowState:
        """执行 LangGraph 工作流."""
        state.workflow_status = "running"
        final_state = await self.graph.ainvoke(state)
        if final_state.workflow_status != "failed":
            final_state.workflow_status = "completed"
        return final_state


class SimpleWorkflowRunner:
    """简化顺序执行器 (LangGraph 不可用时的 fallback)."""

    def __init__(self):
        self.steps = {
            WorkflowStep.STEP1_CLARIFY: step1_clarify,
            WorkflowStep.STEP2_PLAN: step2_plan,
            WorkflowStep.STEP3_RESEARCH: step3_research,
            WorkflowStep.STEP4_EXTRACT: step4_extract,
            WorkflowStep.STEP5_CHECK: step5_check,
            WorkflowStep.STEP6_ASSEMBLE: step6_assemble,
        }

    async def run(self, state: WorkflowState) -> WorkflowState:
        """顺序执行 6 步, 支持条件回退."""
        state.workflow_status = "running"
        step_order = list(WorkflowStep)

        i = 0
        while i < len(step_order):
            step = step_order[i]
            state.advance_to(step)

            if state.workflow_status == "failed":
                break

            step_fn = self.steps.get(step)
            if step_fn is None:
                state.step_results[step].status = StepStatus.SKIPPED
                i += 1
                continue

            result = await step_fn(state)

            # Step5 后的条件路由
            if step == WorkflowStep.STEP5_CHECK and result.status == StepStatus.COMPLETED:
                route = route_after_check(state)
                if route == "step4":
                    i = step_order.index(WorkflowStep.STEP4_EXTRACT)
                    continue
                elif route == "step2":
                    i = step_order.index(WorkflowStep.STEP2_PLAN)
                    continue

            # 失败回退
            if result.status == StepStatus.FAILED:
                fallback = self._get_fallback(step)
                if fallback and state.can_enter_step(fallback):
                    i = step_order.index(fallback)
                    continue
                else:
                    state.workflow_status = "failed"
                    state.abort_reason = f"步骤 {step.value} 失败且无法回退: {result.errors}"
                    break

            i += 1

        if state.workflow_status != "failed":
            state.workflow_status = "completed"
        return state

    @staticmethod
    def _get_fallback(step: WorkflowStep) -> Optional[WorkflowStep]:
        return {
            WorkflowStep.STEP5_CHECK: WorkflowStep.STEP4_EXTRACT,
            WorkflowStep.STEP4_EXTRACT: WorkflowStep.STEP3_RESEARCH,
            WorkflowStep.STEP3_RESEARCH: WorkflowStep.STEP2_PLAN,
        }.get(step)
