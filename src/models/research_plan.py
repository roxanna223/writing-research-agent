"""研究规划 (ResearchPlan) — 研究计划与话题数据模型."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class TopicPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class KnowledgeLayer(str, Enum):
    """知识层, 对应分层RAG."""
    L1_GENERAL = "l1_general"      # 通用资料
    L2_TECHNIQUE = "l2_technique"  # 写作技法
    L3_PRIVATE = "l3_private"      # 项目私设


class ResearchTopic(BaseModel):
    """单个研究话题."""
    id: str = Field(default_factory=lambda: f"topic-{uuid4().hex[:8]}")
    title: str = Field(description="话题标题, 如 '霍格沃茨城堡结构'")
    description: str = Field(description="话题描述")
    keywords: list[str] = Field(description="检索关键词列表")
    priority: TopicPriority = Field(default=TopicPriority.MEDIUM)
    target_layers: list[KnowledgeLayer] = Field(
        default_factory=lambda: [KnowledgeLayer.L1_GENERAL],
        description="目标知识层, 可跨层检索"
    )
    expected_output: str = Field(
        default="", description="期望的检索结果描述"
    )
    assigned_card_types: list[str] = Field(
        default_factory=list,
        description="期望生成的设定卡类型"
    )


class ResearchPlan(BaseModel):
    """研究计划 — Step2 (研究规划) 的输出.

    由 Planner Skill 生成, 指导 Step3 (资料检索).
    """

    id: str = Field(default_factory=lambda: f"plan-{uuid4().hex[:12]}")
    title: str = Field(description="研究计划标题")
    description: str = Field(description="研究计划总览描述")
    fandom: Optional[str] = Field(default=None, description="目标原作/圈子")

    # 原创写作需求 (项目类型为原创时用)
    project_type: str = Field(default="fanfic", description="fanfic | original")
    genre: Optional[str] = Field(default=None, description="题材: 奇幻/科幻/现实/...")
    era: Optional[str] = Field(default=None, description="时代背景")

    # 话题列表
    topics: list[ResearchTopic] = Field(description="研究话题列表, 按优先级排序")

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now)
    total_topics: int = Field(default=0, description="话题总数")

    def model_post_init(self, __context) -> None:
        self.total_topics = len(self.topics)

    @property
    def high_priority_topics(self) -> list[ResearchTopic]:
        return [t for t in self.topics if t.priority == TopicPriority.HIGH]

    @property
    def topic_count_by_layer(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for t in self.topics:
            for layer in t.target_layers:
                counts[layer.value] = counts.get(layer.value, 0) + 1
        return counts
