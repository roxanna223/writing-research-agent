"""设定包 (SettingPackage) — 由设定卡确定性组装而成的完整设定.

设计原则:
- 组装引擎用模板+规则拼装, 不依赖 LLM → 生成稳定率 100%
- 分类索引支持快速定位
- 支持多格式导出 (Markdown/JSON/HTML)
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from .setting_card import SettingCard, CardType


class ExportFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"


class CategoryIndex(BaseModel):
    """分类索引 — 按卡片类型组织."""
    characters: list[str] = Field(default_factory=list, description="人物卡ID列表")
    world_settings: list[str] = Field(default_factory=list, description="世界观卡ID列表")
    plots: list[str] = Field(default_factory=list, description="情节卡ID列表")
    relationships: list[str] = Field(default_factory=list, description="关系卡ID列表")
    items: list[str] = Field(default_factory=list, description="物品卡ID列表")
    locations: list[str] = Field(default_factory=list, description="地点卡ID列表")
    timelines: list[str] = Field(default_factory=list, description="时间线卡ID列表")
    cultures: list[str] = Field(default_factory=list, description="文化卡ID列表")

    @property
    def total_cards(self) -> int:
        return sum(len(v) for v in [
            self.characters, self.world_settings, self.plots,
            self.relationships, self.items, self.locations,
            self.timelines, self.cultures,
        ])


class ConflictReport(BaseModel):
    """冲突报告 — Checker 在 Step5 产出."""
    card_id_a: str
    card_id_b: str
    conflict_type: str = Field(description="冲突类型: 时间线矛盾/人物设定覆盖/世界观冲突")
    description: str
    severity: str = Field(default="medium", description="严重程度: low/medium/high/critical")


class AssemblyConfig(BaseModel):
    """组装配置."""
    template_name: str = Field(default="default", description="组装模板名")
    include_toc: bool = Field(default=True, description="是否包含目录")
    group_by: str = Field(default="type", description="分组方式: type/category/custom")
    sort_order: list[str] = Field(
        default_factory=lambda: [
            "character", "relationship", "world", "location",
            "timeline", "culture", "plot", "item",
        ],
        description="分组排序"
    )
    export_format: ExportFormat = Field(default=ExportFormat.MARKDOWN)


class SettingPackage(BaseModel):
    """设定包 — 核心数据模型.

    由 AssemblyEngine 从 SettingCard 列表确定性组装.
    不经过 LLM → 无截断风险 → 稳定率 100%.
    """

    id: str = Field(default_factory=lambda: f"pkg-{uuid4().hex[:12]}")
    title: str = Field(description="设定包标题")
    description: str = Field(default="", description="设定包描述")
    fandom: Optional[str] = Field(default=None, description="原作/圈子")

    # 卡片引用
    cards: dict[str, SettingCard] = Field(
        default_factory=dict, description="卡片ID → 卡片对象映射"
    )
    category_index: CategoryIndex = Field(
        default_factory=CategoryIndex, description="分类索引"
    )

    # 组装信息
    assembly_config: AssemblyConfig = Field(default_factory=AssemblyConfig)
    assembly_version: str = Field(default="1.0.0")
    assembly_template: str = Field(default="default")

    # 质检信息
    conflict_reports: list[ConflictReport] = Field(
        default_factory=list, description="冲突报告列表"
    )
    checker_passed: bool = Field(
        default=False, description="是否通过 Checker 校验"
    )

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    card_count: int = Field(default=0)
    version: int = Field(default=1)

    def model_post_init(self, __context) -> None:
        self._refresh_indices()

    def add_card(self, card: SettingCard) -> None:
        """添加一张设定卡并更新索引."""
        self.cards[card.id] = card
        self._index_card(card)
        self.card_count = len(self.cards)
        self.updated_at = datetime.now()

    def remove_card(self, card_id: str) -> Optional[SettingCard]:
        """移除一张设定卡."""
        card = self.cards.pop(card_id, None)
        if card:
            self._refresh_indices()
            self.card_count = len(self.cards)
            self.updated_at = datetime.now()
        return card

    def _refresh_indices(self) -> None:
        """重建分类索引."""
        self.category_index = CategoryIndex()
        for card in self.cards.values():
            self._index_card(card)
        self.card_count = len(self.cards)

    def _index_card(self, card: SettingCard) -> None:
        """将卡片加入对应分类索引."""
        idx = self.category_index
        type_map = {
            CardType.CHARACTER: idx.characters,
            CardType.WORLD: idx.world_settings,
            CardType.PLOT: idx.plots,
            CardType.RELATIONSHIP: idx.relationships,
            CardType.ITEM: idx.items,
            CardType.LOCATION: idx.locations,
            CardType.TIMELINE: idx.timelines,
            CardType.CULTURE: idx.cultures,
        }
        target = type_map.get(card.type)
        if target is not None and card.id not in target:
            target.append(card.id)

    def get_cards_by_type(self, card_type: CardType) -> list[SettingCard]:
        """按类型获取卡片列表."""
        return [
            c for c in self.cards.values() if c.type == card_type
        ]

    def get_conflict_free_cards(self) -> list[SettingCard]:
        """获取无冲突的卡片."""
        conflict_ids = set()
        for report in self.conflict_reports:
            conflict_ids.add(report.card_id_a)
            conflict_ids.add(report.card_id_b)
        return [c for c in self.cards.values() if c.id not in conflict_ids]

    def to_markdown(self) -> str:
        """导出为 Markdown 格式."""
        lines = [
            f"# {self.title}",
            f"",
            f"> {self.description}" if self.description else "",
            f"> 原作: {self.fandom}" if self.fandom else "",
            f"> 卡片总数: {self.card_count}",
            f"> 生成时间: {self.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"",
        ]
        if self.conflict_reports:
            lines.append("## ⚠ 冲突报告")
            lines.append("")
            for r in self.conflict_reports:
                lines.append(f"- **[{r.severity}]** {r.description}")
            lines.append("")

        # 按类型排序输出
        sort_order = self.assembly_config.sort_order
        for card_type_str in sort_order:
            try:
                card_type = CardType(card_type_str)
            except ValueError:
                continue
            cards = self.get_cards_by_type(card_type)
            if not cards:
                continue
            lines.append(f"## {_CARD_TYPE_LABELS.get(card_type, card_type.value)}")
            lines.append("")
            for card in cards:
                lines.append(card.to_markdown())
                lines.append("")
        return "\n".join(lines)

    def to_json_export(self) -> dict:
        """导出为 JSON 格式 (datetime → ISO string)."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "fandom": self.fandom,
            "card_count": self.card_count,
            "cards": [
                c.model_dump(mode="json") for c in self.cards.values()
            ],
            "conflicts": [
                r.model_dump(mode="json") for r in self.conflict_reports
            ],
            "created_at": self.created_at.isoformat(),
        }


_CARD_TYPE_LABELS = {
    CardType.CHARACTER: "👤 人物设定",
    CardType.RELATIONSHIP: "🔗 关系设定",
    CardType.WORLD: "🌍 世界观设定",
    CardType.LOCATION: "📍 地点设定",
    CardType.TIMELINE: "⏳ 时间线设定",
    CardType.CULTURE: "🎭 文化设定",
    CardType.PLOT: "📖 情节设定",
    CardType.ITEM: "🔮 物品设定",
}
