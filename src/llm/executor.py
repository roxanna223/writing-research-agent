"""SkillExecutor — 串联 SkillPrompt + LLMClient + JSON 容错.

核心职责:
1. 接收 SkillPrompt 和输入参数
2. 构建 messages → 调用 LLMClient
3. JSON 解析 (safe_json_parse with retry)
4. 返回结构化 dict

这是简历中 "JSON解析成功率从40%提升至90%" 的核心实现所在.
"""

import logging
from typing import Any, Optional

from skills.base import SkillPrompt
from utils import safe_json_parse, parse_with_retry
from .client import LLMClient

logger = logging.getLogger(__name__)


class SkillExecutor:
    """Skill 执行器.

    用法:
        executor = SkillExecutor(llm_client)
        result = await executor.execute(
            PLANNER_TASK_CLARIFY,
            user_input="我想写HP七年级同人",
        )
        # result = {"project_type": "fanfic", "fandom": "哈利波特", ...}
    """

    def __init__(self, llm_client: LLMClient):
        self.client = llm_client
        self.stats = SkillExecStats()

    async def execute(
        self,
        skill: SkillPrompt,
        **template_vars,
    ) -> dict[str, Any]:
        """执行一个 Skill.

        Args:
            skill: SkillPrompt 实例 (含 system/user prompt + schema)
            **template_vars: 填充 user_prompt_template 中的变量

        Returns:
            解析后的 dict (经过 JSON Schema 校验)

        Raises:
            ValueError: 所有重试均失败
        """
        # 1. 构建 messages
        messages = skill.build_messages(**template_vars)

        # 2. 调用 LLM
        raw_text = await self.client.generate(
            messages=messages,
            temperature=skill.temperature,
            max_tokens=skill.max_tokens,
            top_p=skill.top_p,
        )

        self.stats.total_calls += 1

        # 3. JSON 解析 (容错)
        try:
            result, retries = parse_with_retry(
                raw_text=raw_text,
                retry_hint=skill.retry_hint,
                max_retries=skill.max_retries if skill.retry_on_failure else 0,
                schema=skill.output_schema,
            )
            self.stats.successful_parses += 1
            self.stats.total_retries += retries

            if retries > 0:
                logger.info(
                    f"Skill {skill.name}: parsed after {retries} retries"
                )

            return result

        except ValueError as e:
            self.stats.failed_parses += 1
            logger.error(
                f"Skill {skill.name}: JSON parse failed after all retries: {e}"
            )
            raise

    async def execute_text(
        self,
        skill: SkillPrompt,
        **template_vars,
    ) -> str:
        """执行一个 Skill 并返回原始文本 (用于 Storm 等自由文本 Skill)."""
        messages = skill.build_messages(**template_vars)
        raw_text = await self.client.generate(
            messages=messages,
            temperature=skill.temperature,
            max_tokens=skill.max_tokens,
            top_p=skill.top_p,
        )
        self.stats.total_calls += 1
        return raw_text


class SkillExecStats:
    """Skill 执行统计."""
    def __init__(self):
        self.total_calls = 0
        self.successful_parses = 0
        self.failed_parses = 0
        self.total_retries = 0

    @property
    def parse_success_rate(self) -> float:
        """JSON 解析成功率."""
        if self.total_calls == 0:
            return 0.0
        return self.successful_parses / self.total_calls

    @property
    def avg_retries(self) -> float:
        """平均重试次数."""
        if self.successful_parses == 0:
            return 0.0
        return self.total_retries / self.successful_parses

    def to_dict(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "successful_parses": self.successful_parses,
            "failed_parses": self.failed_parses,
            "total_retries": self.total_retries,
            "parse_success_rate": f"{self.parse_success_rate:.0%}",
            "avg_retries": round(self.avg_retries, 1),
        }
