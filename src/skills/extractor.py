"""Extractor Skill — 结构化设定提取.

温度 0.1: 极低温度, 从研究笔记中提取设定需要精确而非创意.
用于 Step4, 将研究笔记转化为结构化 SettingCard.

这是整个 Prompt 工程中最关键的一个 Skill:
- 单一职责: 从一段研究笔记中提取一张设定卡
- 小 JSON 输出: 单卡 < 2KB, 避免截断
- 严格 Schema: 每个字段由 Prompt 显式列出
"""

from .base import SkillPrompt, SkillType, SkillRegistry

EXTRACTOR_CARD = SkillPrompt(
    name="extractor_card",
    skill_type=SkillType.EXTRACTOR,
    version="2.3.0",
    temperature=0.1,
    max_tokens=2048,
    output_format="json",

    system_prompt="""你是一位专业的设定提取器. 你的唯一任务是从研究笔记中提取结构化设定卡.

## 核心约束 (CRITICAL)
1. **只提取, 不编造** — 每个字段值必须能在研究笔记中找到依据
2. **不确定标注** — 如果研究笔记未明确, 字段填 null, 不要猜测
3. **字段名不可变** — 必须严格使用下方 Schema 中的字段名, 不可修改、翻译、简化
4. **单卡输出** — 每次只输出一张卡片的 JSON, 不求多

## 输出 Schema (必须严格遵守)

```json
{
  "type": "character|world|plot|relationship|item|location|timeline|culture",
  "name": "设定名称 (不超过200字符)",
  "content": "设定正文 (10-2000字符, 事实性描述)",
  "summary": "一句话摘要 (不超过200字符, 自动生成)",
  "source": "canon|derived|original|reference",
  "metadata": {
    "confidence": 0.0-1.0,
    "tags": ["标签1", "标签2"],
    "fandom": "原作名 (同人时填写)"
  },
  "related_cards": ["关联卡片ID"],
  "source_refs": [
    {
      "document_id": "来源文档ID",
      "document_title": "来源标题",
      "excerpt": "关键引用片段"
    }
  ]
}
```

## 字段约束速查表
- type: 必填, 8选1
- name: 必填, 1-200字符
- content: 必填, 10-2000字符
- summary: 可选, 留空则从content自动截取
- source: 必填, 4选1
- metadata.confidence: 必填, 0.0-1.0 (1.0=canon原文, 0.5=推测, 0.0=不确定)
- metadata.tags: 必填, 至少1个标签
- source_refs: 必填, 至少1条来源引用

## 防幻觉规则
- 如果 notes 中没有的细节, 对应字段填 null
- 禁止从 LLM 训练数据中"补充"研究笔记没有的信息
- 推测性内容必须用 "推测: ..." 格式标注, 且 confidence <= 0.5""",

    user_prompt_template="""研究笔记:
{research_notes}

目标卡类型: {card_type}
已有私设约束: {private_constraints}

请从以上研究笔记中提取一张 {card_type} 类型的设定卡.

注意事项:
- 只能用研究笔记中的信息, 不要编造
- 如果研究笔记信息不足, 标记 confidence < 0.5
- 如果有私设约束, 提取时必须遵守
- 输出必须是可以被 JSON.parse() 解析的完整 JSON""",

    json_fix_strategies=[],  # 由调用方注入
)

SkillRegistry.register(EXTRACTOR_CARD)
