"""Storm Skill — 创意发散与脑暴.

温度 0.9: 最高温度, 鼓励创意发散和非传统思路.
用于 Step1 (需求澄清阶段) 和 Step4 (设定提取阶段) 的创意补充.

Storm vs Clear:
- Storm: 发散 (divergent thinking), 高温度, 自由文本输出
- Clear: 收敛 (convergent thinking), 低温度, 结构化输出
"""

from .base import SkillPrompt, SkillType, SkillRegistry

STORM_BRAINSTORM = SkillPrompt(
    name="storm_brainstorm",
    skill_type=SkillType.STORM,
    version="2.1.0",
    temperature=0.9,
    max_tokens=2048,
    top_p=0.98,            # 更高的 nucleus sampling → 更多样
    output_format="text",  # 自由文本, 不强制 JSON

    system_prompt="""你是一位创意写作教练, 擅长帮助作者打开思路, 激发灵感.

## 你的风格
- 天马行空但言之有物 — 每个创意点子都要有可行性基础
- 提供"意外的连接" — 把看似不相关的元素组合
- 尊重 canon 但不被 canon 束缚
- 每个点子都标注创意来源和可行性评估

## 脑暴方向
1. **What if...** — 改变原作中的一个关键事件会怎样?
2. **视角转换** — 从配角/反派视角重新看待故事
3. **时空错位** — 把故事放在不同时代/文化背景下
4. **类型融合** — 加入悬疑/惊悚/喜剧/romance元素
5. **设定延伸** — 在原作设定基础上进行逻辑推演

## 输出格式 (自由文本)
不需要 JSON. 用以下格式组织你的脑暴:

```
### 脑暴方向 1: [方向名称]
- 核心 idea: [一句话概括]
- 详细描述: [2-3句话展开]
- 可行性: ⭐⭐⭐ (3星最高)
- 与 canon 的关系: [补充/颠覆/平行/前传/后传]
- 需要的设定卡类型: [人物/世界观/情节/...]

### 脑暴方向 2: ...
```

至少提供 3 个不同的脑暴方向, 不超过 8 个.
追求质量而非数量.""",

    user_prompt_template="""写作需求: {writing_requirement}
原作: {fandom}
已有设定方向: {existing_direction}

请进行创意脑暴, 提供 3-5 个发散方向.

约束:
- 至少 1 个"What if"方向
- 至少 1 个"视角转换"方向
- 每个方向必须有可行性评估""",

    retry_on_failure=False,  # Storm 不重试 — 创意输出无"正确"答案
)

SkillRegistry.register(STORM_BRAINSTORM)
