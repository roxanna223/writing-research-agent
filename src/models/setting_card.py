"""设定卡 (SettingCard) — 最小粒度的设定数据单元.

设计原则:
- 一张卡 = 一个设定点 (单一人/事/物/关系)
- LLM 只负责生成单张卡 → 避免端到端长 JSON 截断
- 确定性组装引擎从卡片拼出设定包
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CardType(str, Enum):
    """设定卡类型."""
    CHARACTER = "character"      # 人物设定
    WORLD = "world"              # 世界观设定
    PLOT = "plot"                # 情节设定
    RELATIONSHIP = "relationship"  # 关系设定
    ITEM = "item"                # 物品/道具设定
    LOCATION = "location"        # 地点设定
    TIMELINE = "timeline"        # 时间线设定
    CULTURE = "culture"          # 文化/社会设定


class SourceType(str, Enum):
    """设定来源类型."""
    CANON = "canon"          # 原作原有设定
    DERIVED = "derived"      # 从原作推导的设定
    ORIGINAL = "original"    # 完全原创的设定
    REFERENCE = "reference"  # 参考外部资料


class CardMetadata(BaseModel):
    """卡片元数据."""
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="置信度: 1.0=canon确认, 0.5=推测, 0.0=不确定"
    )
    tags: list[str] = Field(default_factory=list, description="标签列表")
    fandom: Optional[str] = Field(default=None, description="所属同人圈/原作")
    version: int = Field(default=1, description="版本号, 每次修改+1")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    extraction_prompt_version: Optional[str] = Field(
        default=None, description="生成此卡的Prompt版本"
    )


class SourceRef(BaseModel):
    """溯源引用."""
    document_id: str = Field(description="来源文档ID")
    document_title: str = Field(description="来源文档标题")
    excerpt: Optional[str] = Field(default=None, description="引用片段")
    chunk_index: Optional[int] = Field(default=None, description="文档中的chunk位置")


class SettingCard(BaseModel):
    """设定卡 — 核心数据模型.

    设计要点:
    - JSON 体积小 (<2KB) → LLM 截断风险低
    - 字段名固定, 用 Schema 约束 → 避免字段漂移
    - 关联字段支持图结构 → 确定性组装的基础
    """

    # 核心标识
    id: str = Field(
        default_factory=lambda: f"card-{uuid4().hex[:12]}",
        description="卡片唯一ID"
    )
    type: CardType = Field(description="设定类型")

    # 内容字段
    name: str = Field(
        min_length=1, max_length=200,
        description="设定名称, 如 '西弗勒斯·斯内普'"
    )
    content: str = Field(
        min_length=10, max_length=2000,
        description="设定正文, 10-2000字符"
    )
    summary: str = Field(
        default="", max_length=200,
        description="一句话摘要, 用于列表展示和快速检索"
    )
    source: SourceType = Field(description="设定来源")

    # 溯源
    source_refs: list[SourceRef] = Field(
        default_factory=list, description="参考资料来源列表"
    )

    # 关联 (用于图结构组装)
    related_cards: list[str] = Field(
        default_factory=list,
        description="关联卡片ID列表, 如人物的关联关系"
    )
    conflicts_with: list[str] = Field(
        default_factory=list,
        description="冲突卡片ID列表, 由Checker填充"
    )
    parent_card: Optional[str] = Field(
        default=None, description="父卡片ID, 用于层级结构"
    )

    # 元数据
    metadata: CardMetadata = Field(default_factory=CardMetadata)

    @field_validator("summary", mode="before")
    @classmethod
    def set_default_summary(cls, v: str, info) -> str:
        """未填 summary 时从 content 自动截取."""
        if not v:
            content = info.data.get("content", "")
            if content:
                return content[:200]
        return v

    def to_markdown(self) -> str:
        """导出为 Markdown 格式."""
        lines = [
            f"## {self.name}",
            f"- **类型**: {self.type.value}",
            f"- **来源**: {self.source.value}",
            f"- **置信度**: {self.metadata.confidence:.0%}",
            f"- **标签**: {', '.join(self.metadata.tags)}",
            "",
            self.content,
            "",
        ]
        if self.related_cards:
            lines.append(f"- **关联**: {', '.join(self.related_cards)}")
        if self.conflicts_with:
            lines.append(f"- **⚠ 冲突**: {', '.join(self.conflicts_with)}")
        return "\n".join(lines)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "character",
                "name": "西弗勒斯·斯内普",
                "content": "霍格沃茨魔药学教授, 斯莱特林院长. "
                          "表面冷漠严厉, 实则为保护哈利暗中付出. "
                          "双面间谍, 精通大脑封闭术和黑魔法防御.",
                "summary": "霍格沃茨魔药学教授, 双面间谍",
                "source": "canon",
                "tags": ["斯莱特林", "教授", "凤凰社"],
                "fandom": "哈利波特",
                "confidence": 0.95,
            }
        }
    )
