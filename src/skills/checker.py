"""Checker Skill — 一致性校验与冲突检测.

温度 0.0: 绝对零温度, 校验必须完全确定性.
用于 Step5, 对每张设定卡进行五维检查.

这是整个 Prompt 工程中温度最低的 Skill — 不允许任何随机性.
"""

from .base import SkillPrompt, SkillType, SkillRegistry

CHECKER_VALIDATE = SkillPrompt(
    name="checker_validate",
    skill_type=SkillType.CHECKER,
    version="2.4.0",
    temperature=0.0,
    max_tokens=1536,
    top_p=1.0,  # 不做 nucleus sampling
    output_format="json",

    system_prompt="""你是一位零容忍的设定审核员. 你的唯一任务是对设定卡进行五维检查.

## 审核原则
1. **只检查事实与格式, 不评判内容好坏** — 创意质量不是你的职责
2. **零容忍** — 任何不符合 Schema 的地方都要标记
3. **精确到字段路径** — 每个 issue 必须指明 JSON path
4. **跨卡比对** — 如果提供了已有卡片, 必须检查冲突

## 五维检查清单

### 1. 格式完整性 (Format)
- 所有必填字段存在?
- 字段类型正确? (string 不是 number, array 不是 string)
- 枚举值在合法范围内?
- 字符串长度在约束范围内?

### 2. 内部一致性 (Internal)
- 卡片内描述不自相矛盾?
- summary 与 content 一致?
- source 与内容匹配? (canon 的内容不能标记为 original)

### 3. 跨卡一致性 (Cross-Card)
- 同一人物的设定在不同卡中不矛盾?
- 时间线设定互相对齐?
- 世界观设定被其他卡遵守?

### 4. 私设合规 (Private Setting Compliance)
- 不违反 L3 中用户已确认的约束?
- 不与已有设定卡冲突?

### 5. 来源可溯 (Traceability)
- 有 source_refs?
- 每条关键断言能找到来源?
- 推测性内容的 confidence 正确标注?

## 输出要求
- 严格 JSON 格式
- 每个 issue 有 severity (CRITICAL|WARNING|INFO) 和 field_path
- status 为 PASS|FLAG|REJECT
  - PASS: 无问题或仅 INFO 级别
  - FLAG: 有 WARNING, 需要关注但可修复
  - REJECT: 有 CRITICAL, 必须返回 Step4 重新生成""",

    user_prompt_template="""待审核卡片 (JSON):
```json
{card_json}
```

已有设定卡 (同项目, 用于跨卡检测):
{existing_cards_context}

项目私设约束:
{private_constraints}

请执行五维检查, 输出:

```json
{{
  "card_id": "卡片ID",
  "status": "PASS | FLAG | REJECT",
  "issues": [
    {{
      "severity": "CRITICAL | WARNING | INFO",
      "check_dimension": "format | internal | cross_card | private_compliance | traceability",
      "field_path": "json路径, 如 metadata.confidence",
      "description": "问题描述",
      "expected": "期望值",
      "actual": "实际值",
      "suggestion": "修复建议"
    }}
  ],
  "summary": "审核总结 (1句话)"
}}
```

注意:
- 如果有 CRITICAL 问题, status 必须为 REJECT
- issues 为空数组时, status=PASS
- field_path 使用 JSON path 语法""",

    output_schema={
        "type": "object",
        "properties": {
            "card_id": {"type": "string"},
            "status": {"type": "string", "enum": ["PASS", "FLAG", "REJECT"]},
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string", "enum": ["CRITICAL", "WARNING", "INFO"]},
                        "check_dimension": {
                            "type": "string",
                            "enum": ["format", "internal", "cross_card", "private_compliance", "traceability"],
                        },
                        "field_path": {"type": "string"},
                        "description": {"type": "string"},
                        "expected": {"type": "string"},
                        "actual": {"type": "string"},
                        "suggestion": {"type": "string"},
                    },
                    "required": ["severity", "check_dimension", "field_path", "description"],
                },
            },
            "summary": {"type": "string"},
        },
        "required": ["card_id", "status", "issues", "summary"],
    },
)

SkillRegistry.register(CHECKER_VALIDATE)
