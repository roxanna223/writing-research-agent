"""LLM 统一客户端 — 封装 Anthropic / OpenAI API.

设计原则:
- 统一接口: generate(messages) → text
- 自动检测 provider (基于 model 名称)
- 透明重试 + 速率限制
- 不暴露 provider 差异给上层
"""

import asyncio
import logging
import time
from typing import Any, Optional

from .config import LLMConfig

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """LLM 调用错误."""
    def __init__(self, message: str, provider: str = "", status_code: int = 0):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code


class LLMClient:
    """统一 LLM 客户端.

    自动路由到正确的 provider SDK.

    用法:
        config = LLMConfig(model="claude-sonnet-5")
        client = LLMClient(config)
        text = await client.generate([
            {"role": "system", "content": "You are..."},
            {"role": "user", "content": "Hello"},
        ])
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._anthropic_client = None
        self._openai_client = None
        self._call_count = 0
        self._total_cost_estimate = 0.0

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        response_format: Optional[dict] = None,
    ) -> str:
        """调用 LLM 生成文本.

        Args:
            messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
            temperature: 覆盖默认温度
            max_tokens: 覆盖默认 max_tokens
            top_p: 覆盖默认 top_p
            response_format: {"type": "json_object"} 用于 JSON 模式

        Returns:
            生成的文本
        """
        temp = temperature if temperature is not None else self.config.default_temperature
        mt = max_tokens if max_tokens is not None else self.config.default_max_tokens
        tp = top_p if top_p is not None else self.config.default_top_p

        for attempt in range(self.config.max_retries):
            try:
                if self.config.provider == "anthropic":
                    result = await self._call_anthropic(messages, temp, mt, tp)
                elif self.config.provider == "openai":
                    result = await self._call_openai(messages, temp, mt, tp, response_format)
                else:
                    raise LLMError(f"Unknown provider: {self.config.provider}")

                self._call_count += 1
                return result

            except Exception as e:
                logger.warning(
                    f"LLM call attempt {attempt + 1}/{self.config.max_retries} failed: {e}"
                )
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay_seconds * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    raise LLMError(
                        f"LLM call failed after {self.config.max_retries} attempts: {e}",
                        provider=self.config.provider,
                    )

        raise LLMError("Unreachable")

    async def _call_anthropic(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        top_p: float,
    ) -> str:
        """调用 Anthropic Claude API."""
        api_key = self.config.anthropic_api_key
        if not api_key:
            raise LLMError(
                "ANTHROPIC_API_KEY not set. "
                "Set env var or pass config.anthropic_api_key"
            )

        # 提取 system + user messages
        system = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                user_messages.append(msg)

        try:
            import anthropic
        except ImportError:
            raise LLMError(
                "anthropic package not installed. Run: pip install anthropic"
            )

        if self._anthropic_client is None:
            self._anthropic_client = anthropic.AsyncAnthropic(api_key=api_key)

        response = await self._anthropic_client.messages.create(
            model=self.config.model,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            system=system if system else anthropic.NOT_GIVEN,
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in user_messages
            ],
        )

        return response.content[0].text

    async def _call_openai(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        top_p: float,
        response_format: Optional[dict] = None,
    ) -> str:
        """调用 OpenAI API."""
        api_key = self.config.openai_api_key
        if not api_key:
            raise LLMError(
                "OPENAI_API_KEY not set. "
                "Set env var or pass config.openai_api_key"
            )

        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise LLMError(
                "openai package not installed. Run: pip install openai"
            )

        if self._openai_client is None:
            self._openai_client = AsyncOpenAI(api_key=api_key)

        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = await self._openai_client.chat.completions.create(**kwargs)

        return response.choices[0].message.content or ""

    async def generate_structured(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """生成 JSON 结构化输出.

        自动设置 response_format (OpenAI) 或 Prompt 约束 (Anthropic).
        """
        if self.config.provider == "openai":
            return await self.generate(
                messages, temperature, max_tokens,
                response_format={"type": "json_object"},
            )
        else:
            # Anthropic: 依赖 Prompt 中的 JSON 约束
            return await self.generate(messages, temperature, max_tokens)

    @property
    def stats(self) -> dict:
        """调用统计."""
        return {
            "calls": self._call_count,
            "provider": self.config.provider,
            "model": self.config.model,
        }
