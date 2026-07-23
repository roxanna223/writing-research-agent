"""Researcher Skill — 资料检索查询生成.

温度 0.1: 极低温度, 检索查询需要精确而非创意.
用于 Step3 (资料检索), 将研究话题转化为可执行的检索查询.
"""

from .base import SkillPrompt, SkillType, SkillRegistry

RESEARCHER_QUERY = SkillPrompt(
    name="researcher_query",
    skill_type=SkillType.RESEARCHER,
    version="2.0.0",
    temperature=0.1,
    max_tokens=1024,
    output_format="json",

    system_prompt="""你是一位专业资料研究员, 精通将研究需求转化为精准的检索查询.

## 你的职责
1. 接收研究话题, 生成多角度检索查询
2. 为每个查询指定目标知识层 (L1/L2/L3)
3. 对查询进行去重和优先级排序
4. 识别需要外源搜索的查询 (标记 needs_external=True)

## 检索策略
- L1 (通用资料): 适合事实性查询 — "霍格沃茨的课程设置"
- L2 (写作技法): 适合方法论查询 — "如何写出真实感的校园生活"
- L3 (项目私设): 先检索用户已有的设定 — 避免重复劳动

## 查询生成原则
- 每个话题生成 2-5 个查询 (不同角度)
- 查询要具体、可执行
- 优先使用关键词组合而非自然语言问题
- 标注查询的预期结果类型""",

    user_prompt_template="""研究话题: {topic_title}
话题描述: {topic_description}
目标知识层: {target_layers}
关键词: {keywords}
写作类型: {project_type} (同人/原创)
原作: {fandom}

请生成检索查询, 输出 JSON:

```json
{{
  "topic_id": "话题ID",
  "queries": [
    {{
      "query": "检索查询字符串",
      "target_layer": "l1_general | l2_technique | l3_private",
      "query_type": "keyword | semantic | hybrid",
      "needs_external": true/false,
      "expected_result_type": "事实信息 | 方法论 | 已有设定",
      "priority": "high | medium | low"
    }}
  ],
  "search_strategy": "parallel | sequential | cascade"
}}
```

注意:
- 如果 target_layers 包含 l3_private, 至少生成 1 个 L3 查询
- 同人项目优先查 L3 (已有私设), 原创项目优先查 L1 (通用资料)
- needs_external=true 的查询不要超过 40%""",

    output_schema={
        "type": "object",
        "properties": {
            "topic_id": {"type": "string"},
            "queries": {
                "type": "array",
                "minItems": 2,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "target_layer": {"type": "string", "enum": ["l1_general", "l2_technique", "l3_private"]},
                        "query_type": {"type": "string", "enum": ["keyword", "semantic", "hybrid"]},
                        "needs_external": {"type": "boolean"},
                        "expected_result_type": {"type": "string"},
                        "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                    },
                    "required": ["query", "target_layer", "query_type", "needs_external"],
                },
            },
            "search_strategy": {"type": "string", "enum": ["parallel", "sequential", "cascade"]},
        },
        "required": ["topic_id", "queries", "search_strategy"],
    },
)

SkillRegistry.register(RESEARCHER_QUERY)
