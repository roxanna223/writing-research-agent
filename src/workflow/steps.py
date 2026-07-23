"""6步工作流 — 每步的具体实现."""

import asyncio
import json
from datetime import datetime
from typing import Any

from .state import WorkflowState, WorkflowStep, StepStatus, StepResult


async def step1_clarify(state: WorkflowState) -> StepResult:
    """Step1: 任务澄清.

    调用 Planner (Task Clarify) Skill 分析用户输入,
    必要时交互式追问直到需求清晰.
    """
    result = state.step_results[WorkflowStep.STEP1_CLARIFY]
    result.status = StepStatus.IN_PROGRESS
    result.started_at = datetime.now()

    try:
        # 实际实现: 调用 Planner Prompt → LLM → 解析 JSON
        # 此处为骨架实现
        user_input = state.user_input

        # 模拟澄清逻辑
        state.clarified_requirement = (
            f"用户需求: {user_input}\n"
            f"项目类型: {state.project_type or 'fanfic'}\n"
            f"原作: {state.fandom or '待确认'}\n"
        )

        result.status = StepStatus.COMPLETED
        result.output = {
            "clarified_requirement": state.clarified_requirement,
            "project_type": state.project_type,
            "fandom": state.fandom,
        }

    except Exception as e:
        result.status = StepStatus.FAILED
        result.errors.append(str(e))

    result.completed_at = datetime.now()
    return result


async def step2_plan(state: WorkflowState) -> StepResult:
    """Step2: 研究规划.

    调用 Planner (Research Plan) Skill → 生成 ResearchPlan.
    """
    result = state.step_results[WorkflowStep.STEP2_PLAN]
    result.status = StepStatus.IN_PROGRESS
    result.started_at = datetime.now()

    try:
        # 调用 Planner Research Plan Prompt
        # research_plan = await llm_generate(PLANNER_RESEARCH_PLAN, ...)
        # state.research_plan = ResearchPlan(**json_output)

        result.status = StepStatus.COMPLETED
        result.output = {
            "topics_count": len(state.research_plan.topics) if state.research_plan else 0,
        }

    except Exception as e:
        result.status = StepStatus.FAILED
        result.errors.append(str(e))

    result.completed_at = datetime.now()
    return result


async def step3_research(state: WorkflowState) -> StepResult:
    """Step3: 资料检索.

    调用 Researcher Skill + 分层RAG, 按 ResearchPlan 逐话题检索.
    """
    result = state.step_results[WorkflowStep.STEP3_RESEARCH]
    result.status = StepStatus.IN_PROGRESS
    result.started_at = datetime.now()

    try:
        # 对每个研究话题执行检索
        # for topic in state.research_plan.topics:
        #     queries = await llm_generate(RESEARCHER_QUERY, topic=topic)
        #     for q in queries:
        #         retrieved = rag.retrieve(q)
        #         notes.append(summarize(retrieved))

        result.status = StepStatus.COMPLETED
        result.output = {
            "notes_count": len(state.research_notes),
        }

    except Exception as e:
        result.status = StepStatus.FAILED
        result.errors.append(str(e))

    result.completed_at = datetime.now()
    return result


async def step4_extract(state: WorkflowState) -> StepResult:
    """Step4: 设定提取.

    调用 Extractor Skill, 从研究笔记中逐张生成 SettingCard.
    每张卡独立生成 → 小 JSON → 防截断.
    """
    result = state.step_results[WorkflowStep.STEP4_EXTRACT]
    result.status = StepStatus.IN_PROGRESS
    result.started_at = datetime.now()

    try:
        cards = []
        # 逐卡生成
        # for note in state.research_notes:
        #     card_json = await llm_generate(EXTRACTOR_CARD, notes=note)
        #     card = safe_json_parse(card_json)  # 容错解析
        #     cards.append(card)

        state.generated_cards = cards
        state.card_generation_stats = {
            "total": len(cards),
            "by_type": {},  # 按 type 统计
        }

        result.status = StepStatus.COMPLETED
        result.output = {"cards_generated": len(cards)}

    except Exception as e:
        result.status = StepStatus.FAILED
        result.errors.append(str(e))

    result.completed_at = datetime.now()
    return result


async def step5_check(state: WorkflowState) -> StepResult:
    """Step5: 一致性审核.

    调用 Checker Skill + ConflictDetector,
    对每张卡执行五维检查, 分成 PASS/FLAG/REJECT.
    """
    result = state.step_results[WorkflowStep.STEP5_CHECK]
    result.status = StepStatus.IN_PROGRESS
    result.started_at = datetime.now()

    try:
        approved, flagged, rejected = [], [], []
        conflicts = []

        # 逐卡审核
        # for card in state.generated_cards:
        #     check_result = await llm_generate(CHECKER_VALIDATE, card=card)
        #     if check_result.status == "PASS":
        #         approved.append(card)
        #     elif check_result.status == "FLAG":
        #         flagged.append(card)
        #     else:
        #         rejected.append(card)

        # 冲突检测
        # detector = ConflictDetector(kb)
        # for card in approved + flagged:
        #     conflicts.extend(detector.detect_conflicts(card, approved))

        state.approved_cards = approved
        state.flagged_cards = flagged
        state.rejected_cards = rejected
        state.conflict_reports = conflicts
        state.consistency_score = _calc_consistency(approved, flagged, rejected)

        result.status = StepStatus.COMPLETED
        result.output = {
            "approved": len(approved),
            "flagged": len(flagged),
            "rejected": len(rejected),
            "conflicts": len(conflicts),
            "consistency_score": state.consistency_score,
        }

    except Exception as e:
        result.status = StepStatus.FAILED
        result.errors.append(str(e))

    result.completed_at = datetime.now()
    return result


async def step6_assemble(state: WorkflowState) -> StepResult:
    """Step6: 设定包组装 (确定性逻辑, 不调用 LLM).

    用 AssemblyEngine 将已审核卡片组装为 SettingPackage.
    此步骤是纯代码逻辑 → 生成稳定率 100%.
    """
    result = state.step_results[WorkflowStep.STEP6_ASSEMBLE]
    result.status = StepStatus.IN_PROGRESS
    result.started_at = datetime.now()

    try:
        # 确定性组装 (不调用 LLM)
        # from src.models.setting_package import SettingPackage, AssemblyEngine
        # engine = AssemblyEngine(config=assembly_config)
        # package = engine.assemble(state.approved_cards + state.flagged_cards)

        # state.setting_package = package
        # state.export_paths = engine.export(package, formats=["json", "markdown"])

        result.status = StepStatus.COMPLETED
        result.output = {
            "package_id": "pkg-example",
            "card_count": len(state.approved_cards) + len(state.flagged_cards),
            "assembly_version": "1.0.0",
            "stability": "100%",  # 确定性组装 → 100% 稳定
        }

    except Exception as e:
        result.status = StepStatus.FAILED
        result.errors.append(str(e))

    result.completed_at = datetime.now()
    return result


def _calc_consistency(
    approved: list, flagged: list, rejected: list
) -> float:
    """计算一致性分数."""
    total = len(approved) + len(flagged) + len(rejected)
    if total == 0:
        return 1.0
    consistent = len(approved) + len(flagged)  # flagged 也算基本一致
    return round(consistent / total, 2)
