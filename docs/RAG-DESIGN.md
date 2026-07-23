# 分层RAG系统设计文档

> 面向"同人/原创写作资料辅助Agent"项目的三层知识库检索增强生成系统

---

## 目录

1. [设计哲学](#设计哲学)
2. [三层知识库详解](#三层知识库详解)
3. [数据结构设计](#数据结构设计)
4. [检索策略](#检索策略)
5. [私设冲突自动定位](#私设冲突自动定位)
6. [Embedding选型与Chunk策略](#embedding选型与chunk策略)
7. [知识库初始化与增量更新](#知识库初始化与增量更新)
8. [检索质量评估](#检索质量评估)
9. [与Prompt系统的集成](#与prompt系统的集成)

---

## 设计哲学

### 为什么分层？

单层RAG在写作辅助场景下存在三个核心矛盾：

1. **通用性与专业性的矛盾**：百科知识（如"1970年代英国社会"）和写作技法（如"悲剧人物弧光"）的语义空间完全不同，混在一起互相干扰
2. **稳定性与动态性的矛盾**：公共知识需要版本锁定（确保可复现），而用户私设需要实时更新（支持迭代创作）
3. **canon与私设的矛盾**：同人创作中，区分"原作事实"和"同人私设"是核心需求，单层无法实现

三层分离解决了所有这些矛盾。

### 设计原则

| 原则 | 说明 |
|------|------|
| **分层隔离** | 每层独立存储、独立索引、独立检索，避免语义交叉污染 |
| **结果融合** | 检索后统一融合排序，而非在存储层混合 |
| **溯源完整** | 每条检索结果标注来源层和具体文档，支持交叉验证 |
| **增量可控** | L1/L2定期批量更新，L3实时增量，各自独立 |
| **冲突可见** | L3检索结果显式标注与canon的差异，不做隐性覆盖 |

---

## 三层知识库详解

### L1：通用资料 (General Knowledge)

**定位**：提供事实性背景知识，回答"世界是什么样的"

**典型内容**：
| 类别 | 示例内容 | 数据来源 |
|------|---------|---------|
| 历史事实 | 法国大革命时间线、维多利亚时代社会阶层 | Wikipedia, Britannica |
| 地理信息 | 伦敦地铁线路图、喜马拉雅山脉海拔分布 | OpenStreetMap, GeoNames |
| 科学常识 | 人体解剖结构、基础化学知识、物理定律 | 教科书级公开数据 |
| 文化背景 | 日本茶道流程、北欧神话体系 | 文化百科、学术综述 |
| 职业知识 | 医生日常工作流程、程序员技术栈 | 职业百科、行业报告 |
| 日常生活 | 不同国家饮食习惯、学校制度 | 生活百科 |

**使用场景**：
- 同人创作需要了解原作时代背景（如"1990年代英国社会"）
- 原创写作需要真实地理/历史参考（如"中世纪城堡结构"）
- 角色职业设定需要专业知识（如"法医工作流程"）

**为什么单独一层？**
L1的数据量最大（百万级文档），更新频率最低（月级），语义空间偏向事实陈述。与L2的技法指导混合会导致——当你搜索"如何构建魔法系统"时，大量魔法的百科条目（L1）会淹没写作方法论（L2）的结果。

---

### L2：写作技法 (Writing Techniques)

**定位**：提供创作方法论，回答"怎么写"

**典型内容**：
| 类别 | 示例内容 | 数据来源 |
|------|---------|---------|
| 叙事结构 | 三幕结构、英雄之旅、环形叙事 | 写作教材、编剧手册 |
| 人物弧光 | 正面弧光(成长)、反面弧光(堕落)、平面弧光 | 角色设计理论 |
| 世界观构建 | 魔法系统硬/软分类、科幻设定层级 | 世界构建方法论 |
| 对白技巧 | 潜台词设计、角色语音差异化 | 对话写作指南 |
| 节奏控制 | 场景与续章、张弛节奏 | 创意写作教程 |
| 设定体系 | 设定管理方法、设定与情节的关系 | 写作工坊资料 |

**使用场景**：
- 用户需要"让角色的转变更有说服力"→检索人物弧光技法
- 用户需要"设计一套自洽的魔法体系"→检索魔法系统构建方法论
- 用户需要"改善对话写作"→检索对白技巧

**为什么单独一层？**
L2的内容特点：高度结构化（"方法+示例+原则"的三段式）、专业术语密集、不依赖具体作品。与L1混合会导致事实与方法的混淆——当你搜索"魔法"时，你需要的可能是"如何写好魔法系统"（L2），而非"魔法在历史上的记载"（L1）。

---

### L3：项目私设 (Project Private Settings)

**定位**：存储用户项目的私有设定，管理canon与二创的关系，回答"我设定的世界是什么样的"

**典型内容**：
| 类别 | 示例内容 | 来源 |
|------|---------|------|
| 原创角色 | 角色卡、能力、背景故事 | 用户创建 |
| 原创世界观 | 魔法规则、政治体系、地理 | 用户创建 |
| 同人二创设定 | 与原作不同的if线设定 | 用户创建+Agent辅助 |
| Canon标记 | 原作事实的摘要卡片（用于对齐检查） | Agent从公开资料提取 |
| 设定演化历史 | 旧版本设定、废弃设定 | 自动版本管理 |

**使用场景**：
- 新设定与已有设定的一致性检查
- 基于已有设定补全某一部分
- 多角色关系网络的冲突检测
- canon对齐检查（"这个设定是否违背原作？"）

**为什么单独一层？**
L3是系统的核心差异化层。它需要：
- 实时更新（用户每次编辑立即生效）
- 严格的访问控制（不应泄露给其他用户）
- 字段级对比能力（不仅找相似文档，还要找字段级矛盾）
- 与传统RAG的"检索-生成"模式不同，L3更多服务于验证和补全

---

## 数据结构设计

### ChromaDB Collection Schema

每个知识库层对应一个ChromaDB Collection，使用相同的元数据结构但不同的索引策略。

#### 通用文档元数据Schema（所有层共用）

```json
{
  "doc_id": "string (UUID v4)",
  "layer": "L1|L2|L3",
  "category": "string (L1: history|geography|science|culture|... | L2: narrative|character|worldbuilding|dialogue|... | L3: character|world|plot|relationship)",
  "title": "string",
  "source_url": "string|null",
  "source_title": "string|null",
  "content_hash": "string (SHA-256)",
  "chunk_index": "integer",
  "total_chunks": "integer",
  "parent_doc_id": "string|null",
  "created_at": "ISO 8601 datetime",
  "updated_at": "ISO 8601 datetime",
  "version": "integer",
  "language": "zh|en|mixed",
  "quality_score": "float (0.0-1.0)",
  "tags": ["string"],
  "canon_status": "canon|derived|original|null (L3专用)"
}
```

#### L1 Collection: `knowledge_l1_general`

```
collection_name: "knowledge_l1_general"
embedding_function: text-embedding-3-large (OpenAI) 或 bge-large-zh-v1.5 (本地)
distance_metric: cosine

索引策略:
- 主索引: embedding (用于语义搜索)
- 辅助索引: category (用于分类过滤)
- 辅助索引: tags (用于标签过滤)
- 辅助索引: language (用于语言过滤)

Chunk配置:
- chunk_size: 512 tokens
- chunk_overlap: 64 tokens (12.5% overlap)
- 保留文档边界（不在句子中间切分）

为什么512 tokens？
- L1内容以事实陈述为主，每个事实段落通常200-500 tokens
- 512 tokens足够包含一个完整的事实单元（如一个人物的生平段落）
- 较小的chunk提高检索精度，与L1"事实查找"的使用模式匹配
```

#### L2 Collection: `knowledge_l2_techniques`

```
collection_name: "knowledge_l2_techniques"
embedding_function: text-embedding-3-large (OpenAI) 或 bge-large-zh-v1.5 (本地)
distance_metric: cosine

索引策略:
- 主索引: embedding (用于语义搜索)
- 辅助索引: category (用于分类过滤——用户可能只需要"人物弧光"相关技法)
- 关键词索引: 专业术语（如"英雄之旅"、"三幕结构"、"人物弧光"）

Chunk配置:
- chunk_size: 1024 tokens
- chunk_overlap: 128 tokens (12.5% overlap)
- 保留方法-示例-原则的结构完整性

为什么1024 tokens？
- L2内容的结构是"方法论+示例+原则"，每个完整单元通常600-1000 tokens
- 1024 tokens确保一个完整的技法说明不被切碎
- 较大的chunk有利于模型理解技法的完整上下文
```

#### L3 Collection: `knowledge_l3_private`

```
collection_name: "knowledge_l3_private_{project_id}"
embedding_function: text-embedding-3-large (OpenAI) 或 bge-large-zh-v1.5 (本地)
distance_metric: cosine

索引策略:
- 主索引: embedding (用于语义搜索)
- 辅助索引: card_type (character|world|plot|relationship)
- 辅助索引: source (canon|derived|original)
- 辅助索引: name_hash (人物/地点名称的哈希，用于精确匹配)
- 全文索引: name字段的精确文本匹配

Chunk配置:
- 每个设定卡 = 一个chunk（不拆分）
- 为什么不分块？设定卡是原子性的——一张角色卡被切分后，两个分块可能产生矛盾的一致性判断

特殊元数据:
- canon_status: canon|derived|original
  - canon: 来自原作的事实（如"哈利波特的魔杖是冬青木"）
  - derived: 根据canon推导的设定（如"基于哈利的性格推断他对某事的反应"）
  - original: 完全同人原创设定（如"原创角色"或"if线设定"）
- conflicts_with: ["card_id"] (已知与此卡有冲突的卡片ID列表)
- related_cards: ["card_id"] (关联卡片)
- card_version: 设定卡的版本号
```

---

## 检索策略

### 路由决策：何时查哪层？

```
┌─────────────────────┐
│  Planner生成检索规划 │
│  指定每层的查询意图  │
└──────┬──────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│          Researcher 路由矩阵          │
│                                      │
│  查询意图          → 查询层           │
│  ──────────────────────────────────  │
│  "事实背景"        → L1 优先          │
│  "写作方法"        → L2 优先          │
│  "已有设定"        → L3 优先          │
│  "角色信息"        → L1 + L3 混合     │
│  "世界观规则"      → L2 + L3 混合     │
│  "canon事实"       → L1 (canon子集)   │
│  "同人对比"        → L1 + L3 对比      │
└──────────────────────────────────────┘
```

### 多路召回策略

每层使用两路召回，取并集后融合排序：

```
路1: 语义搜索 (Semantic Search)
  - 将查询向量化
  - 在目标层的embedding索引中搜索Top-K_semantic
  - 优势：理解语义，同义词匹配
  - 劣势：可能遗漏精确关键词匹配

路2: 关键词搜索 (Keyword Search / BM25)
  - 对查询分词后执行BM25全文检索
  - 在目标层的关键词索引中搜索Top-K_keyword
  - 优势：精确匹配术语、人名、地名
  - 劣势：不理解语义变体

融合: 加权RRF (Reciprocal Rank Fusion)
  - 语义搜索结果权重: w_semantic = 0.6
  - 关键词搜索结果权重: w_keyword = 0.4
  - RRF公式: score(doc) = Σ w_i / (k + rank_i(doc))
    其中 k = 60 (平滑参数)
  - 取融合后的Top-N作为该层最终结果
```

**为什么语义权重更高(0.6)?**
写作辅助场景中，用户的查询往往不是精确术语匹配（"帮我补充世界观"中的"补充"不是检索关键词），语义理解比关键词匹配更重要。但保留关键词路径(0.4)是为了捕获专有名词（人名、地名、作品名）。

### 跨层融合排序

三层各自返回Top-N后，统一融合：

```
1. 层内去重：基于 content_hash 去重
2. 相关性过滤：relevance_score < threshold 的结果丢弃
   - L1 threshold = 0.5（宽松，L1内容多需要更多候选）
   - L2 threshold = 0.6（适中）
   - L3 threshold = 0.7（严格，私设检索必须高相关）
3. 跨层加权RRF融合：
   - L1 weight = 0.35
   - L2 weight = 0.30
   - L3 weight = 0.35
4. 多样性重排 (MMR, λ=0.7)：
   - 避免返回过多相似文档
   - 在相关性和多样性之间平衡
5. 最终返回 Top-K_final（默认 K=10）
```

**为什么L1和L3权重相等(0.35)?**
这是"外部参考"(L1)和"用户自己的设定"(L3)的平衡。L3内容更个性化但可能不完整，L1内容更全面但可能不适用。等权融合确保用户能同时看到"世界事实"和"我的设定"。

---

## 私设冲突自动定位

### 为什么需要这个？

在同人创作中，最常见的痛点不是"缺少设定"，而是"设定自相矛盾"。一个中型同人项目（5万字以上）通常有50-200条散落的设定。作者自己都记不清"这个角色上次的设定是什么"，更不用说维护一致性了。

### 算法流程

```
输入: 新设定卡 (SettingCard)
输出: 冲突报告 (ConflictReport)

步骤:

1. 新设定向量化
   └── 使用与L3相同的embedding模型将新卡片的 content 字段向量化

2. 在L3中检索Top-k相似设定
   ├── k = 5 (默认)
   ├── 过滤: 同 type 优先（角色与角色比较，世界观与世界观比较）
   └── 过滤: 排除自身（如果是更新已有卡片）

3. 字段级对比 (Field-Level Comparison)
   对每个候选卡片执行:

   3.1 同名人物冲突检测
       规则: name 字段相同（或相似度 > 0.85）但 card_id 不同
       对比字段: personality, background, abilities, appearance
       语义相似度阈值: > 0.7 → 标记为一致, < 0.7 → 标记为潜在冲突
       例子: card_A说"角色内向孤僻"，card_B说"角色热情开朗" → 冲突

   3.2 时间线矛盾检测
       规则: 提取所有含时间信息的设定（年龄、事件日期、先后关系）
       构建时间线图 → 检测循环依赖和矛盾断言
       例子: card_A说"事件X发生在1995年"，card_B说"事件X发生在1997年" → 矛盾
       例子: card_A说"A先于B"，card_B说"B先于A" → 循环矛盾

   3.3 设定覆盖检测 (Setting Override)
       规则: 同一实体（同名+同type）有多个版本
       判断: source=original 的设定是否意图覆盖 source=canon 的设定
       如果不确定意图 → 标记为"潜在覆盖冲突"，需用户确认
       例子: canon说"魔法需要魔杖"，用户私设"无杖魔法广泛存在"
             → 如果用户明确标记为"if线"→ 非冲突
             → 如果用户未标记 → 潜在冲突

   3.4 关系网络一致性检测
       规则: 构建人物关系有向图
       检测: 单向关系是否在对方卡片中对称
       例子: card_A(roleX)的关系字段声称"与roleY是密友"
             card_B(roleY)的关系字段没有提到roleX
             → 不对称关系，低严重度警告

4. 冲突报告生成 (ConflictReport)
   {
     "new_card_id": "string",
     "conflicts": [
       {
         "conflict_type": "name_collision|timeline|override|relationship_asymmetry",
         "severity": "critical|high|medium|low",
         "existing_card_id": "string",
         "field_level_detail": {
           "field": "string",
           "new_value": "string",
           "existing_value": "string",
           "similarity_score": float
         },
         "auto_resolution": "string|null",
         "requires_user_input": boolean
       }
     ],
     "suggestions": [
       {
         "action": "merge|overwrite|keep_both|user_decide",
         "reasoning": "string"
       }
     ]
   }
```

### 冲突严重度分级

| 严重度 | 定义 | 示例 | 自动处理 |
|--------|------|------|---------|
| critical | 逻辑矛盾，物理上不可能 | 同一角色同时出现在两个地点 | 必须人工处理 |
| high | 语义冲突，影响理解 | 角色性格描述完全相反 | 建议人工处理 |
| medium | 细节不一致 | 年龄计算与实际出生年份不符 | 可自动建议修正 |
| low | 风格或命名不一致 | 同一地点拼写不同 | 可自动修正 |

### 冲突检测中embedding的使用

字段级对比不是简单的字符串匹配，而是语义对比：

```
compare_fields(field_a: string, field_b: string) -> similarity_score: float

1. 将两个字段文本分别向量化（使用同一embedding模型）
2. 计算余弦相似度
3. 如果相似度 > 0.85 → 语义一致，无冲突
4. 如果相似度 0.5-0.85 → 灰色地带，标记为低优先级
5. 如果相似度 < 0.5 → 语义不同，可能冲突

为什么用0.85/0.5阈值？
- 0.85：同一事实的不同措辞（如"性格内向"和"不善于社交"）相似度约0.85-0.95
- 0.50：有相关性但含义不同的陈述相似度约0.5-0.7
- 低于0.5：基本无关甚至是相反含义
```

---

## Embedding选型与Chunk策略

### Embedding模型选型

| 模型 | 维度 | 中文支持 | 推荐场景 | 优劣势 |
|------|------|---------|---------|--------|
| **text-embedding-3-large** (OpenAI) | 3072 | 优秀 | 云端部署、高质量需求 | 精度最高，有API成本；维度大可做高效降维 |
| **bge-large-zh-v1.5** (BAAI) | 1024 | 优秀 | 本地部署、数据隐私需求 | 中英文混合效果好，免费，C-MTEB榜首 |
| **bge-m3** (BAAI) | 1024 | 优秀 | 多语言混合场景 | 支持100+语言，适合中英混合同人圈 |
| **jina-embeddings-v3** | 1024 | 良好 | 长文档场景 | 支持8192 token输入，适合不分块的设定卡 |

**推荐方案**：
- 生产环境：`bge-m3` 本地部署（零API成本、数据不出域、中英混合性能优异）
- 快速验证：`text-embedding-3-large` API（无需运维、精度高）

**为什么优先推荐本地模型？**
L3存储用户私设，涉及创作隐私。将用户的同人设定发送给外部embedding服务存在隐私风险。本地embedding彻底消除这一风险。

### Chunk策略决策树

```
文档长度 < 512 tokens (约380个中文字符)?
  ├── 是 → 不分块，整个文档作为一个chunk
  └── 否 → 继续判断

文档类型是"设定卡"(SettingCard)?
  ├── 是 → 不分块（设定卡是原子单元）
  └── 否 → 继续判断

文档类型是"结构化内容"(百科全书条目、写作技法)?
  ├── 是 → 按自然段落边界分块
  │       chunk_size: 512/1024 (L1/L2)
  │       overlap: 12.5%
  │       优先在标题、列表、段落边界处切分
  └── 否 → 按句子边界分块
          chunk_size: 512
          overlap: 10%
          确保不在句子中间切分（使用句号、问号、感叹号作为切分点）
```

**为什么12.5% overlap？**
这是实践中验证的"刚好够"的重叠比例：
- 5% overlap：有些跨chunk边界的语义单元被切断
- 12.5% overlap：绝大多数跨边界语义单元被完整保留在至少一个chunk中
- 25% overlap：冗余过高，检索结果中出现大量重复内容

---

## 知识库初始化与增量更新

### 初始化流程

```
阶段1: L1初始化（通用资料）
  1. 确定初始覆盖范围：
     - 历史：主要文明的历史时间线（中日欧美为核心）
     - 地理：世界主要国家和城市
     - 科学：基础科学概念
     - 文化：主要文化现象和习俗
     - 总量预估：50,000-100,000条文档
  2. 数据源清洗与标准化
  3. 批量embedding（使用队列+并发控制）
  4. 质量抽检（每1000条抽检10条人工评估）
  5. 写入ChromaDB collection knowledge_l1_general

阶段2: L2初始化（写作技法）
  1. 整理核心写作技法体系（约500-2000篇高质量文献）
  2. 人工标注category和tags
  3. 批量embedding
  4. 全量质量审核（L2数据量小，可全量人工审核）
  5. 写入ChromaDB collection knowledge_l2_techniques

阶段3: L3初始化（项目私设）
  1. 项目创建时自动生成空的 knowledge_l3_private_{project_id}
  2. 用户首次使用时可选：
     a. 空白初始化（全新原创项目）
     b. Canon导入（从L1自动提取该作品的canon设定卡作为基线）
     c. 从已有设定文件导入
```

### 增量更新流程

```
L1/L2 增量更新（月度批量）:
  1. 数据源变更检测（爬取/监听）
  2. 新增文档:
     a. 计算 content_hash
     b. 如果hash与已有文档不同 → 新增
     c. 如果hash相同 → 跳过
  3. 修改文档:
     a. 检测到 content_hash 变化
     b. 旧版本标记为 deprecated，新版本写入
     c. 保留旧版本的 embedding 30天（供回滚）
  4. 删除文档:
     a. 标记为 deprecated，不物理删除
     b. 过滤查询时排除 deprecated=True

L3 增量更新（实时）:
  1. 用户通过Agent创建/修改设定卡
  2. 立即计算 embedding 并写入/更新 ChromaDB
  3. 触发冲突检测（后台异步）
  4. 如有冲突 → 在下一次用户交互时展示冲突报告
  5. 版本管理:
     - 每次修改创建新版本
     - 旧版本保留30天
     - 用户可以手动回滚到任意历史版本
```

### 更新触发条件

| 事件 | 触发动作 | 优先级 |
|------|---------|--------|
| 用户新建设定卡 | L3写入 + 冲突检测 | 同步 |
| 用户修改设定卡 | L3更新 + 冲突检测 | 同步 |
| 用户删除设定卡 | L3标记删除 + 关系清理 | 同步 |
| L1数据源有更新 | 月度批量更新队列 | 后台 |
| L2新增技法资料 | 人工审核后批量更新 | 后台 |
| Embedding模型升级 | 全量re-embedding | 计划维护窗口 |

---

## 检索质量评估

### 评估指标

| 指标 | 定义 | 目标值 | 测量方法 |
|------|------|--------|---------|
| **Recall@K** | Top-K结果中包含正确答案的比例 | L1≥0.85, L2≥0.90, L3≥0.95 | 构造测试查询集，标注ground truth |
| **MRR** (Mean Reciprocal Rank) | 第一个正确答案的排名倒数的均值 | ≥0.75 | 同上 |
| **NDCG@10** | 归一化折损累积增益 | ≥0.80 | 需要相关性分级标注（完全相关/部分相关/不相关） |
| **Precision@5** | Top-5中相关结果的比例 | ≥0.70 | 同上 |
| **冲突检测召回率** | 实际存在的冲突中被正确检出的比例 | ≥0.90 | 构造含已知冲突的设定包 |
| **冲突检测精确率** | 报告为冲突的项中真正是冲突的比例 | ≥0.80 | 同上（避免过多假阳性干扰用户） |
| **检索延迟P95** | 95%的检索请求在Xms内完成 | <500ms | 生产环境监控 |
| **结果多样性** (1-MMR内聚度) | 返回结果的内容差异度 | ≥0.60 | 计算返回文档间的平均余弦距离 |

### 评估测试集

```
测试集结构:
├── queries_l1.json  (100个L1查询 + ground truth)
│   格式: {"query": "string", "relevant_doc_ids": ["id1", "id2"]}
├── queries_l2.json  (100个L2查询 + ground truth)
├── queries_l3.json  (100个L3查询 + ground truth)
└── conflict_cases.json (50个已知冲突的设定包)

测试集来源:
- 50%: 从真实用户使用中采样和标注
- 30%: 由领域专家（资深同人写手）构造
- 20%: 合成数据（边界情况压力测试）
```

### 质量监控

```
线上指标看板:
- 检索结果用户采纳率（用户使用了检索结果的哪一条）
- 冲突报告用户确认率（用户确认了多少个冲突）
- 用户手动搜索频率（Agent的结果不够好，用户选择自己搜）
- 平均每会话重试次数

告警阈值:
- Recall@10 < 0.75 持续1小时 → 触发排查
- 检索延迟P95 > 1000ms → 触发扩容
- 冲突检测假阳性率 > 30% → 调整阈值
- 用户手动搜索率 > 20% → 检索策略需要调整
```

---

## 与Prompt系统的集成

### 数据流

```
用户输入
  │
  ▼
Planner (P-01)
  │ 生成 research_plan (含target_layers和search_queries)
  ▼
Researcher (P-03)
  │ 执行分层检索 → 返回 fused_results
  ├──→ L1 返回: 事实性背景知识
  ├──→ L2 返回: 写作技法指导
  └──→ L3 返回: 已有私设（用于对齐和冲突检测）
  │
  ▼
Extractor (P-04) / Storm (P-02a) / Clear (P-02b)
  │ 基于 fused_results 提取设定卡
  │ 使用 L3 结果做冲突预检
  ▼
Checker (P-05)
  │ 完整一致性校验（含L3冲突检测算法）
  ▼
Formatter (P-06)
  │ 格式化交付
  ▼
用户收到设定包
```

### 检索上下文注入格式

当Researcher将结果传递给下游Skill时，使用标准化的上下文注入格式：

```
## L1 通用资料 ({result_count}条)

### [L1-001] {title} | 相关性: {relevance_score}
来源: {source_title} ({source_url})
{content}

### [L1-002] {title} | 相关性: {relevance_score}
...

## L2 写作技法 ({result_count}条)

### [L2-001] {title} | 相关性: {relevance_score}
{content}
...

## L3 项目私设 ({result_count}条)

### [L3-001] {name} | 类型: {type} | 来源: {source} | 冲突状态: {conflict_status}
{content}
已有关联: {related_cards}
已知冲突: {conflicts_with}
...
```

### 与PROMPTS.md的一致性说明

本文档中描述的三层知识库结构对应PROMPTS.md中以下内容：
- Planner (P-01) 的 `target_layers` 字段指定每层查询意图
- Researcher (P-03) 的 `per_layer_results` 和 `fused_results` 字段承载检索结果
- Checker (P-05) 的冲突检测逻辑依赖L3的 `conflicts_with` 元数据和本文档描述的冲突检测算法
- Extractor (P-04) 和 Checker (P-05) 的 `source_document` 字段引用L1/L2的 `doc_id`

与DATA-MODEL.md的一致性说明：
- L3中每张设定卡的数据结构对应DATA-MODEL.md中定义的 SettingCard JSON Schema
- L3的向量化使用 SettingCard.content 字段，元数据使用其他字段
- 冲突检测结果的结构与 SettingCard.conflicts_with 字段对应
