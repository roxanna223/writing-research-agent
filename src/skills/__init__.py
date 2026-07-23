"""Skill层 — 7个Skill, 8套Prompt模板.

映射关系:
┌──────────────┬──────────┬──────┬──────────────────────────┐
│ Skill         │ 温度     │ 步骤  │ 职责                     │
├──────────────┼──────────┼──────┼──────────────────────────┤
│ Planner       │ 0.3      │ 1,2  │ 任务分解+研究规划        │
│ Storm         │ 0.9      │ 1,4  │ 创意发散+设定脑暴        │
│ Clear         │ 0.3      │ 1    │ 需求澄清+追问            │
│ Researcher    │ 0.1      │ 3    │ 资料检索查询生成         │
│ Extractor     │ 0.1      │ 4    │ 结构化设定提取           │
│ Checker       │ 0.0      │ 5    │ 一致性校验+冲突检测      │
│ Formatter     │ -        │ 6    │ 确定性组装(不调用LLM)    │
└──────────────┴──────────┴──────┴──────────────────────────┘
"""

from .base import SkillPrompt, SkillRegistry
from .planner import PLANNER_TASK_CLARIFY, PLANNER_RESEARCH_PLAN
from .storm import STORM_BRAINSTORM
from .clear import CLEAR_CLARIFY
from .researcher import RESEARCHER_QUERY
from .extractor import EXTRACTOR_CARD
from .checker import CHECKER_VALIDATE

__all__ = [
    "SkillPrompt",
    "SkillRegistry",
    "PLANNER_TASK_CLARIFY",
    "PLANNER_RESEARCH_PLAN",
    "STORM_BRAINSTORM",
    "CLEAR_CLARIFY",
    "RESEARCHER_QUERY",
    "EXTRACTOR_CARD",
    "CHECKER_VALIDATE",
]
