"""评估模型 — 6维度评估体系的数据结构."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EvalDimension(str, Enum):
    """6个评估维度."""
    COVERAGE = "coverage"         # 研究维度覆盖率
    ACCURACY = "accuracy"         # 设定准确性
    CONSISTENCY = "consistency"   # 设定一致性
    CREATIVITY = "creativity"     # 创意丰富度
    FORMAT = "format"             # 格式规范性
    USABILITY = "usability"       # 可用性/可复用性


# 维度权重 (总和 = 1.0)
DIMENSION_WEIGHTS: dict[EvalDimension, float] = {
    EvalDimension.COVERAGE: 0.25,
    EvalDimension.ACCURACY: 0.20,
    EvalDimension.CONSISTENCY: 0.20,
    EvalDimension.CREATIVITY: 0.15,
    EvalDimension.FORMAT: 0.10,
    EvalDimension.USABILITY: 0.10,
}

# 维度中文标签
DIMENSION_LABELS: dict[EvalDimension, str] = {
    EvalDimension.COVERAGE: "研究维度覆盖率",
    EvalDimension.ACCURACY: "设定准确性",
    EvalDimension.CONSISTENCY: "设定一致性",
    EvalDimension.CREATIVITY: "创意丰富度",
    EvalDimension.FORMAT: "格式规范性",
    EvalDimension.USABILITY: "可用性/可复用性",
}


class DimensionScore(BaseModel):
    """单个维度的评分."""
    dimension: EvalDimension
    score: float = Field(ge=0.0, le=5.0, description="维度得分 (0-5)")
    weight: float = Field(ge=0.0, le=1.0, description="维度权重")
    weighted_score: float = Field(default=0.0, description="加权得分")
    rationale: str = Field(default="", description="评分理由")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")

    def model_post_init(self, __context) -> None:
        self.weighted_score = self.score * self.weight


class EvalRubric(BaseModel):
    """评分标准 (Rubric)."""
    dimension: EvalDimension
    level_1: str = Field(description="1分标准")
    level_2: str = Field(description="2分标准")
    level_3: str = Field(description="3分标准")
    level_4: str = Field(description="4分标准")
    level_5: str = Field(description="5分标准")


# 预置评分标准
DEFAULT_RUBRICS: dict[EvalDimension, EvalRubric] = {
    EvalDimension.COVERAGE: EvalRubric(
        dimension=EvalDimension.COVERAGE,
        level_1="仅覆盖1个研究维度",
        level_2="覆盖2-3个研究维度",
        level_3="覆盖4-5个研究维度",
        level_4="覆盖6-7个研究维度，有深度",
        level_5="覆盖8+研究维度，全面深入,无盲区",
    ),
    EvalDimension.ACCURACY: EvalRubric(
        dimension=EvalDimension.ACCURACY,
        level_1="多处与 canon 严重不符",
        level_2="有2-3处明显错误",
        level_3="基本准确, 有1-2处小偏差",
        level_4="高度准确, 仅细微偏差",
        level_5="完全准确, 与 canon 完美对齐",
    ),
    EvalDimension.CONSISTENCY: EvalRubric(
        dimension=EvalDimension.CONSISTENCY,
        level_1="内部矛盾严重, 多处逻辑冲突",
        level_2="存在2-3处不一致",
        level_3="基本一致, 有1-2处可忽略的矛盾",
        level_4="高度一致, 仅边缘矛盾",
        level_5="完全一致, 无任何内部矛盾",
    ),
    EvalDimension.CREATIVITY: EvalRubric(
        dimension=EvalDimension.CREATIVITY,
        level_1="纯复制 canon, 无任何延伸",
        level_2="有少量简单延伸",
        level_3="有合理的创新和延伸",
        level_4="创新丰富且与 canon 融合自然",
        level_5="创新惊艳, 在 canon 基础上开辟新视角",
    ),
    EvalDimension.FORMAT: EvalRubric(
        dimension=EvalDimension.FORMAT,
        level_1="格式混乱, 难以阅读",
        level_2="有基本结构但不够清晰",
        level_3="结构清晰, 基本格式正确",
        level_4="格式规范, 排版精美",
        level_5="完美格式, 可直接出版级呈现",
    ),
    EvalDimension.USABILITY: EvalRubric(
        dimension=EvalDimension.USABILITY,
        level_1="无法直接用于写作",
        level_2="需要大幅修改才能使用",
        level_3="基本可用, 需要少量调整",
        level_4="可直接使用, 引用方便",
        level_5="即拿即用, 完美嵌入写作流程",
    ),
}


class EvaluationResult(BaseModel):
    """一次评估的完整结果."""
    id: str = Field(default_factory=lambda: f"eval-{uuid4().hex[:12]}")
    package_id: str = Field(description="被评估的设定包ID")
    evaluator: str = Field(default="auto", description="评估者: auto/human/hybrid")

    # 维度评分
    dimension_scores: list[DimensionScore] = Field(description="各维度评分")

    # 汇总
    total_score: float = Field(default=0.0, description="加权总分 (0-5)")
    grade: str = Field(default="", description="等级: A/B/C/D/F")

    # 额外指标
    coverage_rate: float = Field(default=0.0, description="研究维度覆盖率")
    consistency_hit_rate: float = Field(default=0.0, description="一致性检查命中率")

    # 对比信息
    compared_with: Optional[str] = Field(default=None, description="对比系统, 如 'ChatGPT'")
    comparison_winner: Optional[str] = Field(default=None, description="胜出方")
    comparison_notes: str = Field(default="", description="对比备注")

    created_at: datetime = Field(default_factory=datetime.now)

    def model_post_init(self, __context) -> None:
        if self.dimension_scores:
            self.total_score = sum(d.weighted_score for d in self.dimension_scores)
            # 计算等级
            if self.total_score >= 4.5:
                self.grade = "A"
            elif self.total_score >= 4.0:
                self.grade = "B"
            elif self.total_score >= 3.0:
                self.grade = "C"
            elif self.total_score >= 2.0:
                self.grade = "D"
            else:
                self.grade = "F"

    @classmethod
    def create_empty(cls, package_id: str) -> "EvaluationResult":
        """创建空白评估 (待填充)."""
        scores = [
            DimensionScore(
                dimension=dim,
                score=0.0,
                weight=DIMENSION_WEIGHTS[dim],
            )
            for dim in EvalDimension
        ]
        return cls(package_id=package_id, dimension_scores=scores)
