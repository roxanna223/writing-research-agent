"""LLM 配置管理 — 环境变量 + 默认值."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    """LLM 调用配置.

    优先级: 环境变量 > 默认值 > 代码传入
    """

    # 模型选择
    model: str = field(
        default_factory=lambda: os.getenv("LITELLM_MODEL", "claude-sonnet-5")
    )
    # 可选: gpt-4o, gpt-4o-mini, claude-opus-4-8, claude-haiku-4-5

    # API Keys
    anthropic_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY")
    )
    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )

    # 默认生成参数 (可被 SkillPrompt 覆盖)
    default_temperature: float = 0.3
    default_max_tokens: int = 2048
    default_top_p: float = 0.95

    # 速率限制
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    request_timeout: int = 60

    # 成本控制
    max_budget_per_call: float = 0.50  # 单次调用最大 $0.50

    @property
    def is_configured(self) -> bool:
        """检查是否至少配置了一个 API key."""
        return bool(self.anthropic_api_key or self.openai_api_key)

    @property
    def provider(self) -> str:
        """推断当前使用的 provider."""
        if "claude" in self.model.lower() or "anthropic" in self.model.lower():
            return "anthropic"
        if "gpt" in self.model.lower() or "openai" in self.model.lower():
            return "openai"
        return "unknown"

    @property
    def requires_key(self) -> Optional[str]:
        """返回所需的 API key 环境变量名."""
        if self.provider == "anthropic":
            return "ANTHROPIC_API_KEY"
        if self.provider == "openai":
            return "OPENAI_API_KEY"
        return None
