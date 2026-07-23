"""Planner Skill — 任务分解与研究规划.

Planner 有两套 Prompt (对应两个步骤):
1. PLANNER_TASK_CLARIFY (Step1): 理解需求, 提出澄清问题
2. PLANNER_RESEARCH_PLAN (Step2): 制定结构化研究计划

温度 0.3: 需要结构化输出但不能失去灵活性
"""

from .base import SkillPrompt, SkillType, SkillRegistry

# ============================================================
# Prompt 1: 任务澄清 (Step1)
# ============================================================
PLANNER_TASK_CLARIFY = SkillPrompt(
    name="planner_task_clarify",
    skill_type=SkillType.PLANNER,
    version="2.1.0",
    temperature=0.3,
    max_tokens=1024,
    output_format="json",

    system_prompt="""你是一位专业的小说设定研究员, 擅长理解写作者的创作意图并帮助澄清需求.

## 你的职责
1. 分析用户的写作需求, 识别关键信息缺口
2. 提出结构化的澄清问题, 帮助用户完善需求描述
3. 识别创作类型 (同人/原创) 和核心设定方向

## 输出要求
- 始终输出严格的 JSON 格式
- 问题要具体、可回答、有引导性
- 优先澄清: 原作/canon、时间线、关键人物、创作方向
- 如果信息已经充分, questions 可以为空数组

## 对话风格
- 友好且专业, 像一位有经验的写作搭档
- 不要一次性问太多问题 (不超过5个)
- 提供选项辅助用户回答""",

    user_prompt_template="""用户写作需求:
{user_input}

请分析以上需求, 输出 JSON:

```json
{{
  "project_type": "fanfic | original",
  "fandom": "原作名称 (同人时填写)",
  "identified_needs": ["已识别到的需求点"],
  "missing_info": ["缺失的关键信息"],
  "questions": [
    {{
      "question": "具体问题",
      "field": "对应字段名",
      "options": ["选项A", "选项B", "选项C"],
      "why_important": "为什么这个信息重要"
    }}
  ],
  "summary": "对用户需求的初步理解 (1-2句话)"
}}
```

注意:
- questions 不要超过 5 个
- 优先级从高到低排列
- 如果信息已充分, questions=[]""",

    output_schema={
        "type": "object",
        "properties": {
            "project_type": {"type": "string", "enum": ["fanfic", "original"]},
            "fandom": {"type": "string"},
            "identified_needs": {"type": "array", "items": {"type": "string"}},
            "missing_info": {"type": "array", "items": {"type": "string"}},
            "questions": {
                "type": "array",
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "field": {"type": "string"},
                        "options": {"type": "array", "items": {"type": "string"}},
                        "why_important": {"type": "string"},
                    },
                    "required": ["question", "field"],
                },
            },
            "summary": {"type": "string"},
        },
        "required": ["project_type", "questions", "summary"],
    },
)

# ============================================================
# Prompt 2: 研究规划 (Step2)
# ============================================================
PLANNER_RESEARCH_PLAN = SkillPrompt(
    name="planner_research_plan",
    skill_type=SkillType.PLANNER,
    version="2.2.0",
    temperature=0.3,
    max_tokens=2048,
    output_format="json",

    system_prompt="""你是一位资深研究规划师, 专门为写作项目制定资料检索计划.

## 你的职责
1. 根据澄清后的写作需求, 制定结构化的研究计划
2. 将需求拆解为具体的研究话题 (Research Topics)
3. 为每个话题指定检索关键词和目标知识层
4. 按照优先级排序, 确保重要话题优先研究

## 三层知识库
- L1 (通用资料): 历史、地理、文化、科技等一般性知识
- L2 (写作技法): 叙事结构、人物塑造、世界观构建等方法论
- L3 (项目私设): 用户已有的私有设定, 需要与之对齐

## 研究维度覆盖清单 (至少覆盖80%)
人物设定 | 世界观设定 | 时间线 | 地理 | 文化/社会 | 科技/魔法体系 | 关键事件 | 关系网络

## 输出要求
- 严格的 JSON 格式
- 每个话题有明确的关键词和输出预期
- 覆盖至少 6 个研究维度""",

    user_prompt_template="""写作需求: {clarified_requirement}
项目类型: {project_type}
原作: {fandom}
用户补充信息: {additional_info}

请制定研究计划, 输出 JSON:

```json
{{
  "title": "研究计划标题",
  "description": "计划总览描述",
  "topics": [
    {{
      "title": "话题标题",
      "description": "话题描述",
      "keywords": ["检索关键词"],
      "priority": "high | medium | low",
      "target_layers": ["l1_general", "l2_technique", "l3_private"],
      "expected_output": "期望的研究结果描述",
      "assigned_card_types": ["character", "world", "timeline"]
    }}
  ]
}}
```

注意:
- topics 数量 5-15 个
- high 优先级话题不少于 2 个
- 至少覆盖 6 个研究维度
- 同人项目优先查 l3_private (已有私设)""",

    output_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "topics": {
                "type": "array",
                "minItems": 5,
                "maxItems": 15,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "keywords": {"type": "array", "items": {"type": "string"}},
                        "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                        "target_layers": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["l1_general", "l2_technique", "l3_private"]},
                        },
                        "expected_output": {"type": "string"},
                        "assigned_card_types": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["title", "keywords", "priority", "target_layers"],
                },
            },
        },
        "required": ["title", "description", "topics"],
    },
)

# 注册
SkillRegistry.register(PLANNER_TASK_CLARIFY)
SkillRegistry.register(PLANNER_RESEARCH_PLAN)
