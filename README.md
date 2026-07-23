# 人物写作资料辅助Agent

> **Writing Research Assistant Agent** — 面向同人/原创写作者的结构化资料检索与设定生成助手

## 一句话概述

区别于被动问答的ChatBot，本Agent采用**6步结构化工作流**，从任务澄清到设定交付形成完整闭环，主动引导作者完成写作前期的资料检索与设定整理，输出可复用的**设定包**与**设定卡**。

## 解决的痛点

| 痛点 | 传统方案 | 本Agent方案 |
|------|----------|-------------|
| 资料检索分散 | 多个网站/Wiki/笔记间跳转 | 分层RAG一站式检索 |
| 设定整理低效 | 手动复制粘贴→格式混乱 | 结构化设定卡自动生成 |
| 设定冲突难发现 | 靠人脑记忆 | 私设冲突自动定位 |
| LLM输出不可靠 | 端到端生成，截断/漂移频发 | 确定性组装，稳定率100% |
| 缺乏质量衡量 | 凭感觉判断 | 6维度自动评估 |

## 核心特性

### 🔄 6步结构化工作流

```
用户输入 → Step1任务澄清 → Step2研究规划 → Step3资料检索
         → Step4设定提取 → Step5设定整理 → Step6设定交付 → 设定包+设定卡
```

每一步有明确的输入/输出契约，由专门的Skill驱动，区别于"一问一答"的聊天模式。

### 🎯 7 Skills × 8 Prompt Templates

| Skill | 职责 | 温度 | 输出格式 |
|-------|------|------|----------|
| **Planner** | 任务分解与研究规划 | 0.3 | JSON Plan |
| **Storm** | 创意发散与脑暴 | 0.9 | Free Text |
| **Clear** | 需求澄清与追问 | 0.3 | JSON Questions |
| **Researcher** | 资料检索与摘要 | 0.1 | JSON Results |
| **Extractor** | 结构化设定提取 | 0.1 | JSON Cards |
| **Checker** | 一致性校验与冲突检测 | 0.0 | JSON Report |
| **Formatter** | 设定包格式化组装 | - | Markdown/JSON |

### 📚 分层RAG知识库

```
L1 通用资料 ─── 历史、地理、文化、科学等通用知识
L2 写作技法 ─── 叙事结构、人物塑造、世界观构建等方法论
L3 项目私设 ─── 用户自定义的私有设定，支持冲突自动定位
```

### 📦 设定卡 + 设定包

- **设定卡 (Setting Card)**：最小粒度，一张卡记录一个设定点（人物/世界观/情节/关系）
- **设定包 (Setting Package)**：确定性逻辑从已有卡片组装，稳定率100%

## 技术栈

| 层级 | 技术 | 选型理由 |
|------|------|----------|
| LLM | Claude API (Opus/Sonnet) | 结构化输出能力最强 |
| 框架 | FastAPI + LangGraph | 高性能API + 状态图编排 |
| 向量库 | ChromaDB | 轻量本地部署，适合个人使用 |
| 结构化 | Pydantic + Instructor | 约束生成，JSON解析成功率90%+ |
| Embedding | text-embedding-3-small | 性价比最优 |

## 项目结构

```
a2/
├── README.md
├── docs/
│   ├── PRD.md                  # 产品需求文档
│   ├── ARCHITECTURE.md         # 系统架构文档
│   ├── WORKFLOW.md             # 6步工作流详细设计
│   ├── PROMPTS.md              # 7 Skill + 8 Prompt模板
│   ├── RAG-DESIGN.md           # 分层RAG系统设计
│   ├── DATA-MODEL.md           # 设定包/卡JSON Schema
│   ├── EVALUATION.md           # 6维度评估体系
│   └── BADCASE-ITERATION.md    # 5轮Badcase迭代记录
├── src/
│   ├── models/                 # Pydantic数据模型
│   ├── skills/                 # 8套Prompt模板
│   ├── rag/                    # RAG检索引擎
│   ├── workflow/               # LangGraph工作流
│   └── evaluation/             # 评估模块
└── data/
    ├── knowledge/              # 三层知识库
    │   ├── l1_general/
    │   ├── l2_technique/
    │   └── l3_private/
    ├── cards/                  # 设定卡存储
    └── packages/               # 设定包存储
```

## 效果指标

| 指标 | 迭代前 | 迭代后 |
|------|--------|--------|
| JSON解析成功率 | 40% | **90%** |
| 字段匹配率 | 30% | **85%** |
| 生成稳定率 | 50% | **100%** |
| 综合评分(vs ChatGPT) | - | **4.5/5** |
| 研究维度覆盖率 | - | **100%** |
| 一致性检查命中率 | - | **~75%** |

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化知识库
python src/rag/init_knowledge_base.py

# 运行CLI
python src/main.py

# 运行Web界面
streamlit run src/app.py
```

## 许可证

MIT
