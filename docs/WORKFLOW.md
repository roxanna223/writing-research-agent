# 同人/原创写作资料辅助Agent — 6步工作流详细设计

> 版本：V1.0 | 日期：2026-07-23 | 作者：工作流设计团队
>
> 关联文档：[PRD.md](./PRD.md) | [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 1. 工作流总览

### 1.1 六步流水线

```
用户输入 ──→ [S1 任务澄清] ──→ [S2 研究规划] ──→ [S3 资料检索]
                                                    │
                                                    ▼
用户交付 ←── [S6 设定交付] ←── [S5 设定整理] ←── [S4 设定提取]
   │                                  │
   └──────── 可复用设定包 ────────────┘
```

### 1.2 全局状态定义

所有步骤共享同一个 `WorkflowState` 对象（见 [ARCHITECTURE.md 第2.3节](./ARCHITECTURE.md#23-orchestration-layer)）。每个步骤从State中读取前序步骤的输出，并将自身产出写入State。

### 1.3 步骤速览

| 步骤 | 名称 | Skill(s) | 是否有LLM | 是否有人机交互 |
|---|---|---|---|---|
| S1 | 任务澄清 | Planner #1 + Clearer | 是 | **是**（澄清问答） |
| S2 | 研究规划 | Planner #2 | 是 | 否 |
| S3 | 资料检索 | Researcher | 否（Embedding检索） | 否 |
| S4 | 设定提取 | Extractor | 是 | 否 |
| S5 | 设定整理 | Checker | 是 | **是**（冲突仲裁） |
| S6 | 设定交付 | Formatter | **否（确定性引擎）** | 否 |

---

## 2. 各步骤详细设计

---

### Step 1 — 任务澄清 (Clarification)

#### 2.1.1 概述

用户的需求描述往往模糊、不完整或存在内在矛盾。任务澄清步骤通过主动反问，将模糊需求转化为可执行的研究任务。

#### 2.1.2 输入

| 字段 | 类型 | 来源 | 描述 |
|---|---|---|---|
| `state.userInput` | string | 用户在Chat UI提交 | 原始需求描述，例如"我要写一个XX同人" |

#### 2.1.3 Skill调用链

```
Planner #1 (澄清问题生成)
    │
    │ 输入: userInput
    │ Prompt: "你是一个写作研究规划助手。用户描述了一个写作项目需求。
    │         请分析需求的模糊之处，生成3-5个澄清问题..."
    │ 输出: ClarificationQuestion[]
    │
    ▼
[用户回答]
    │
    ▼
Clearer (清晰度检查)
    │
    │ 输入: 用户回答
    │ Prompt: "评估以下回答的清晰度和完整性。对每个维度的清晰度打分(0-1)..."
    │ 输出: {clarityScore: float, needMoreClarification: bool, followUp: Q[]}
    │
    ▼
判定是否继续澄清
```

#### 2.1.4 输出

| 字段 | 类型 | 描述 |
|---|---|---|
| `state.clarificationQA` | QAPair[] | 澄清问答对列表 |
| `state.clarityScore` | float | 综合清晰度评分 (0.0-1.0) |

单条QAPair的Schema：

```json
{
  "round": 1,
  "question": "现代AU是指完全去除咒术改为科技体系，还是保留咒术但设定在当代？",
  "answer": "保留咒术体系，但时间设定在2024年东京",
  "clarityScore": 0.9
}
```

#### 2.1.5 触发条件

- 首次：用户提交初始需求后自动触发
- 回退触发：来自S2的 `research_scope_too_broad` 回退信号

#### 2.1.6 退出条件

- **正常退出**：`clarityScore >= 0.8`
- **强制退出**：`state.clarificationQA.length >= 5`（5轮上限，防止死循环）
- 强制退出时，Agent输出提示："为避免过度追问，我将基于现有信息进行规划，标注为'待确认'的设定项您可以在后续编辑中补充。"

#### 2.1.7 异常处理

| 异常场景 | Fallback策略 |
|---|---|
| 用户回答极短（"随便""都可以"） | Clearer标记低分+提示用户"具体的设定偏好会让最终设定包更贴合您的需求" |
| 用户完全不回答 | 3轮超时后强制退出，按"通用默认设定"进入S2 |
| Planner输出格式异常 | 重试1次，仍失败则使用固定模板问题（"作品名称？AU类型？角色偏好？"） |

---

### Step 2 — 研究规划 (Research Planning)

#### 2.2.1 概述

Planner #2 根据澄清后的需求，生成结构化的研究计划（ResearchPlan），明确需要研究的维度和每个维度的检索策略。

#### 2.2.2 输入

| 字段 | 类型 | 来源 |
|---|---|---|
| `state.userInput` | string | S0初始 |
| `state.clarificationQA` | QAPair[] | S1输出 |

#### 2.2.3 处理逻辑

```
Planner #2 Prompt核心指令：
1. 识别写作类型：同人（需指定原作）/ 原创（需指定世界观类型）
2. 拆解研究维度：
   - 同人类型必须包含：原作设定考据、AU改编方向、人物性格锚点
   - 原创类型必须包含：世界观规则、势力/组织、历史年表
3. 每个维度生成2-4个具体检索query
4. 标记每个维度的优先级 (HIGH/MEDIUM/LOW)
5. 指定期望的设定卡类别和数量范围
```

#### 2.2.4 输出：ResearchPlan Schema

```json
{
  "projectType": "fanfiction_au",
  "originalWork": "咒术回战",
  "auType": "现代保留咒术",
  "dimensions": [
    {
      "id": "dim_001",
      "name": "原作咒术体系考据",
      "priority": "HIGH",
      "queries": [
        "咒术回战 咒力体系 设定",
        "咒术回战 咒术师等级制度",
        "咒术回战 领域展开 规则"
      ],
      "expectedCards": {
        "categories": ["世界观规则", "能力体系"],
        "countRange": [5, 10]
      }
    },
    {
      "id": "dim_002",
      "name": "现代AU改编案例",
      "priority": "MEDIUM",
      "queries": [
        "同人写作 AU设定 现代背景保留奇幻元素 方法论",
        "咒术回战 现代AU 同人设定 参考"
      ],
      "expectedCards": {
        "categories": ["写作技法", "改编案例"],
        "countRange": [2, 5]
      }
    }
  ],
  "excludePatterns": ["动画原创剧情", "未确认的粉丝理论（标注conflict的）"],
  "scopeNotes": "仅限原作漫画1-27卷和官方Fanbook设定"
}
```

#### 2.2.5 触发条件

- S1正常退出后自动触发
- S3回退触发（`research_insufficient`）

#### 2.2.6 退出条件

- ResearchPlan生成成功，`dimensions.length > 0`
- 若生成失败（JSON解析失败），重试1次；仍失败则使用fallback规划（默认研究维度）

#### 2.2.7 回退逻辑：向S1回退

当Planner判断需求仍然过于模糊（ResearchPlan维度数 < 2 或所有维度优先级皆为LOW）时，回退到S1请求进一步澄清，触发条件为 `research_scope_too_broad`。

---

### Step 3 — 资料检索 (Research)

#### 2.3.1 概述

Researcher根据ResearchPlan中的queries，在三层RAG知识库中并行检索，返回分层标注的检索结果。

#### 2.3.2 输入

| 字段 | 类型 | 来源 |
|---|---|---|
| `state.researchPlan.dimensions[].queries[]` | string[] | S2输出 |

#### 2.3.3 三层RAG检索策略

```
对于每个 dimension:
  对于每个 query:
    ┌─────────────────────────────────────────────────────────┐
    │              并行检索 (Promise.all)                      │
    │                                                          │
    │  query ──→ embed ──→ ChromaDB-L1 ──→ topK=5 (通用资料)  │
    │  query ──→ embed ──→ ChromaDB-L2 ──→ topK=3 (写作技法)  │
    │  query ──→ embed ──→ ChromaDB-L3 ──→ topK=3 (项目私设)  │
    │                                                          │
    │  L3查询条件: state.projectId → l3-private-{projectId}   │
    │  若项目无历史私设，L3返回空数组                              │
    └─────────────────────────────────────────────────────────┘
```

**分层权重策略**：

| 层级 | 相似度阈值 | Top-K | 作用 |
|---|---|---|---|
| L1 通用资料 | ≥ 0.65 | 5 | 提供原作事实和基础设定 |
| L2 写作技法 | ≥ 0.60 | 3 | 提供方法和案例参考 |
| L3 项目私设 | ≥ 0.50 | 3 | 提供用户历史设定，优先级最高 |

**L3优先规则**：当L3返回结果时，标记 `l3_override: true`，在S4提取和S5冲突检测中L3设定具有仲裁优先权。

#### 2.3.4 输出

```json
{
  "dimensionResults": [
    {
      "dimensionId": "dim_001",
      "resultsByLayer": {
        "L1": [
          {
            "chunkId": "l1_0042",
            "text": "咒力是咒术师和咒灵使用的能量...",
            "source": "咒术回战wiki§战斗体系",
            "similarity": 0.87
          }
        ],
        "L2": [],
        "L3": [
          {
            "chunkId": "l3_prior_001",
            "text": "本项目中咒力基因突变为隐性遗传...",
            "source": "l3-private-proj_001@历史设定包v1",
            "similarity": 0.72,
            "l3_override": true
          }
        ]
      }
    }
  ],
  "summary": {
    "totalChunks": 42,
    "l1Count": 30,
    "l2Count": 8,
    "l3Count": 4,
    "dimensionsCovered": 3,
    "dimensionsUncovered": 0
  }
}
```

#### 2.3.5 触发条件

- S2正常退出后自动触发
- S4回退触发（`research_insufficient`）

#### 2.3.6 退出条件

- 所有维度至少返回1条结果 → 正常进入S4
- 某个维度返回0条结果 → 标记该维度为 `uncovered`，仍进入S4（旁路）
- 全部维度返回0条 → 触发 `research_insufficient`，回退到S2重新规划或调整检索策略

#### 2.3.7 异常处理

| 异常场景 | Fallback策略 |
|---|---|
| Embedding服务不可用 | 降级为BM25关键词检索（PostgreSQL full-text search） |
| ChromaDB某层超时(>5s) | 该层返回空，不影响其他层 |
| 检索结果全为低相似度(<0.5) | 扩大topK到10，降低阈值到0.4重试 |
| L1/L2/L3全部超时 | 返回空结果，触发S2回退（可能query不匹配知识库内容） |

---

### Step 4 — 设定提取 (Extraction)

#### 2.4.1 概述

Extractor将检索到的非结构化文本chunk，通过LLM逐批提取为结构化的SettingCard（单张小JSON）。这是LLM参与的最关键步骤，也是输出质量控制的核心节点。

#### 2.4.2 输入

| 字段 | 类型 | 来源 |
|---|---|---|
| `state.searchResults.dimensionResults[].resultsByLayer` | LayerResults | S3输出 |

#### 2.4.3 处理逻辑

```
将检索结果按dimension分批（每批最多10个chunk，避免context过长）：

for each batch:
  1. 拼接chunk文本为context block（标注每段的layer+source）
  2. 调用 Extractor Prompt:
     "你是一个设定提取引擎。从以下研究资料中，提取写作设定项。
      对每条设定，输出一个JSON对象，包含:
      - category: 设定的分类（世界观规则|人物设定|能力体系|历史事件|...）
      - key: 设定项名称
      - value: 设定内容（保持原文表述，不做推断）
      - source: 来源标注（包含layer和具体出处）
      - confidence: 置信度（0.0-1.0，基于信息来源的权威性）

      重要规则:
      1. 只提取明确陈述的设定，不推断、不补充、不创作
      2. 如果同一设定在多个来源中出现，L3优先级最高，标注primary_source
      3. 输出格式必须是严格的JSON数组
      4. 每张卡片一个独立设定项"

  3. 解析LLM输出的JSON
  4. JSON Schema校验（失败则重试1次）
  5. 去批次内重复（基于 key + category 的hash）
  6. 注入 settingCardId（uuid）
```

#### 2.4.4 输出：SettingCard Schema

```json
{
  "id": "card_a1b2c3d4",
  "category": "世界观规则",
  "key": "咒力来源",
  "value": "咒力来源于人类负面情绪的积累与释放",
  "source": {
    "primary": "L1@咒术回战wiki§战斗体系",
    "secondary": ["L3@历史设定包v1"],
    "layerPriority": "L3"
  },
  "confidence": 0.95,
  "metadata": {
    "extractedAt": "2026-07-23T10:30:00Z",
    "dimensionId": "dim_001",
    "batchNumber": 1
  }
}
```

#### 2.4.5 触发条件

- S3正常退出后自动触发

#### 2.4.6 退出条件

- 至少提取到 `dimensions.length * 1` 张设定卡 → 进入S5
- 提取卡片数为0 → 触发 `research_insufficient`，回退到S3（扩大检索范围重试）
- 提取卡片数远低于预期（< `expectedCards.countRange[0] * 0.3`） → 同样回退到S3

#### 2.4.7 LLM输出校验策略

```
┌───────────────────────────────────────────────┐
│          Extractor 输出校验流水线               │
│                                                │
│  LLM输出 ──→ JSON.parse()                      │
│                │ 失败 → 重试(1次) ──→ 仍失败    │
│                │                     → 降级缓存 │
│                ▼ 成功                           │
│             JSON Schema校验                     │
│                │ 失败 → 逐条修复(移除非法字段)   │
│                ▼ 成功                           │
│             语义去重                            │
│                │                                │
│                ▼                                │
│          SettingCard[]                         │
└───────────────────────────────────────────────┘
```

此校验流水线是JSON解析成功率从40%提升至90%的关键机制。

---

### Step 5 — 设定整理 (Checking)

#### 2.5.1 概述

Checker对提取的原始设定卡进行三阶段处理：冲突检测、去重合并、分类排序。当检测到设定冲突时，中断工作流请求用户仲裁。

#### 2.5.2 输入

| 字段 | 类型 | 来源 |
|---|---|---|
| `state.settingCards` | SettingCard[] | S4输出 |

#### 2.5.3 三阶段处理

**阶段A：冲突检测**

```
Checker Prompt (Phase A):

"审查以下设定卡片列表，检测冲突：
 1. 语义冲突：同category + 同key + 不同value → 标记为CONFLICT
 2. 层级冲突：L3私设与L1通用资料矛盾 → L3优先，但需标注 'L1-L3-MISMATCH'
 3. 逻辑冲突：设定A隐含了与设定B矛盾的推论 → 标记为IMPLIED_CONFLICT

 输出冲突列表，每个冲突包含:
 - conflictId, type (SEMANTIC|LAYER|IMPLIED)
 - cards: [cardA_id, cardB_id] (冲突双方)
 - description: 冲突描述
 - suggestion: 建议解决方案"

对每对语义冲突：
 计算冲突无法自动解决 → 标记为 'unresolved' → 请求用户仲裁
```

**阶段B：去重合并**

```
对语义相似度 ≥ 0.9 的卡片对：
  - 若来自同一source → 删除重复，保留先提取的
  - 若来自不同source → 合并source列表，保留高confidence的value
  - 若来自不同layer（同一设定L1和L3都有）→ 保留L3版本，标注L1为secondary source
```

**阶段C：分类排序**

```
按预定义类别层级排序：
1. 世界观规则
2. 能力体系
3. 人物设定
4. 势力组织
5. 历史事件
6. 地理场景
7. 文化习俗
8. 关键道具

同类别内：按priority（来自ResearchPlan）降序 → 按confidence降序
```

#### 2.5.4 输出

| 字段 | 类型 | 描述 |
|---|---|---|
| `state.settingCards` | SettingCard[] | 清洗后的设定卡列表（去重、归类） |
| `state.conflicts` | Conflict[] | 待仲裁的冲突列表 |

Conflict Schema：

```json
{
  "conflictId": "conf_001",
  "type": "LAYER",
  "cards": ["card_0012", "card_0038"],
  "description": "咒力来源设定冲突：L1通用资料标注咒力源自负面情绪，L3用户历史私设标注源自基因突变",
  "suggestion": "建议选择L3私设（用户设定优先）或标注为'本作采用基因突变设定'",
  "status": "unresolved"
}
```

#### 2.5.5 触发条件

- S4正常退出后自动触发
- 用户仲裁完成后回退触发（重新检查冲突是否已解决）

#### 2.5.6 退出条件

- **无冲突或所有冲突已仲裁** → 正常进入S6
- **存在未解决的冲突** → 中断，等待用户仲裁

#### 2.5.7 人机交互：冲突仲裁

```
Agent 呈现冲突:
┌─────────────────────────────────────────────────────────┐
│ ⚠️ 检测到 2 个设定冲突，需要您的决策：                     │
│                                                          │
│ 冲突 #1：咒力来源                                        │
│ ┌──────────────────────────────────────────────────┐    │
│ │ 版本A (L1-通用)：咒力来源于人类负面情绪           │    │
│ │ 版本B (L3-私设)：咒力来源于基因突变               │    │
│ │                                                   │    │
│ │ ○ 采用版本A（原作设定）                           │    │
│ │ ● 采用版本B（我的私设）                           │    │
│ │ ○ 两者并存，分情况适用                            │    │
│ └──────────────────────────────────────────────────┘    │
│                                                          │
│ 冲突 #2：五条悟·战斗力定位                                │
│ ...                                                      │
│                                                          │
│ [确认决策]                                               │
└─────────────────────────────────────────────────────────┘

用户提交决策 → Checker重新运行(仅Phase A) → 确认全部解决 → 进入S6
```

#### 2.5.8 异常处理

| 异常场景 | Fallback策略 |
|---|---|
| Checker发现冲突数量 > 20 | 按优先级排序，仅展示TOP 10冲突，其余自动采用L3 or L1（保守策略） |
| 用户长时间未仲裁(>5分钟) | 自动采用保守策略：L3优先于L1（私设优先），等待用户后续手动修改 |
| Checker自身判断矛盾（A-B冲突、B-C冲突、A-C不冲突） | 标记三角冲突，全部提请用户决策 |

---

### Step 6 — 设定交付 (Delivery)

#### 2.6.1 概述

Formatter（确定性组装引擎）将校验通过的设定卡拼装成最终的SettingPackage。**此步骤完全不由LLM参与**，使用模板引擎+规则函数保证100%确定性输出。

#### 2.6.2 输入

| 字段 | 类型 | 来源 |
|---|---|---|
| `state.settingCards` | SettingCard[] | S5输出（已清洗、无冲突） |
| `state.researchPlan` | ResearchPlan | S2输出（用于章节结构） |
| `state.projectId` | string | 全局 |
| `state.userInput` | string | S0初始（用于设定包标题） |

#### 2.6.3 组装流程（纯确定性的4步流水线）

```
Step A — 模板选择
  │
  │ 基于 state.researchPlan.projectType 选择模板:
  │  · fanfiction_au → template/au-fanfic.md
  │  · fanfiction_canon → template/canon-fanfic.md
  │  · original_fantasy → template/original-fantasy.md
  │  · ... (可扩展)
  │
  ▼
Step B — 字段映射
  │
  │ 遍历模板占位符，将SettingCard按category分组填入:
  │
  │ 模板占位符语法:
  │ {{project.title}}          → 从userInput智能摘要
  │ {{section:世界观规则}}      → filter cards by category
  │ {{card.key}}               → 具体字段值
  │ {{card.value}}             → 具体字段值
  │ {{card.source.primary}}    → 来源标注
  │ {{metadata.cardCount}}     → 统计值
  │
  ▼
Step C — 规则校验
  │
  │ 校验规则（纯函数，可单元测试）:
  │  1. 必填section非空: 每个模板section至少应有1张card
  │  2. 来源完整性: 每张card的source.primary非空
  │  3. 置信度阈值: confidence < 0.6的card标注"(待验证)"
  │  4. 引用完整性: 同设定包内card间的交叉引用有效
  │
  ▼
Step D — 文档渲染
  │
  │ 生成双格式输出:
  │  1. Markdown (渲染为完整文档)
  │  2. JSON (结构化机器可读格式)
  │ 存储到PostgreSQL settings_packages表
  │
  ▼
SettingPackage 就绪
```

#### 2.6.4 输出：SettingPackage Schema

```json
{
  "id": "pkg_7f8a9b0c",
  "projectId": "proj_123",
  "version": 1,
  "title": "《咒术回战》现代AU同人设定包",
  "createdAt": "2026-07-23T10:35:00Z",
  "templateId": "fanfiction_au_v2",
  "summary": {
    "totalCards": 28,
    "categories": ["世界观规则", "能力体系", "人物设定", "势力组织"],
    "sourceLayers": {"L1": 18, "L2": 4, "L3": 6},
    "conflictResolved": 2,
    "lowConfidenceCards": 3
  },
  "sections": [
    {
      "heading": "世界观规则",
      "cards": [ /* SettingCard[] */ ]
    },
    {
      "heading": "能力体系",
      "cards": [ /* SettingCard[] */ ]
    }
  ],
  "sourceIndex": [
    {
      "source": "咒术回战wiki§战斗体系",
      "usedInCards": ["card_0012", "card_0015"],
      "layer": "L1"
    }
  ],
  "downloads": {
    "markdown": "/api/v1/projects/proj_123/packages/export?format=md",
    "json": "/api/v1/projects/proj_123/packages/export?format=json"
  }
}
```

#### 2.6.5 触发条件

- S5正常退出后自动触发（所有冲突已解决）

#### 2.6.6 退出条件

- 组装成功 → 工作流整体完成
- 模板缺失（未知projectType） → 降级使用通用模板 `template/default.md`

#### 2.6.7 异常处理

| 异常场景 | Fallback策略 |
|---|---|
| 某section映射后为空（0张card） | 渲染为"（此分类无提取到的设定，您可手动补充）" |
| 模板渲染引擎异常 | 降级为纯JSON输出（跳过Markdown渲染） |
| 存储失败（DB不可写） | 直接在响应流中返回完整SettingPackage JSON（不持久化） |

---

## 3. 步骤间数据契约

### 3.1 契约图

```
S1 ──── clarificationQA[] ────→ S2
S2 ──── researchPlan ──────────→ S3
S3 ──── searchResults ─────────→ S4
S4 ──── settingCards[] ────────→ S5
S5 ──── settingCards[](clean) ─→ S6
S5 ──── conflicts[] ───────────→ S5 (仲裁后回退)
```

### 3.2 契约变更策略

- **向前兼容**：新增字段必须有默认值
- **契约版本号**：State对象携带`schemaVersion`，不同版本间有迁移函数
- **契约校验**：每个步骤入口处校验输入Schema（使用Zod），校验失败时标记错误并跳过该步骤

---

## 4. 异常处理总览

### 4.1 分类策略

| 异常类别 | 处理方式 | 示例 |
|---|---|---|
| **可恢复错误** | 重试(最多1次) → 降级 | LLM JSON解析失败、RAG单层超时 |
| **可旁路错误** | 标记跳过 → 继续后续步骤 | 单个dimension检索为空 |
| **需回退错误** | 回退到前序步骤 | 检索全局为空、提取卡片数不足 |
| **阻塞性错误** | 终止工作流 → 通知用户 | 全层RAG不可用、LLM API全局不可用 |

### 4.2 回退矩阵

| 当前步骤 | 可回退到 | 触发条件 |
|---|---|---|
| S2 研究规划 | S1 任务澄清 | 需求仍然过于模糊（维度数<2或全部LOW优先级） |
| S3 资料检索 | S2 研究规划 | 重新规划（修改查询策略） |
| S4 设定提取 | S3 资料检索 | 提取卡片数不足（扩大检索范围或调整阈值） |
| S5 设定整理 | S5 设定整理（自身） | 用户仲裁后重新检查冲突 |
| S5 设定整理 | S4 设定提取 | 冲突大面积出现（>30%卡片涉及冲突），可能提取质量差，重新提取 |

### 4.3 全局超时

| 阶段 | 超时时间 | 超时行为 |
|---|---|---|
| 整体工作流 | 300s | 强制终止，返回已完成的部分结果 + 未完成步骤说明 |
| 单步LLM调用 | 60s | 重试1次，仍超时则跳过该批 |
| 人机交互等待 | 300s | 强制采用保守默认决策，继续流程 |

---

## 5. 循环保护机制

### 5.1 循环检测

LangGraph状态机内置循环计数器，记录每个节点的进入次数。当任一步骤被进入超过如下阈值时触发保护：

| 步骤 | 最大进入次数 | 超限行为 |
|---|---|---|
| S1 任务澄清 | 5 | 强制进入S2 |
| S2 研究规划 | 3 | 使用固定fallback规划 |
| S3 资料检索 | 3 | 使用缓存结果 |
| S4 设定提取 | 3 | 使用历史成功提取模板 |
| S5 设定整理 | 5 | 自动采用保守策略 |
| S6 设定交付 | 2 | 强制输出（跳过可选校验） |

### 5.2 状态快照

每次人机交互中断时（S1澄清等待、S5仲裁等待），系统自动保存WorkflowState快照到PostgreSQL，确保：
- 用户刷新页面后可恢复中断的工作流
- 服务重启后不丢失进行中的任务

---

## 6. Prompt管理策略

### 6.1 8套Prompt清单

| # | Prompt名称 | 所属Skill | 用途 |
|---|---|---|---|
| 1 | `planner-clarify` | Planner #1 | 分析需求模糊点，生成澄清问题 |
| 2 | `planner-plan` | Planner #2 | 生成结构化ResearchPlan |
| 3 | `clearer-check` | Clearer | 检查回答清晰度，决定是否需追问 |
| 4 | `researcher-query` | Researcher | 检索查询改写与扩展 |
| 5 | `extractor-default` | Extractor | 设定卡提取（通用） |
| 6 | `extractor-character` | Extractor | 人物设定卡提取（专项优化） |
| 7 | `checker-conflict` | Checker | 冲突检测与归类 |
| 8 | `formatter-template` | Formatter | 模板选择规则（非LLM，规则集合） |

### 6.2 Prompt版本管理

- 所有Prompt存储在 `prompts/` 目录，Git版本控制
- 每个Prompt头部标注版本号和适用范围
- Prompt变更需经过效果对比测试（新旧Prompt对相同输入的输出对比）

---

> 本文档与 [PRD.md](./PRD.md)（产品需求）和 [ARCHITECTURE.md](./ARCHITECTURE.md)（系统架构）共同构成项目核心设计文档。三份文档需交叉阅读。
