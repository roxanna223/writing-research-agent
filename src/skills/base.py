"""Skill Prompt 基类与注册中心."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class SkillType(str, Enum):
    PLANNER = "planner"
    STORM = "storm"
    CLEAR = "clear"
    RESEARCHER = "researcher"
    EXTRACTOR = "extractor"
    CHECKER = "checker"
    FORMATTER = "formatter"


@dataclass
class SkillPrompt:
    """一个 Skill 的 Prompt 模板.

    设计要点:
    - temperature 按职责设定: 创意任务高, 严谨任务低
    - output_schema: 约束 LLM 输出格式, 减少字段漂移
    - max_tokens: 限制输出长度, 防止 JSON 截断
    - retry_on_failure: 是否在解析失败时重试
    - retry_hint: 重试时的修复提示
    """

    name: str
    skill_type: SkillType
    version: str = "1.0.0"

    # Prompt 模板
    system_prompt: str = ""
    user_prompt_template: str = ""

    # 生成参数
    temperature: float = 0.3
    max_tokens: int = 2048
    top_p: float = 0.95

    # 输出约束
    output_schema: Optional[dict] = None         # JSON Schema
    output_format: str = "json"                   # json | text | markdown
    few_shot_examples: list[dict] = field(default_factory=list)

    # 容错配置
    retry_on_failure: bool = True
    max_retries: int = 3
    retry_hint: str = ""                          # 重试时追加的修复提示

    # JSON 解析容错
    json_fix_strategies: list[Callable[[str], str]] = field(default_factory=list)

    def build_user_prompt(self, **kwargs) -> str:
        """填充模板变量, 生成 User Prompt."""
        prompt = self.user_prompt_template
        for key, value in kwargs.items():
            prompt = prompt.replace(f"{{{key}}}", str(value))
        return prompt

    def build_messages(self, **kwargs) -> list[dict]:
        """构建完整的 messages 数组."""
        messages = [{"role": "system", "content": self.system_prompt}]

        # 如果有 few-shot 示例, 拼入 system
        if self.few_shot_examples:
            shots_text = "\n\n## 示例\n\n"
            for i, example in enumerate(self.few_shot_examples, 1):
                shots_text += f"### 示例 {i}\n"
                shots_text += f"输入: {example.get('input', '')}\n"
                shots_text += f"输出: {example.get('output', '')}\n\n"
            messages[0]["content"] += shots_text

        messages.append({
            "role": "user",
            "content": self.build_user_prompt(**kwargs),
        })
        return messages


class SkillRegistry:
    """Skill 注册中心 — 管理所有 Prompt 模板."""

    _instance: Optional["SkillRegistry"] = None
    _skills: dict[str, SkillPrompt] = {}

    def __new__(cls) -> "SkillRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, skill: SkillPrompt) -> None:
        cls._skills[skill.name] = skill

    @classmethod
    def get(cls, name: str) -> Optional[SkillPrompt]:
        return cls._skills.get(name)

    @classmethod
    def list_all(cls) -> list[str]:
        return list(cls._skills.keys())

    @classmethod
    def get_by_step(cls, step: int) -> list[SkillPrompt]:
        """获取某步骤关联的所有 Skill."""
        step_skill_map = {
            1: ["planner_task_clarify", "clear_clarify"],
            2: ["planner_research_plan"],
            3: ["researcher_query"],
            4: ["extractor_card", "storm_brainstorm"],
            5: ["checker_validate"],
            6: [],  # Formatter 不调用 LLM
        }
        names = step_skill_map.get(step, [])
        return [cls._skills[n] for n in names if n in cls._skills]
