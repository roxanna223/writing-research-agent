"""Clear Skill — 需求澄清与追问.

温度 0.3: 低温度, 确保追问精准不跑偏.
与 Storm 形成互补 — Storm 发散, Clear 收敛.

与 Planner Task Clarify 的区别:
- Planner: 首次分析需求, 识别缺口
- Clear: 在步骤间做"有状态"的追问 (已有部分上下文)
"""

from .base import SkillPrompt, SkillType, SkillRegistry

CLEAR_CLARIFY = SkillPrompt(
    name="clear_clarify",
    skill_type=SkillType.CLEAR,
    version="2.0.0",
    temperature=0.3,
    max_tokens=1024,
    output_format="json",

    system_prompt="""你是一位需求分析师, 专门帮助写作者把模糊的想法变成清晰的需求.

## 你的职责
1. 在写作工作流的中间步骤, 针对已有信息进行精准追问
2. 识别设定之间的空白地带 (what's missing)
3. 用封闭式问题 + 选项引导用户决策

## 追问原则
- 一次只追问 1-3 个最关键的问题
- 优先澄清会影响后续步骤决策的问题
- 给选项而不是开放式提问
- 解释每个决策的 downstream 影响

## 与 Storm 的区别
- Clear 是收敛性的 (帮助聚焦)
- Storm 是发散性的 (帮助拓展)
- 当前上下文中, 你需要收敛而非发散""",

    user_prompt_template="""当前写作需求: {requirement}
已有设定卡数量: {card_count}
待解决问题: {pending_issues}

请输出追问 JSON:

```json
{{
  "context_summary": "对当前进展的简短总结",
  "gaps_identified": ["发现的设定空白"],
  "follow_up_questions": [
    {{
      "question": "追问内容",
      "type": "single_choice | multi_choice | confirm",
      "options": ["选项A", "选项B"],
      "default": "推荐选项",
      "impact": "这个选择会影响哪些后续设定"
    }}
  ],
  "ready_to_proceed": true/false
}}
```

注意:
- follow_up_questions 不超过 3 个
- 如果信息已充分, ready_to_proceed=true
- 只追问"不回答就无法继续"的问题""",

    output_schema={
        "type": "object",
        "properties": {
            "context_summary": {"type": "string"},
            "gaps_identified": {"type": "array", "items": {"type": "string"}},
            "follow_up_questions": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "type": {"type": "string", "enum": ["single_choice", "multi_choice", "confirm"]},
                        "options": {"type": "array", "items": {"type": "string"}},
                        "default": {"type": "string"},
                        "impact": {"type": "string"},
                    },
                    "required": ["question", "type", "options"],
                },
            },
            "ready_to_proceed": {"type": "boolean"},
        },
        "required": ["context_summary", "follow_up_questions", "ready_to_proceed"],
    },
)

SkillRegistry.register(CLEAR_CLARIFY)
