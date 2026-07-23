"""数据模型层 - SettingCard, SettingPackage, ResearchPlan 等核心数据结构."""

from .setting_card import SettingCard, CardType, SourceType
from .setting_package import SettingPackage
from .research_plan import ResearchPlan, ResearchTopic
from .evaluation import EvaluationResult, EvalDimension

__all__ = [
    "SettingCard",
    "CardType",
    "SourceType",
    "SettingPackage",
    "ResearchPlan",
    "ResearchTopic",
    "EvaluationResult",
    "EvalDimension",
]
