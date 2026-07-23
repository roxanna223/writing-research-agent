# 同人/原创写作资料辅助Agent — 系统架构文档

> 版本：V1.0 | 日期：2026-07-23 | 作者：架构团队
>
> 关联文档：[PRD.md](./PRD.md) | [WORKFLOW.md](./WORKFLOW.md)

---

## 1. 架构概览

### 1.1 核心设计原则

| 原则 | 描述 |
|---|---|
| **LLM薄层化** | LLM仅负责需要语义理解的小任务（生成设定卡JSON、检测冲突），不参与确定性逻辑 |
| **确定性优先** | 组装、路由、校验等环节全部使用规则引擎，保证100%可复现 |
| **关注点分离** | 7个Skill独立封装，通过LangGraph状态机编排，互不耦合 |
| **分层RAG** | L1通用资料、L2写作技法、L3项目私设，层次间物理隔离 |

### 1.2 系统分层架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │  Chat UI    │  │  SettingCard │  │  SettingPackage Viewer   │   │
│  │  (对话交互)  │  │  Editor      │  │  (设定包预览+下载)        │   │
│  └──────┬──────┘  └──────┬───────┘  └───────────┬──────────────┘   │
│         │                │                      │                   │
├─────────┼────────────────┼──────────────────────┼───────────────────┤
│         │       API GATEWAY (RESTful)           │                   │
│         │  POST /projects                       │                   │
│         │  POST /projects/:id/settings           │                   │
│         │  GET  /projects/:id/packages           │                   │
│         │  WS   /projects/:id/workflow           │                   │
├─────────┼───────────────────────────────────────┼───────────────────┤
│         │            ORCHESTRATION LAYER         │                   │
│  ┌──────┴──────────────────────────────────────┴──────────────┐    │
│  │                LangGraph State Machine                      │    │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐│    │
│  │  │Clari-│→│Plan- │→│Resea-│→│Extra-│→│Check-│→│Deliv-││    │
│  │  │ficat-│ │ning  │ │rch   │ │ction │ │ing   │ │ery   ││    │
│  │  │ion   │ │      │ │      │ │      │ │      │ │      ││    │
│  │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘│    │
│  │     │        │        │        │        │        │      │    │
│  │     └────────┴────────┼────────┴────────┴────────┘      │    │
│  │              │        │        │        │               │    │
│  │     (回退)   │  (回退)│ (回退) │ (回退) │  (回退)        │    │
│  │              ▼        ▼        ▼        ▼               │    │
│  │         ┌────────────────────────────┐                  │    │
│  │         │       State Context        │                  │    │
│  │         │  (跨步骤共享状态对象)        │                  │    │
│  │         └────────────────────────────┘                  │    │
│  └──────────────────────┬──────────────────────────────────┘    │
│                         │                                        │
├─────────────────────────┼────────────────────────────────────────┤
│                         │          SKILL LAYER                   │
│  ┌──────────┬──────────┬┴─────────┬──────────┬──────────┐      │
│  │ Planner  │ Clearer  │Researcher│Extractor │ Checker  │      │
│  │ 任务澄清  │ 清晰度检查│ 三层RAG  │ 设定提取  │ 冲突检测  │      │
│  │ 研究规划  │          │          │          │ 去重归类  │      │
│  └─────┬────┴─────┬────┴────┬─────┴────┬─────┴────┬─────┘      │
│        │          │         │          │          │             │
│  ┌─────┴──────────┴─────────┴──────────┴──────────┴─────┐      │
│  │               Formatter (确定性组装引擎)                │      │
│  │         模板选择 → 字段映射 → 规则校验 → 文档渲染       │      │
│  └────────────────────────┬───────────────────────────────┘      │
│                           │                                       │
├───────────────────────────┼───────────────────────────────────────┤
│                           │         DATA LAYER                    │
│  ┌──────────────────┐  ┌─┴───────────┐  ┌────────────────────┐   │
│  │   RAG Engine     │  │ Setting Store│  │   Project Store    │   │
│  │ L1:ChromaDB-1   │  │ PostgreSQL  │  │   PostgreSQL        │   │
│  │ L2:ChromaDB-2   │  │ (SettingCard │  │   (Project + User)  │   │
│  │ L3:ChromaDB-3   │  │  + Package)  │  │                     │   │
│  └────────┬─────────┘  └──────┬───────┘  └──────────┬─────────┘   │
│           │                   │                      │             │
│  ┌────────┴───────────────────┴──────────────────────┴─────────┐  │
│  │                    Vector Index (ChromaDB)                    │  │
│  │  L1: 公开发布资料 (wiki, fanbook, 官方设定集摘要)            │  │
│  │  L2: 写作技法文献 (叙事学、世界观构建、人物塑造)              │  │
│  │  L3: 用户私有设定 (项目级隔离, 可跨项目引用)                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. 各层职责与接口定义

### 2.1 Presentation Layer

**职责**：用户交互界面，不包含业务逻辑。

| 组件 | 职责 |
|---|---|
| Chat UI | 显示工作流进度、Agent消息、澄清问题，接收用户输入 |
| SettingCard Editor | 可视化编辑单张设定卡的字段值 |
| SettingPackage Viewer | 渲染设定包，提供Markdown/JSON下载 |

**接口**：通过API Gateway的REST和WebSocket与后端通信。

### 2.2 API Gateway

**职责**：请求路由、认证、限流、请求/响应格式标准化。

| 端点 | 方法 | 描述 |
|---|---|---|
| `/api/v1/projects` | POST | 创建新项目（触发工作流） |
| `/api/v1/projects/:id` | GET | 获取项目详情+状态 |
| `/api/v1/projects/:id/clarify` | POST | 提交澄清回答 |
| `/api/v1/projects/:id/resolve-conflict` | POST | 提交冲突仲裁决策 |
| `/api/v1/projects/:id/packages` | GET | 获取设定包 |
| `/api/v1/projects/:id/packages/export` | GET | 导出设定包（md/json） |
| `/api/v1/projects/:id/cards` | GET | 列出所有设定卡 |
| `/api/v1/projects/:id/cards/:cardId` | PATCH | 编辑设定卡 |
| `/api/v1/projects/:id/workflow` | WS | 工作流状态订阅（实时推送步骤变更） |

**统一响应格式**（遵循Repository Pattern设计）：

```json
{
  "success": true,
  "data": { /* 业务数据 */ },
  "error": null,
  "meta": { "page": 1, "total": 42 }
}
```

### 2.3 Orchestration Layer

**职责**：工作流状态管理、步骤编排、回退逻辑、人机交互中断控制。

核心组件为**LangGraph StateGraph**，定义详见第3节。

**State Context（跨步骤共享状态）**：

```typescript
interface WorkflowState {
  projectId: string;
  currentStep: StepEnum;
  userInput: string;              // 用户的初始需求描述
  clarificationQA: QAPair[];      // 澄清问答记录
  researchPlan: ResearchPlan;     // 研究规划
  searchResults: LayerResults[];  // 三层检索结果
  settingCards: SettingCard[];    // 提取的设定卡列表
  conflicts: Conflict[];          // 检测到的冲突
  finalPackage: SettingPackage;   // 最终设定包
  errors: WorkflowError[];        // 错误日志
}
```

### 2.4 Skill Layer

**职责**：封装独立的AI能力单元，每个Skill可单独测试、替换和版本管理。

| Skill | 对应Prompt | 输入 | 输出 | 模型要求 |
|---|---|---|---|---|
| Planner | 2套（任务澄清/研究规划） | WorkflowState片段 | 澄清问题列表 / ResearchPlan | 推理能力强(Claude Sonnet/Opus) |
| Clearer | 1套 | 用户回答 | 清晰度评分 + 追问 | 轻量推理(Claude Haiku) |
| Researcher | 1套（含RAG配置） | ResearchPlan | 分层检索结果 | 检索为主，Embedding模型辅助 |
| Extractor | 1套 | 检索结果chunk | SettingCard JSON数组 | 结构化输出强(Claude Sonnet) |
| Checker | 1套 | SettingCard列表 | 冲突列表 + 归类结果 | 逻辑推理(Claude Sonnet) |
| Formatter | 1套（确定性引擎，非LLM） | 校验后SettingCard列表 | SettingPackage | 不调用LLM |

### 2.5 Data Layer

**职责**：持久化存储与检索。

| 存储 | 技术 | 内容 |
|---|---|---|
| Vector DB L1 | ChromaDB Collection `l1-general` | 公开wiki摘要、官方设定 |
| Vector DB L2 | ChromaDB Collection `l2-technique` | 写作技法文档 |
| Vector DB L3 | ChromaDB Collection `l3-private-{projectId}` | 项目私设，物理隔离 |
| Relational DB | PostgreSQL | Project、SettingCard、SettingPackage、User |
| Embedding Model | text-embedding-3-small / bge-large-zh | 中文优化Embedding |

---

## 3. LangGraph状态图设计

### 3.1 状态节点定义

```
                    ┌──────────────┐
                    │   START      │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ clarification│  ← Planner #1 (澄清问题生成)
                    │              │  ← Clearer (清晰度检查)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐  need_more_clarify (←回退, max 5次)
                    │   human_     │
                    │   feedback   │  ← 等待用户回答澄清问题
                    └──────┬───────┘
                           │ confirmed
                    ┌──────▼───────┐
                    │   planning   │  ← Planner #2 (研究规划生成)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   research   │  ← Researcher (三层RAG)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐  research_insufficient (←回退)
                    │  extraction  │  ← Extractor (设定卡提取)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   checking   │  ← Checker (冲突检测+去重+归类)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐  has_conflicts
                    │   human_     │  ← 等待用户仲裁
                    │   arbitrate  │
                    └──────┬───────┘
                           │ resolved
                    ┌──────▼───────┐
                    │   delivery   │  ← Formatter (确定性组装)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │     END      │
                    └──────────────┘
```

### 3.2 转换条件（Conditional Edges）

```python
# LangGraph状态机转换逻辑（伪代码）

def route_after_clarification(state):
    if state.rounds >= MAX_CLARIFICATION_ROUNDS:  # 5轮上限
        return "planning"  # 强制进入规划
    clarity_score = state.clarity_score
    if clarity_score >= CLARITY_THRESHOLD:  # 0.8
        return "planning"
    else:
        return "human_feedback"

def route_after_extraction(state):
    card_count = len(state.setting_cards)
    expected_dimensions = len(state.research_plan.dimensions)
    if card_count == 0 or card_count < expected_dimensions * 0.3:
        return "research"  # 回退：检索不充分
    else:
        return "checking"

def route_after_checking(state):
    unresolved = [c for c in state.conflicts if c.status == "unresolved"]
    if len(unresolved) > 0:
        return "human_arbitrate"
    else:
        return "delivery"

def route_after_arbitration(state):
    # 仲裁后重新checking确认冲突已解决
    return "checking"
```

---

## 4. 数据流图

```
USER INPUT: "写一篇《咒术回战》现代AU同人..."
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP1 CLARIFICATION                                              │
│                                                                  │
│  Input: userInput (raw text)                                     │
│  Process: Planner#1 → 生成澄清问题                                │
│           Clearer → 检查用户回答清晰度                             │
│  Output: clarificationQA[] ← {q, a, clarity_score}               │
│  Skill: Planner (#1) + Clearer                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP2 PLANNING                                                   │
│                                                                  │
│  Input: userInput + clarificationQA[]                            │
│  Process: Planner#2 → 分析需求 → 拆解研究维度 → 生成检索query     │
│  Output: ResearchPlan {                                          │
│    dimensions: [{name, queries[], priority, expected_type}],     │
│    scope: "原作设定考据|AU改编|写作技法",                          │
│    exclude_patterns: []                                          │
│  }                                                               │
│  Skill: Planner (#2)                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP3 RESEARCH                                                   │
│                                                                  │
│  Input: ResearchPlan.dimensions[].queries[]                      │
│  Process: Researcher → 并行检索三层RAG:                           │
│           L1 (通用资料): query → embed → ChromaDB-L1 → top_k     │
│           L2 (写作技法): query → embed → ChromaDB-L2 → top_k     │
│           L3 (项目私设): query → embed → ChromaDB-L3 → top_k     │
│  Output: LayerResults[] ← [{layer, chunks: [{text, source}]}]    │
│  Skill: Researcher                                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP4 EXTRACTION                                                 │
│                                                                  │
│  Input: LayerResults[].chunks[].text                             │
│  Process: Extractor → LLM逐批提取 → SettingCard JSON              │
│           ┌─────────────────────────────────────┐                │
│           │ {                                    │                │
│           │   "id": "card_001",                  │                │
│           │   "category": "世界观规则",          │                │
│           │   "key": "咒力来源",                 │                │
│           │   "value": "咒力来源于负面情绪",     │                │
│           │   "source": "L1@咒术回战wiki§3.2",  │                │
│           │   "confidence": 0.95                 │                │
│           │ }                                    │                │
│           └─────────────────────────────────────┘                │
│  Output: SettingCard[]                                           │
│  Skill: Extractor                                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP5 CHECKING                                                   │
│                                                                  │
│  Input: SettingCard[]                                            │
│  Process: Checker →                                              │
│    Phase A - 冲突检测: 同key不同value → Conflict标记              │
│    Phase B - 去重:      语义相似度>0.9 → 合并保留高置信度         │
│    Phase C - 归类:      按category分组 → 层级排序                 │
│  Output: SettingCard[] (cleaned) + Conflict[]                    │
│  Skill: Checker                                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼ (若有冲突 → 用户仲裁 → 回到Step5)
                             │
┌─────────────────────────────────────────────────────────────────┐
│ STEP6 DELIVERY                                                   │
│                                                                  │
│  Input: SettingCard[] (final, validated)                         │
│  Process: Formatter (确定性组装引擎, 零LLM):                      │
│    Step A - 模板选择: 根据WorkflowType选择模板                    │
│    Step B - 字段映射: cards → 模板占位符                          │
│    Step C - 规则校验: 必填字段完整? 引用完整? 格式合规?            │
│    Step D - 文档渲染: Markdown + JSON双格式                       │
│  Output: SettingPackage {                                        │
│    metadata: {title, createdAt, cardCount, sourceSummary},       │
│    sections: [{heading, cards: SettingCard[]}],                  │
│    relationshipGraph: {...},                                     │
│    sourceIndex: [{source, usedCards}]                            │
│  }                                                               │
│  Skill: Formatter (非LLM)                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    USER GETS SETTING PACKAGE ✓
```

---

## 5. 技术选型决策记录

### 5.1 LLM选型：Claude vs GPT-4o

| 评估维度 | Claude (Anthropic) | GPT-4o (OpenAI) | 决策 |
|---|---|---|---|
| JSON结构化输出能力 | **优秀**（Structured Outputs API原生支持） | 良好（JSON Mode + 严格Schema） | Claude |
| 中文学术/创作领域理解 | **优秀**（中文语料训练充分） | 优秀 | Claude |
| 推理链长度 | **长上下文窗口200K，连贯推理佳** | 128K，推理链偶尔断裂 | Claude |
| 成本 | Sonnet $3/$15 per MTok | GPT-4o $2.5/$10 per MTok | 相当 |
| 工具调用/Function Calling | 优秀 | **优秀** | 相当 |
| Prompt遵循度 | **极高**（对复杂指令遵循好） | 高 | Claude |

**决策**：选择 **Claude Sonnet** 作为主力模型（Extractor、Checker），**Claude Haiku** 用于轻量任务（Clearer）。核心理由是JSON结构化输出的原生支持和中文创作领域的理解深度。

### 5.2 向量数据库选型：ChromaDB vs Pinecone vs Weaviate

| 评估维度 | ChromaDB | Pinecone | Weaviate |
|---|---|---|---|
| 部署方式 | **嵌入式/本地优先** | 仅云托管 | 自托管或云 |
| MVP开发速度 | **极快**（pip install即可） | 中等（需配置云实例） | 中等 |
| 中文Embedding兼容 | **良好** | 良好 | 良好 |
| 成本（MVP阶段） | **零成本** | $70+/月起步 | 中等 |
| 集合隔离能力 | **原生支持多Collection** | 需Namespace模拟 | 原生支持 |

**决策**：选择 **ChromaDB**。MVP阶段嵌入式部署零运维成本，且其多Collection机制天然支持三层RAG的物理隔离（`l1-general`、`l2-technique`、`l3-private-{projectId}`）。

### 5.3 工作流引擎选型：LangGraph vs 自研状态机

| 评估维度 | LangGraph | 自研状态机 |
|---|---|---|
| 开发效率 | **高**（内置checkpoint、中断恢复） | 低（需从零实现） |
| 人机交互支持 | **原生支持interrupt/resume** | 需自行实现 |
| 社区生态 | **活跃**，与LangChain/LangSmith集成 | 无 |
| 灵活性 | 高，支持条件分支和循环 | 高 |
| 学习成本 | 中等 | 低 |

**决策**：选择 **LangGraph**。核心原因是其原生的人机交互中断机制（`interrupt()`）天然匹配工作流中"等待用户澄清""等待仲裁冲突"的场景，避免了自研状态机的大量边界代码。

### 5.4 关系数据库选型：PostgreSQL

选择PostgreSQL而非MongoDB的理由：
- SettingCard与SettingPackage之间存在强关联关系（外键约束、JOIN查询）
- JSONB字段支持灵活的Schema演进，同时保持关系型查询能力
- 成熟的全文搜索能力（`tsvector`），可作为RAG的补充检索通道

---

## 6. 关键设计模式：确定性组装引擎

### 6.1 设计动机

纯LLM端到端生成设定包存在根本性缺陷：
- **随机性**：相同输入每次生成内容不同，设定卡字段可能遗漏或新增
- **幻觉**：LLM可能在组装时"补充"未曾提取的设定
- **格式不稳定**：Markdown结构每次不同，无法可靠解析

### 6.2 实现原理

```
┌──────────────────────────────────────────────────────────────────┐
│              确定性组装引擎 (Formatter Skill)                      │
│                                                                    │
│  输入: SettingCard[] (已校验) + WorkflowType                       │
│                                                                    │
│  ┌──────────┐    ┌──────────────┐    ┌───────────┐    ┌────────┐ │
│  │ Template │ →  │ Field Mapper │ →  │ Rule      │ →  │ Render │ │
│  │ Selector │    │              │    │ Validator │    │ Engine │ │
│  └──────────┘    └──────────────┘    └───────────┘    └────────┘ │
│       │               │                   │               │       │
│       ▼               ▼                   ▼               ▼       │
│  根据类型选      按category映射       检查必填字段     渲染Markdown  │
│  择对应模板      cards到模板槽位      完整性&格式       + JSON      │
│                                                                    │
│  模板示例 (partial):                                               │
│  ┌─────────────────────────────────────────────────┐              │
│  │ # {{project.title}} 设定包                       │              │
│  │                                                  │              │
│  │ ## 世界观规则                                    │              │
│  │ | 设定项 | 设定值 | 来源 |                       │              │
│  │ |--------|--------|------|                       │              │
│  │ {% for card in cards | filter: "category==世界观" %}            │
│  │ | {{card.key}} | {{card.value}} | {{card.source}} |            │
│  │ {% endfor %}                                    │              │
│  └─────────────────────────────────────────────────┘              │
│                                                                    │
│  关键特性:                                                         │
│  · 零LLM调用 — 纯模板引擎 (Jinja2风格) + JS规则函数                │
│  · 同输入必同输出 — 确定性100%                                     │
│  · 模板版本化管理 — 模板更新不改变已有数据                          │
│  · 规则可测试 — 每条校验规则独立单元测试                            │
└──────────────────────────────────────────────────────────────────┘
```

### 6.3 效果对比

| 指标 | 端到端LLM生成 | 确定性组装引擎 |
|---|---|---|
| 生成稳定率 | 50% | **100%** |
| JSON解析成功率 | 40% → (优化后) | **100%（跳过解析）** |
| 格式一致性 | 每次不同 | **完全相同** |
| 幻觉引入率 | 约10-15% | **0%** |

---

## 7. 安全设计

| 层面 | 措施 |
|---|---|
| 认证 | JWT Bearer Token + Refresh Token |
| 授权 | 项目级RBAC（Owner / Editor / Viewer） |
| 数据隔离 | L3私设ChromaDB Collection按`projectId`物理隔离 |
| 输入校验 | API Gateway层Schema校验（Zod/JSON Schema） |
| 速率限制 | 每用户每模型每日调用上限；RAG检索频率限制 |
| LLM输出校验 | Extractor输出JSON Schema校验（重试3次，失败则降级缓存） |

---

## 8. 部署架构

```
┌──────────────────────────────────────────┐
│              Cloudflare CDN              │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────▼───────────────────────┐
│         Nginx (Reverse Proxy + SSL)       │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────▼───────────────────────┐
│         Node.js API Server (:3000)        │
│    ┌──────────────────────────────────┐   │
│    │  Express/Fastify + LangGraph     │   │
│    └──────────────────────────────────┘   │
└──────┬────────────────────┬──────────────┘
       │                    │
┌──────▼──────┐    ┌────────▼──────────┐
│  PostgreSQL │    │  ChromaDB (:8000) │
│  (Primary)  │    │  L1 / L2 / L3     │
└─────────────┘    └───────────────────┘
       │
┌──────▼──────┐
│  Redis      │
│  (Cache +   │
│   Sessions) │
└─────────────┘
```

---

> 本文档与 [PRD.md](./PRD.md)（产品需求）和 [WORKFLOW.md](./WORKFLOW.md)（工作流设计）共同构成项目核心设计文档。三份文档需交叉阅读。
