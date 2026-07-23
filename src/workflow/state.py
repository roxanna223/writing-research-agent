"""工作流状态定义 — 6步状态机的核心状态结构."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class WorkflowStep(str, Enum):
    """6个步骤."""
    STEP1_CLARIFY = "step1_clarify"        # 任务澄清
    STEP2_PLAN = "step2_plan"              # 研究规划
    STEP3_RESEARCH = "step3_research"      # 资料检索
    STEP4_EXTRACT = "step4_extract"        # 设定提取
    STEP5_CHECK = "step5_check"            # 一致性审核
    STEP6_ASSEMBLE = "step6_assemble"      # 设定包组装


class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """单个步骤的执行结果."""
    step: WorkflowStep
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output: Any = None                # 步骤输出 (类型随步骤不同)
    errors: list[str] = field(default_factory=list)
    retries: int = 0
    max_retries: int = 3

    def to_dict(self) -> dict:
        return {
            "step": self.step.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "errors": self.errors,
            "retries": self.retries,
        }


@dataclass
class WorkflowState:
    """6步工作流的全局状态.

    在各步骤间流转, 每个步骤读取上游输出、写入自己的产出.
    """

    # 会话标识
    session_id: str = ""
    project_id: str = ""

    # 用户输入
    user_input: str = ""                       # 用户原始输入
    clarified_requirement: str = ""            # Step1 输出: 澄清后需求
    project_type: str = ""                     # fanfic | original
    fandom: str = ""                           # 原作名称

    # 各步骤结果
    step_results: dict[WorkflowStep, StepResult] = field(default_factory=dict)

    # Step1 输出
    clarification_questions: list[dict] = field(default_factory=list)
    clarify_ready: bool = False                # 澄清是否完成

    # Step2 输出
    research_plan: Optional[Any] = None        # ResearchPlan

    # Step3 输出
    research_notes: list[dict] = field(default_factory=list)

    # Step4 输出
    generated_cards: list[dict] = field(default_factory=list)
    card_generation_stats: dict = field(default_factory=dict)

    # Step5 输出
    approved_cards: list[dict] = field(default_factory=list)
    flagged_cards: list[dict] = field(default_factory=list)
    rejected_cards: list[dict] = field(default_factory=list)
    conflict_reports: list[dict] = field(default_factory=list)
    consistency_score: float = 0.0

    # Step6 输出
    setting_package: Optional[Any] = None      # SettingPackage
    export_paths: dict[str, str] = field(default_factory=dict)

    # 流程控制
    current_step: WorkflowStep = WorkflowStep.STEP1_CLARIFY
    step_entry_count: dict[WorkflowStep, int] = field(default_factory=dict)
    max_step_reentry: int = 3                  # 每步最多重入次数
    workflow_status: str = "pending"           # pending | running | completed | failed
    abort_reason: str = ""

    def __post_init__(self):
        """初始化步骤结果."""
        for step in WorkflowStep:
            if step not in self.step_results:
                self.step_results[step] = StepResult(step=step)
            if step not in self.step_entry_count:
                self.step_entry_count[step] = 0

    def can_enter_step(self, step: WorkflowStep) -> bool:
        """检查是否可进入某步骤 (防死循环)."""
        count = self.step_entry_count.get(step, 0)
        return count < self.max_step_reentry

    def advance_to(self, step: WorkflowStep) -> None:
        """前进到指定步骤."""
        if not self.can_enter_step(step):
            self.workflow_status = "failed"
            self.abort_reason = f"步骤 {step.value} 重入次数超限 ({self.max_step_reentry})"
            return
        self.current_step = step
        self.step_entry_count[step] = self.step_entry_count.get(step, 0) + 1

    def goto_previous(self) -> Optional[WorkflowStep]:
        """回退到上一步."""
        step_order = list(WorkflowStep)
        current_idx = step_order.index(self.current_step)
        if current_idx > 0:
            prev_step = step_order[current_idx - 1]
            self.advance_to(prev_step)
            return prev_step
        return None

    @property
    def progress(self) -> dict:
        """获取工作流进度."""
        step_order = list(WorkflowStep)
        completed = sum(
            1 for s in step_order
            if self.step_results.get(s, StepResult(step=s)).status == StepStatus.COMPLETED
        )
        return {
            "current_step": self.current_step.value,
            "completed_steps": completed,
            "total_steps": len(step_order),
            "percentage": round(completed / len(step_order) * 100, 1),
            "workflow_status": self.workflow_status,
        }
