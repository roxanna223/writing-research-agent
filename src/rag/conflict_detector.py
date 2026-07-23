"""私设冲突自动定位 — 简历中"私设冲突自动定位"功能的实现.

算法流程:
1. 新设定卡片字段化 → 提取断言列表
2. 在 L3 私设库中检索同类字段
3. 字段级比对 → 分类冲突类型
4. 生成冲突报告
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .knowledge_base import KnowledgeBase, KnowledgeChunk, KnowledgeLayer
from .retriever import MultiLayerRetriever


class ConflictType(str, Enum):
    """冲突类型."""
    DIRECT = "direct"           # 直接矛盾: A=17, B=16
    IMPLICIT = "implicit"       # 隐含矛盾: 需要推理
    TIMELINE = "timeline"       # 时间线冲突: 年龄/日期不对
    OVERRIDE = "override"       # 设定覆盖: 新卡覆盖旧卡 (可能是合法的)
    DUPLICATE = "duplicate"     # 重复设定


class ConflictSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Assertion:
    """从设定卡提取的断言."""
    card_id: str
    field_path: str              # 如 "basicInfo.age"
    field_value: str             # 字符串化后的值
    field_type: str              # string | number | boolean
    subject: str                 # 断言主体, 如 "character:哈利波特"
    predicate: str               # 断言谓词, 如 "age"


@dataclass
class ConflictReport:
    """冲突报告."""
    card_id_a: str
    card_id_b: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    field_path: str
    value_a: str
    value_b: str
    description: str = ""
    resolution: str = ""         # auto_fix | auto_suggest | human_review
    suggested_fix: str = ""


class ConflictDetector:
    """私设冲突自动定位器.

    核心方法: detect_conflicts(new_card_assertions, existing_knowledge) → ConflictReport[]
    """

    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
        self.retriever = MultiLayerRetriever(knowledge_base)

    def extract_assertions(self, card: dict) -> list[Assertion]:
        """从设定卡中提取所有断言.

        将嵌套的 JSON 扁平化为 (主体, 谓词, 值) 三元组.
        """
        assertions: list[Assertion] = []
        card_id = card.get("id", "unknown")

        def _extract(obj, prefix: str = ""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    full_path = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, (str, int, float, bool)):
                        assertions.append(Assertion(
                            card_id=card_id,
                            field_path=full_path,
                            field_value=str(value),
                            field_type=type(value).__name__,
                            subject=f"card:{card_id}",
                            predicate=full_path,
                        ))
                    elif isinstance(value, (dict, list)):
                        _extract(value, full_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    _extract(item, f"{prefix}[{i}]")

        _extract(card)
        return assertions

    def detect_conflicts(
        self,
        new_card: dict,
        existing_cards: list[dict],
        project_id: str = "",
    ) -> list[ConflictReport]:
        """检测新卡与已有卡片之间的冲突.

        Args:
            new_card: 新生成的设定卡
            existing_cards: 同项目已有的设定卡
            project_id: 项目ID

        Returns:
            冲突报告列表
        """
        new_assertions = self.extract_assertions(new_card)
        reports: list[ConflictReport] = []

        for assertion in new_assertions:
            # 在已有卡片中检索同类断言
            for existing_card in existing_cards:
                if existing_card.get("id") == assertion.card_id:
                    continue  # 跳过自身

                existing_assertions = self.extract_assertions(existing_card)

                for ex_assertion in existing_assertions:
                    # 比对: 同类型 + 同主体 + 同谓词
                    if self._is_comparable(assertion, ex_assertion):
                        conflict = self._compare_assertions(
                            assertion, ex_assertion
                        )
                        if conflict:
                            reports.append(conflict)

        return reports

    def _is_comparable(self, a1: Assertion, a2: Assertion) -> bool:
        """判断两个断言是否可比 (同类型、同语义领域)."""
        # 简化: 同字段路径的最后一段
        a1_field = a1.field_path.split(".")[-1] if "." in a1.field_path else a1.field_path
        a2_field = a2.field_path.split(".")[-1] if "." in a2.field_path else a2.field_path
        return a1_field == a2_field and a1.field_type == a2.field_type

    def _compare_assertions(
        self, new_a: Assertion, old_a: Assertion
    ) -> Optional[ConflictReport]:
        """比对两个断言, 判断是否冲突."""
        # 值相同 → 不冲突 (可能是补充而非覆盖)
        if new_a.field_value.strip().lower() == old_a.field_value.strip().lower():
            return ConflictReport(
                card_id_a=new_a.card_id,
                card_id_b=old_a.card_id,
                conflict_type=ConflictType.DUPLICATE,
                severity=ConflictSeverity.LOW,
                field_path=new_a.field_path,
                value_a=new_a.field_value,
                value_b=old_a.field_value,
                description=f"字段 {new_a.field_path} 的值与已有设定相同: {new_a.field_value}",
                resolution="auto_fix",
                suggested_fix="标记为重复, 可合并",
            )

        # 值不同 → 可能冲突
        conflict_type = self._classify_conflict(new_a, old_a)

        return ConflictReport(
            card_id_a=new_a.card_id,
            card_id_b=old_a.card_id,
            conflict_type=conflict_type,
            severity=self._determine_severity(conflict_type),
            field_path=new_a.field_path,
            value_a=new_a.field_value,
            value_b=old_a.field_value,
            description=self._describe_conflict(new_a, old_a, conflict_type),
            resolution=self._suggest_resolution(conflict_type),
            suggested_fix=self._suggest_fix(new_a, old_a),
        )

    @staticmethod
    def _classify_conflict(new_a: Assertion, old_a: Assertion) -> ConflictType:
        """分类冲突类型."""
        # 时间相关字段 → TIMELINE
        time_fields = {"age", "date", "year", "timeline", "birth", "death"}
        field_name = new_a.field_path.split(".")[-1].lower()
        if field_name in time_fields:
            return ConflictType.TIMELINE

        # 数字型冲突 → DIRECT (明确矛盾)
        if new_a.field_type == "number":
            return ConflictType.DIRECT

        # 默认为直接矛盾
        return ConflictType.DIRECT

    @staticmethod
    def _determine_severity(conflict_type: ConflictType) -> ConflictSeverity:
        """根据冲突类型确定严重程度."""
        severity_map = {
            ConflictType.DIRECT: ConflictSeverity.HIGH,
            ConflictType.IMPLICIT: ConflictSeverity.MEDIUM,
            ConflictType.TIMELINE: ConflictSeverity.CRITICAL,
            ConflictType.OVERRIDE: ConflictSeverity.LOW,
            ConflictType.DUPLICATE: ConflictSeverity.LOW,
        }
        return severity_map.get(conflict_type, ConflictSeverity.MEDIUM)

    @staticmethod
    def _describe_conflict(
        new_a: Assertion, old_a: Assertion, conflict_type: ConflictType
    ) -> str:
        """生成冲突描述."""
        templates = {
            ConflictType.DIRECT: (
                f"字段 '{new_a.field_path}' 的值冲突: "
                f"新值='{new_a.field_value}' vs 已有='{old_a.field_value}'"
            ),
            ConflictType.TIMELINE: (
                f"时间线冲突: '{new_a.field_path}' 的 "
                f"新值='{new_a.field_value}' 与已有设定='{old_a.field_value}' 矛盾"
            ),
            ConflictType.OVERRIDE: (
                f"设定覆盖: '{new_a.field_path}' 的 "
                f"新值='{new_a.field_value}' 将覆盖旧值='{old_a.field_value}'"
            ),
            ConflictType.DUPLICATE: (
                f"重复设定: '{new_a.field_path}' 在两个卡片中值相同"
            ),
            ConflictType.IMPLICIT: (
                f"隐含不一致: '{new_a.field_path}' 可能与其他设定矛盾"
            ),
        }
        return templates.get(conflict_type, f"未知冲突类型: {new_a.field_path}")

    @staticmethod
    def _suggest_resolution(conflict_type: ConflictType) -> str:
        """建议解决方式."""
        resolution_map = {
            ConflictType.DIRECT: "human_review",    # 需要人工判断哪个值正确
            ConflictType.IMPLICIT: "human_review",
            ConflictType.TIMELINE: "auto_suggest",  # 可自动计算正确值
            ConflictType.OVERRIDE: "auto_fix",      # 新值覆盖旧值
            ConflictType.DUPLICATE: "auto_fix",     # 自动去重
        }
        return resolution_map.get(conflict_type, "human_review")

    @staticmethod
    def _suggest_fix(new_a: Assertion, old_a: Assertion) -> str:
        """生成修复建议."""
        return (
            f"请确认字段 '{new_a.field_path}' 的正确值.\n"
            f"  方案A: 采用新值 '{new_a.field_value}'\n"
            f"  方案B: 保留已有 '{old_a.field_value}'\n"
            f"  方案C: 自行指定其他值"
        )
