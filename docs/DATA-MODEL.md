# 设定包与设定卡 JSON Schema 设计文档

> 面向"同人/原创写作资料辅助Agent"项目的核心数据模型

---

## 目录

1. [设计哲学](#设计哲学)
2. [SettingCard JSON Schema](#settingcard-json-schema)
3. [SettingPackage JSON Schema](#settingpackage-json-schema)
4. [确定性组装引擎](#确定性组装引擎)
5. [版本管理与增量更新](#版本管理与增量更新)
6. [导出格式支持](#导出格式支持)
7. [完整示例数据：哈利波特的同人设定](#完整示例数据哈利波特的同人设定)
8. [与PROMPTS.md和RAG-DESIGN.md的一致性](#与promptsmd和rag-designmd的一致性)

---

## 设计哲学

### 为什么选择"卡片-包"两层模型？

传统的写作辅助工具通常采用"文档"模型——设定是一篇或多篇自由格式的文本。这在实践中导致三个问题：

1. **查找困难**："我上次写的那个关于魔法的设定在哪一页？"
2. **更新不一致**：修改了角色A的某个属性，但忘记在另一个文档中同步修改
3. **组装不稳定**：每次"总结设定"时，AI生成的措辞和组织方式都不同（我们测量的生成稳定率仅50%）

"卡片-包"模型通过**原子化存储 + 确定性组装**解决了这些问题：

```
原子化存储 (SettingCard)          确定性组装 (Assembly Engine)
┌──────┐ ┌──────┐ ┌──────┐        ┌─────────────────────┐
│ Card │ │ Card │ │ Card │  ──→   │   SettingPackage    │
│  A   │ │  B   │ │  C   │        │  (按模板机械组装)    │
└──────┘ └──────┘ └──────┘        └─────────────────────┘
   ↑ 每张卡独立修改和版本管理           ↑ 100%可复现的输出
```

- **生成稳定率：50% → 100%**（不再依赖LLM生成设定包的组织结构，改用确定性规则从卡片列表组装）
- **修改影响面可控**：修改一张卡 = 更新一个版本，关联卡片通过Checker自动检测冲突
- **卡片可复用**：同一张世界观卡片可用于多个设定包（如"魔法学院"设定可复用于不同故事）

### 核心设计原则

| 原则 | 说明 |
|------|------|
| **原子性** | 每张卡描述一个且仅一个设定实体，不跨实体 |
| **可溯源** | 每张卡标注信息来源（canon/derived/original）和提取版本 |
| **自描述** | 卡片的schema本身就是文档，字段语义清晰 |
| **可组合** | 卡片通过id引用关联，包是卡片的视图 |
| **版本化** | 所有实体支持版本追踪和回滚 |

---

## SettingCard JSON Schema

### 完整JSON Schema (Draft 2020-12)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://writing-assistant.dev/schemas/setting-card.schema.json",
  "title": "SettingCard",
  "description": "一张原子化的设定卡片，描述单个设定实体",
  "type": "object",
  "required": [
    "id",
    "type",
    "name",
    "content",
    "source",
    "fandom",
    "created_at",
    "version"
  ],
  "properties": {
    "id": {
      "type": "string",
      "description": "卡片唯一标识符。格式: {type_initial}-{sequence}-{slug}",
      "pattern": "^(C|W|P|R)-\\d{3}-[a-z0-9-]+$",
      "examples": ["C-001-snape", "W-005-hogwarts-castle", "P-003-quidditch-accident"]
    },
    "type": {
      "type": "string",
      "enum": ["character", "world", "plot", "relationship"],
      "description": "设定卡类型。C=character, W=world, P=plot, R=relationship"
    },
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 200,
      "description": "设定实体名称。对于人物，使用全名；对于世界观设定，使用主题名称"
    },
    "aliases": {
      "type": "array",
      "items": { "type": "string" },
      "description": "别名/昵称列表，用于搜索和一致性检查时的名称匹配",
      "default": []
    },
    "content": {
      "type": "string",
      "minLength": 1,
      "maxLength": 5000,
      "description": "设定卡的主要内容。自由文本，推荐使用Markdown格式以提升可读性。这是向量化的主要来源"
    },
    "summary": {
      "type": "string",
      "maxLength": 280,
      "description": "一句话摘要，用于列表展示和快速预览。类似推文长度限制",
      "default": ""
    },
    "source": {
      "type": "string",
      "enum": ["canon", "derived", "original"],
      "description": "信息来源类型。canon=原作事实，derived=从canon合理推导，original=完全原创设定"
    },
    "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "对该设定确信程度的评估。canon来源通常为1.0，derived为0.5-0.9，original由用户确认后为1.0",
      "default": 1.0
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" },
      "description": "自由标签，用于分类和检索",
      "default": []
    },
    "fandom": {
      "type": "string",
      "description": "所属同人圈/作品名称。原创作品填写 'original'"
    },
    "canon_stage": {
      "type": "string",
      "description": "（同人创作）卡片所依据的原作时间线阶段。如 '亲世代'、'子世代'、'if线-战后'",
      "default": null
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "卡片首次创建时间 (ISO 8601)"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time",
      "description": "卡片最后修改时间 (ISO 8601)"
    },
    "version": {
      "type": "integer",
      "minimum": 1,
      "description": "卡片版本号，每次修改递增。初始版本为1"
    },
    "status": {
      "type": "string",
      "enum": ["draft", "confirmed", "deprecated", "archived"],
      "description": "卡片状态。draft=草稿待确认，confirmed=已确认，deprecated=已被新版本取代，archived=已归档不再使用",
      "default": "draft"
    },
    "related_cards": {
      "type": "array",
      "items": { "type": "string" },
      "description": "关联卡片的ID列表。用于表达引用关系，如角色卡引用其所属组织的世界观卡",
      "default": []
    },
    "conflicts_with": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "card_id": { "type": "string" },
          "conflict_type": {
            "type": "string",
            "enum": ["name_collision", "timeline", "override", "relationship_asymmetry", "semantic_contradiction"]
          },
          "description": { "type": "string" },
          "detected_at": { "type": "string", "format": "date-time" },
          "resolved": { "type": "boolean", "default": false }
        },
        "required": ["card_id", "conflict_type", "description"]
      },
      "description": "已知与此卡存在冲突的其他卡片",
      "default": []
    },
    "parent_card": {
      "type": "string",
      "description": "父卡片ID。用于表达层级关系，如子角色引用父级角色",
      "default": null
    },
    "source_document": {
      "type": "string",
      "description": "提取来源文档的ID（对应RAG检索结果中的doc_id）。source=canon或derived时必填",
      "default": null
    },
    "source_evidence": {
      "type": "string",
      "maxLength": 1000,
      "description": "提取依据的原文引用。帮助后续验证提取准确性",
      "default": null
    },
    "extraction_prompt_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "提取此卡时使用的Prompt版本号（对应PROMPTS.md中的版本管理）。用于追溯字段漂移到具体版本",
      "default": null
    },
    "fields": {
      "type": "object",
      "description": "类型特定的结构化字段。根据type值使用不同的子schema",
      "oneOf": [
        { "$ref": "#/$defs/CharacterFields" },
        { "$ref": "#/$defs/WorldFields" },
        { "$ref": "#/$defs/PlotFields" },
        { "$ref": "#/$defs/RelationshipFields" }
      ]
    }
  },

  "$defs": {
    "CharacterFields": {
      "title": "CharacterFields",
      "description": "type=character时的专用字段",
      "type": "object",
      "properties": {
        "full_name": {
          "type": "string",
          "description": "角色的完整姓名"
        },
        "gender": {
          "type": "string",
          "description": "性别认同"
        },
        "age": {
          "type": "object",
          "description": "年龄信息（因为时间线变化，年龄用范围或计算式表达）",
          "properties": {
            "value": { "type": "string" },
            "format": {
              "type": "string",
              "enum": ["exact", "range", "calculated"],
              "description": "exact=确切年龄, range=范围, calculated=基于出生年份计算"
            },
            "birth_year": { "type": "string" },
            "reference_stage": {
              "type": "string",
              "description": "此年龄对应的canon_stage"
            }
          }
        },
        "appearance": {
          "type": "string",
          "description": "外貌描述",
          "default": null
        },
        "personality": {
          "type": "string",
          "description": "性格描述",
          "default": null
        },
        "background": {
          "type": "string",
          "description": "背景故事",
          "default": null
        },
        "abilities": {
          "type": "array",
          "items": { "type": "string" },
          "description": "能力/技能列表"
        },
        "weaknesses": {
          "type": "array",
          "items": { "type": "string" },
          "description": "弱点/缺陷列表"
        },
        "motivations": {
          "type": "array",
          "items": { "type": "string" },
          "description": "动机/驱动力"
        },
        "affiliations": {
          "type": "array",
          "items": { "type": "string" },
          "description": "所属组织/团体（引用World卡片的ID或直接写名称）"
        },
        "speech_pattern": {
          "type": "string",
          "description": "说话方式/语言习惯",
          "default": null
        },
        "arc_type": {
          "type": "string",
          "enum": ["positive", "negative", "flat", "fall_rise", "rise_fall"],
          "description": "人物弧光类型。positive=成长, negative=堕落, flat=平面不变, fall_rise=先堕落后成长, rise_fall=先成长后堕落"
        }
      }
    },

    "WorldFields": {
      "title": "WorldFields",
      "description": "type=world时的专用字段",
      "type": "object",
      "properties": {
        "category": {
          "type": "string",
          "enum": [
            "geography", "culture", "politics", "economics",
            "technology", "magic_system", "religion", "history",
            "biology", "language", "social_structure", "other"
          ],
          "description": "世界观设定的分类"
        },
        "rules": {
          "type": "string",
          "description": "该世界观要素的规则/原理描述",
          "default": null
        },
        "limitations": {
          "type": "string",
          "description": "该世界观要素的限制条件",
          "default": null
        },
        "inhabitants": {
          "type": "array",
          "items": { "type": "string" },
          "description": "与该设定相关的角色/种族（引用Character卡片ID）"
        },
        "connected_locations": {
          "type": "array",
          "items": { "type": "string" },
          "description": "关联的地点（引用World卡片ID）"
        },
        "historical_period": {
          "type": "string",
          "description": "该设定生效的历史时期"
        },
        "inspirations": {
          "type": "array",
          "items": { "type": "string" },
          "description": "该设定的创作灵感来源（现实参照、其他作品等）"
        }
      }
    },

    "PlotFields": {
      "title": "PlotFields",
      "description": "type=plot时的专用字段",
      "type": "object",
      "properties": {
        "stage": {
          "type": "string",
          "enum": ["setup", "rising_action", "climax", "falling_action", "resolution", "backstory", "side_quest"],
          "description": "情节节点在叙事结构中的阶段"
        },
        "key_events": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "event": { "type": "string" },
              "timestamp": { "type": "string", "description": "事件时间（事件内时间线）" },
              "cause": { "type": "string", "description": "事件的直接原因" },
              "effect": { "type": "string", "description": "事件的直接后果" }
            }
          },
          "description": "关键事件列表"
        },
        "participants": {
          "type": "array",
          "items": { "type": "string" },
          "description": "参与此情节的角色（引用Character卡片ID）"
        },
        "location": {
          "type": "string",
          "description": "情节发生的主要地点（引用World卡片ID）"
        },
        "conflict_type": {
          "type": "string",
          "enum": ["person_vs_person", "person_vs_self", "person_vs_society", "person_vs_nature", "person_vs_technology", "person_vs_fate"],
          "description": "冲突类型"
        },
        "pacing": {
          "type": "string",
          "enum": ["fast", "moderate", "slow", "variable"],
          "description": "节奏"
        }
      }
    },

    "RelationshipFields": {
      "title": "RelationshipFields",
      "description": "type=relationship时的专用字段",
      "type": "object",
      "properties": {
        "participants": {
          "type": "array",
          "items": { "type": "string" },
          "minItems": 2,
          "maxItems": 5,
          "description": "关系参与者的角色卡片ID（至少2个）"
        },
        "relationship_type": {
          "type": "string",
          "enum": [
            "familial", "romantic", "friendship", "antagonistic",
            "mentor_student", "professional", "political", "secret",
            "one_sided", "complicated", "other"
          ],
          "description": "关系类型"
        },
        "dynamics": {
          "type": "string",
          "description": "关系动力学描述（权力关系、情感流向等）"
        },
        "history": {
          "type": "string",
          "description": "关系的历史演变",
          "default": null
        },
        "current_state": {
          "type": "string",
          "enum": ["positive", "neutral", "negative", "ambiguous", "evolving"],
          "description": "当前关系状态"
        },
        "is_mutual": {
          "type": "boolean",
          "description": "关系是否双向/对称",
          "default": false
        },
        "public_perception": {
          "type": "string",
          "description": "他人眼中的这段关系",
          "default": null
        },
        "key_events": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "event": { "type": "string" },
              "impact": { "type": "string" },
              "timestamp": { "type": "string" }
            }
          },
          "description": "影响此关系的关键事件"
        }
      }
    }
  }
}
```

### 字段设计理由

#### 为什么 type 使用枚举值而非自由字符串？

四个枚举值 `character|world|plot|relationship` 覆盖了写作设定中95%以上的实体类型。使用枚举而非自由字符串有四个理由：
1. **路由确定性**：检索和冲突检测中的"同类型优先"策略依赖精确的类型匹配
2. **Schema验证**：不同type有完全不同的fields子结构，枚举是oneOf路由的锚点
3. **UI渲染**：前端可以用确定的组件渲染不同类型的卡片
4. **统计分析**：可以统计项目中各类型卡片的分布

如果用户确实需要新类型（如 "item"、"creature"），可以通过 `tags` 字段标注而无需修改Schema——这是一种"开放扩展但封闭修改"的设计。

#### 为什么 source 分 canon/derived/original？

在同人创作中，区分"原作事实"和"我的二创"是核心需求：

- **canon**: "斯内普是霍格沃茨的魔药学教授"——原作明确陈述的事实
- **derived**: "斯内普在霍格沃茨期间可能经常去禁书区"——合理推断但非明确事实
- **original**: "斯内普有一个名为艾琳的童年玩伴"——完全同人原创

这种区分支持三个功能：
1. canon对齐检查（RAG-DESIGN.md中的L3冲突检测）
2. 阅读时让读者知道"什么是确定的，什么是不确定的"
3. 与其他同人作者交流时清楚标明自己的设定边界

#### 为什么 conflicts_with 是嵌入数组而非独立关系表？

在设计阶段，我们考虑了两种方案：

**方案A（图数据库 - 独立关系表）**：
```
CREATE TABLE card_conflicts (
  card_id_a UUID,
  card_id_b UUID,
  conflict_type TEXT,
  ...
);
```
优点：查询灵活，适合复杂图遍历。
缺点：需要在两个系统间维护一致性，卡片导出/导入时需要单独处理关联数据。

**方案B（嵌入数组 - 当前方案）**：
```
conflicts_with: [{ card_id, conflict_type, ... }]
```
优点：自包含，卡片导出时不需要额外查询；与SettingCard原子性设计一致。
缺点：冲突信息冗余存储（冲突双向记录在两边的卡片中）。

**选择方案B的理由**：对于写作辅助场景，一张卡通常只有0-5个冲突，数据量极小。嵌入方案的自包含性使得卡片可以独立导出/导入/分享，这个价值远大于冗余存储的成本。Checker负责维护冲突双向一致性。

---

## SettingPackage JSON Schema

### 完整JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://writing-assistant.dev/schemas/setting-package.schema.json",
  "title": "SettingPackage",
  "description": "一个设定包，由多张设定卡通过确定性组装引擎组合而成",
  "type": "object",
  "required": [
    "package_id",
    "title",
    "fandom",
    "created_at",
    "assembly_version",
    "cards"
  ],
  "properties": {
    "package_id": {
      "type": "string",
      "description": "设定包唯一标识符。格式: PKG-{timestamp}-{short_hash}",
      "pattern": "^PKG-\\d{14}-[a-f0-9]{6}$"
    },
    "title": {
      "type": "string",
      "minLength": 1,
      "maxLength": 200,
      "description": "设定包的标题"
    },
    "description": {
      "type": "string",
      "maxLength": 2000,
      "description": "设定包的描述/简介"
    },
    "fandom": {
      "type": "string",
      "description": "所属同人圈/作品名称。原创作品填写 'original'"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time"
    },
    "assembly_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "组装引擎的版本号。同一组卡片用不同版本引擎组装可能产生不同的输出结构"
    },
    "assembly_template": {
      "type": "string",
      "enum": ["full_profile", "character_focus", "world_focus", "plot_focus", "relationship_map", "summary"],
      "description": "组装模板类型，决定包的输出结构和组织方式",
      "default": "full_profile"
    },
    "card_count": {
      "type": "integer",
      "minimum": 1,
      "description": "设定包包含的卡片总数（计算字段）"
    },
    "cards": {
      "type": "array",
      "description": "设定包包含的所有设定卡",
      "items": { "$ref": "https://writing-assistant.dev/schemas/setting-card.schema.json" },
      "minItems": 1
    },
    "indices": {
      "type": "object",
      "description": "分类索引——由组装引擎自动生成，不手动维护",
      "properties": {
        "characters": {
          "type": "array",
          "items": { "type": "string" },
          "description": "所有type=character的卡片ID列表"
        },
        "world_settings": {
          "type": "array",
          "items": { "type": "string" },
          "description": "所有type=world的卡片ID列表"
        },
        "plots": {
          "type": "array",
          "items": { "type": "string" },
          "description": "所有type=plot的卡片ID列表"
        },
        "relationships": {
          "type": "array",
          "items": { "type": "string" },
          "description": "所有type=relationship的卡片ID列表"
        }
      }
    },
    "statistics": {
      "type": "object",
      "description": "设定包的统计信息——由组装引擎自动计算",
      "properties": {
        "total_cards": { "type": "integer" },
        "by_type": {
          "type": "object",
          "properties": {
            "character": { "type": "integer" },
            "world": { "type": "integer" },
            "plot": { "type": "integer" },
            "relationship": { "type": "integer" }
          }
        },
        "by_source": {
          "type": "object",
          "properties": {
            "canon": { "type": "integer" },
            "derived": { "type": "integer" },
            "original": { "type": "integer" }
          }
        },
        "average_confidence": { "type": "number" },
        "conflict_count": {
          "type": "integer",
          "description": "未解决的冲突数量"
        }
      }
    },
    "conflict_summary": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "conflict_id": { "type": "string" },
          "severity": { "type": "string" },
          "card_a": { "type": "string" },
          "card_b": { "type": "string" },
          "description": { "type": "string" },
          "resolved": { "type": "boolean" }
        }
      },
      "description": "从所有卡片汇总的冲突摘要"
    },
    "check_report": {
      "type": "object",
      "description": "最后一次Checker运行的完整报告（引用PROMPTS.md P-05输出格式）",
      "properties": {
        "check_id": { "type": "string" },
        "overall_score": { "type": "number" },
        "passed": { "type": "boolean" },
        "checked_at": { "type": "string", "format": "date-time" },
        "conflicts": { "type": "array" },
        "warnings": { "type": "array" },
        "completeness_report": { "type": "object" }
      }
    },
    "export_formats": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "format": { "type": "string", "enum": ["markdown", "json", "html"] },
          "exported_at": { "type": "string", "format": "date-time" },
          "content_hash": { "type": "string" }
        }
      },
      "description": "已导出的格式记录"
    }
  }
}
```

### 为什么 indices 和 statistics 是计算字段？

`indices` 和 `statistics` 是冗余信息——它们可以从 `cards` 数组推导。但我们仍然存储它们，原因是：
1. **快速访问**：查询"这个包的character类型卡片有多少张"不需要遍历整个cards数组
2. **API响应优化**：列表API可以返回statistics而不加载完整card内容
3. **一致性校验**：statistics与cards的差异本身就是一种数据完整性检查

组装引擎在每次组装时重新计算这两个字段，确保它们总是准确的。

---

## 确定性组装引擎

### 设计动机

在Badcase分析中我们发现，直接让LLM从卡片列表生成设定包文档，其输出结构在多次运行间的一致性只有50%。换句话说，同样的输入，两次生成的结果中大标题都不一样。

**确定性组装引擎**将"组织内容"和"生成内容"解耦：
- **组织**（确定性的）：按模板规则决定输出的结构、顺序、层级——100%可复现
- **生成**（由LLM完成的）：提取和归类卡片时的一次性工作——输出是卡片本身（已存入数据库，不重复生成）

### 组装引擎的输入/输出契约

```
输入 (Input):
{
  "cards": [SettingCard],           // 必须：要组装的设定卡列表
  "template": "full_profile",       // 可选：组装模板，默认 full_profile
  "options": {                      // 可选：组装选项
    "include_drafts": false,        // 是否包含草稿状态的卡片
    "include_deprecated": false,    // 是否包含已废弃的卡片
    "sort_by": "type|confidence|created", // 排序方式
    "group_related": true,          // 是否将关联卡片放在一起
    "show_sources": true,           // 是否显示来源信息
    "show_confidence": true,        // 是否显示置信度
    "show_conflicts": true,         // 是否显示冲突标记
    "language": "zh"                // 输出语言
  }
}

输出 (Output):
{
  "package": SettingPackage,        // 完整的设定包（符合上述Schema）
  "assembly_metadata": {
    "algorithm": "deterministic-rule-engine",
    "version": "1.0.0",
    "rules_applied": ["sort", "group", "index"],
    "cards_included": 5,
    "cards_excluded": {
      "drafts_excluded": 0,
      "deprecated_excluded": 0,
      "duplicates_deduplicated": 0
    },
    "assembly_duration_ms": 12
  }
}
```

### 组装规则（全确定性，无LLM参与）

```
Rule 1: 卡片过滤
  IF options.include_drafts == false:
    REMOVE cards WHERE status == "draft"
  IF options.include_deprecated == false:
    REMOVE cards WHERE status == "deprecated"
  DEDUPLICATE by id (keep highest version)

Rule 2: 卡片排序
  PRIMARY KEY: 按type顺序 (character → world → plot → relationship)
  SECONDARY KEY: 按name字母序
  TERTIARY KEY: 按 confidence 降序

Rule 3: 索引构建
  FOR EACH card:
    SWITCH card.type:
      CASE "character" → ADD card.id TO indices.characters
      CASE "world" → ADD card.id TO indices.world_settings
      CASE "plot" → ADD card.id TO indices.plots
      CASE "relationship" → ADD card.id TO indices.relationships

Rule 4: 统计计算
  statistics.total_cards = COUNT(cards)
  statistics.by_type = GROUP BY type, COUNT
  statistics.by_source = GROUP BY source, COUNT
  statistics.average_confidence = AVG(cards.confidence)
  statistics.conflict_count = COUNT unresolved conflicts

Rule 5: 冲突汇总
  FOR EACH card:
    FOR EACH conflict in card.conflicts_with WHERE resolved == false:
      ADD TO conflict_summary

Rule 6: 关系分组（如果 options.group_related == true）
  FOR EACH character card:
    FIND ALL relationship cards WHERE card.id IN relationship.participants
    GROUP these relationship cards under the character card in display order
```

### 组装模板

| 模板 | 说明 | 卡片排列方式 |
|------|------|-------------|
| `full_profile` | 完整设定档案 | 按type分四个大章节，每章内按name排序 |
| `character_focus` | 以人物为中心 | 人物卡排最前+每个角色后跟其相关的关系卡和情节卡 |
| `world_focus` | 以世界观为中心 | 世界观卡排最前+每个设定后跟相关的地理/文化卡 |
| `plot_focus` | 以情节为中心 | 按情节卡stage排序+每个情节后跟参与角色 |
| `relationship_map` | 关系图谱视图 | 所有关系卡+被引用的角色卡 |
| `summary` | 精简摘要 | 每张卡只输出name和summary字段，1页纸概览 |

---

## 版本管理与增量更新

### SettingCard 版本管理

```
版本生命周期:
  draft → confirmed → (修改) → new draft → confirmed (version++)
                                           ↘ old version → deprecated → archived (30天后)

版本追踪:
  每个 card_id 在数据库中可以有多个版本记录:
  - 当前活跃版本: status = "draft" 或 "confirmed"
  - 历史版本: status = "deprecated"（保留30天）
  - 归档版本: status = "archived"（30天后自动转换）

修改操作:
  1. 读取当前活跃版本
  2. 创建新版本记录（version = old_version + 1）
  3. 新记录 status = "draft"
  4. 用户确认后 status → "confirmed"
  5. 旧版本 status → "deprecated"

回滚操作:
  1. 选择历史版本
  2. 创建新记录（version = current_max + 1）
  3. 复制历史版本内容到新记录
  4. status = "draft" → 用户确认 → "confirmed"
```

### SettingPackage 版本管理

```
包是卡片的视图，本身不"修改"——每次组装生成新的 package_id。

包的版本通过以下方式追踪：
  1. package_id 中的 timestamp 记录组装时间
  2. 包中每张卡片的 version 记录各自的最新版本
  3. assembly_version 记录使用的组装引擎版本

"同一个设定包的不同版本"通过 comparing 两个 package_id 实现：
  - 比较两张卡的 content 差异 → 内容变更
  - 比较卡片的 version 差异 → 更新次数
  - 比较卡片列表 → 新增/删除的卡
```

### 增量更新流程

```
场景1: 用户修改了一张卡
  1. SettingCard.version += 1
  2. 触发冲突检测（Checker，异步）
  3. 如果有冲突 → 更新 conflicts_with 字段
  4. 用户下次打开设定包 → 重新组装（自动获取最新版本）
  5. 用户看到更新后的包（变化以diff形式高亮）

场景2: Agent提取了新卡
  1. 新卡写入L3（status="draft", confidence根据来源设置）
  2. 触发冲突检测
  3. 用户确认后 status → "confirmed"
  4. 手动添加到设定包（或自动添加到"当前工作包"）

场景3: 用户废弃了一张卡
  1. status → "deprecated"
  2. 从所有设定包的卡片列表中移除
  3. 但在数据库中保留30天
  4. 如果有其他卡片 related_cards 引用了此卡 → 生成警告
```

---

## 导出格式支持

### Markdown导出

```markdown
# {package.title}
> {package.description}

**所属作品**: {package.fandom}
**生成时间**: {package.created_at}
**卡片数量**: {package.statistics.total_cards}
**平均置信度**: {package.statistics.average_confidence * 100}%

---

## 角色设定 ({package.statistics.by_type.character}张)

### {card.name} `[id: {card.id}]`
- **别名**: {card.aliases.join(', ')}
- **来源**: {card.source} | **置信度**: {card.confidence * 100}%
- **外貌**: {card.fields.appearance}
- **性格**: {card.fields.personality}
- **背景**: {card.fields.background}
- **能力**: {card.fields.abilities.join(', ')}
- **所属组织**: {card.fields.affiliations.join(', ')}

{card.content}

> 溯源: {card.source_document} | Prompt版本: {card.extraction_prompt_version}

---

## 世界观设定 ({package.statistics.by_type.world}张)

### {card.name} `[id: {card.id}]`
- **分类**: {card.fields.category}
- **来源**: {card.source} | **置信度**: {card.confidence * 100}%

**规则**:
{card.fields.rules}

**限制**:
{card.fields.limitations}

{card.content}

---

## 情节设定 ({package.statistics.by_type.plot}张)

### {card.name} `[id: {card.id}]`
- **阶段**: {card.fields.stage}
- **冲突类型**: {card.fields.conflict_type}
- **地点**: {card.fields.location}
- **参与者**: {card.fields.participants.join(', ')}

{card.content}

---

## 关系设定 ({package.statistics.by_type.relationship}张)

### {card.name} `[id: {card.id}]`
- **参与者**: {card.fields.participants.join(' ↔ ')}
- **关系类型**: {card.fields.relationship_type}
- **当前状态**: {card.fields.current_state}
- **双向**: {card.fields.is_mutual ? '是' : '否'}

**关系动态**:
{card.fields.dynamics}

{card.content}

---

## 冲突与警告

{for each conflict in package.conflict_summary}
- [{conflict.severity}] {conflict.description}
  - 涉及卡片: {conflict.card_a}, {conflict.card_b}
  - 已解决: {conflict.resolved ? '是' : '否'}
{endfor}
```

### JSON导出

直接输出完整的 SettingPackage JSON 对象，格式化为2空格缩进。这是机器可读的原始格式，用于导入/导出/备份。

### HTML导出

生成独立HTML文档，包含：
- CSS样式（响应式、可打印、暗色模式支持）
- 目录导航（固定侧边栏）
- 卡片类型徽章（角色/世界观/情节/关系用不同颜色标识）
- 置信度指示条
- 冲突高亮提示

---

## 完整示例数据：哈利波特的同人设定

以下展示一个亲世代斯内普同人的设定包，包含5张设定卡（3张角色、1张世界观、1张关系）和1个完整设定包。

### 示例卡片 C-001: 西弗勒斯·斯内普

```json
{
  "id": "C-001-severus-snape",
  "type": "character",
  "name": "西弗勒斯·斯内普",
  "aliases": ["斯内普", "Sev", "混血王子", "鼻涕精"],
  "content": "西弗勒斯·斯内普，霍格沃茨魔法学校斯莱特林学院学生（1971-1978）。出生于1960年1月9日，混血出身——父亲托比亚斯·斯内普是麻瓜，母亲艾琳·普林斯是女巫。家境贫寒，在蜘蛛尾巷长大。\n\n在霍格沃茨期间展现出卓越的魔药学天赋和黑魔法防御术才能。与格兰芬多的莉莉·伊万斯自幼相识并保持深厚友谊，直到五年级的"泥巴种"事件导致友谊破裂。\n\n性格孤僻、自尊心极强、对力量有执念。在校期间发明了多个咒语（包括神锋无影），对黑魔法有浓厚兴趣。是鼻涕精俱乐部（未来的食死徒预备军）的核心成员。\n\n他的核心矛盾在于：出身与野心之间的撕裂，对莉莉的爱与对力量的渴望之间的冲突，以及每次选择带来的无法挽回的后果。",
  "summary": "斯莱特林学生，魔药天才，与莉莉·伊万斯关系复杂，正在走向一条黑暗但注定孤独的道路",
  "source": "canon",
  "confidence": 1.0,
  "tags": ["protagonist", "slytherin", "potions-master", "half-blood", "tragic-hero"],
  "fandom": "哈利波特",
  "canon_stage": "亲世代（1971-1978）",
  "created_at": "2026-07-20T08:00:00Z",
  "updated_at": "2026-07-22T15:30:00Z",
  "version": 3,
  "status": "confirmed",
  "related_cards": ["C-002-lily-evans", "C-003-james-potter", "W-001-slytherin-common-room", "R-001-snape-lily"],
  "conflicts_with": [
    {
      "card_id": "C-007-young-snape",
      "conflict_type": "name_collision",
      "description": "存在另一张斯内普卡片（童年时期），两个卡片对斯内普11岁前魔法能力的描述不一致",
      "detected_at": "2026-07-21T10:00:00Z",
      "resolved": false
    }
  ],
  "parent_card": null,
  "source_document": "L1-hp-canon-042",
  "source_evidence": "《哈利·波特与死亡圣器》第33章'王子的故事'中详细描述了斯内普的学生时代",
  "extraction_prompt_version": "1.0.0",
  "fields": {
    "full_name": "西弗勒斯·托比亚·斯内普",
    "gender": "男",
    "age": {
      "value": "11-18",
      "format": "range",
      "birth_year": "1960",
      "reference_stage": "亲世代学生时期"
    },
    "appearance": "黑发及肩，鹰钩鼻，皮肤蜡黄，身形瘦削。常年穿着二手长袍，但始终保持着一种阴郁而危险的优雅",
    "personality": "内向孤僻、自尊心极强、对认可极度渴望。在学术领域自信甚至傲慢，在社交领域笨拙且易受伤害。对亲近的人有深沉的忠诚（尤其是莉莉），对敌人则怀有长久的怨恨。早期的残忍倾向与深藏的温柔并存",
    "background": "蜘蛛尾巷出身，父亲是失业麻瓜工人且有家暴倾向，母亲是没落纯血家族的后裔。在进入霍格沃茨前，莉莉是他唯一的同龄朋友。分院帽几乎没犹豫就将他分入斯莱特林",
    "abilities": [
      "魔药学天才（在校期间已能做NEWT级别魔药）",
      "黑魔法防御术精通",
      "自创咒语（神锋无影、倒挂金钟等）",
      "大脑封闭术入门",
      "魔杖less魔法（非正式）"
    ],
    "weaknesses": [
      "社交笨拙，容易说错话激怒他人",
      "对力量的过度崇拜导致容易受卢修斯等食死徒影响",
      "在压力下做出伤害亲近之人的选择",
      "无法放下怨恨（尤其是对詹姆·波特）"
    ],
    "motivations": [
      "逃离贫困和卑微的出身",
      "获得力量以保护自己和重视的人",
      "获得莉莉的认可和爱",
      "在魔法世界中证明自己的价值"
    ],
    "affiliations": ["斯莱特林学院", "鼻涕精俱乐部（疑似食死徒预备团体）"],
    "speech_pattern": "语速偏慢，措辞精准且有时刻薄。习惯使用长句和复杂的修饰语。愤怒时变得简洁而冰冷。从不使用粗俗的脏话，但能用正常的词汇说出极伤人的话",
    "arc_type": "fall_rise"
  }
}
```

### 示例卡片 C-002: 莉莉·伊万斯

```json
{
  "id": "C-002-lily-evans",
  "type": "character",
  "name": "莉莉·伊万斯",
  "aliases": ["莉莉", "Lily", "伊万斯"],
  "content": "莉莉·伊万斯，格兰芬多学院学生，与斯内普同年。麻瓜出身，但魔法天赋极高——尤其在魔咒学和魔药学。\n\n她与斯内普青梅竹马，在进入霍格沃茨后友谊经历了考验和最终的破裂。五年级的"泥巴种"事件是两人关系的转折点。\n\n性格方面，莉莉热情、勇敢、正义感极强，但有时略显自我正义。她真心关心斯内普，但不能接受他对黑魔法的迷恋和与未来食死徒的交往。\n\n在canon中，她最终与詹姆·波特走到一起。但在本同人项目中，她的情感选择将是重要的戏剧焦点——理想主义与实用主义、安全感与冒险欲之间的矛盾。",
  "summary": "格兰芬多学生，麻瓜出身的天才女巫，斯内普的童年挚友和一生挚爱",
  "source": "canon",
  "confidence": 1.0,
  "tags": ["female-lead", "gryffindor", "muggleborn", "genius"],
  "fandom": "哈利波特",
  "canon_stage": "亲世代（1971-1978）",
  "created_at": "2026-07-20T08:30:00Z",
  "updated_at": "2026-07-20T08:30:00Z",
  "version": 1,
  "status": "confirmed",
  "related_cards": ["C-001-severus-snape", "C-003-james-potter", "R-001-snape-lily"],
  "conflicts_with": [],
  "parent_card": null,
  "source_document": "L1-hp-canon-043",
  "source_evidence": "系列中多处提到莉莉的学生时代，尤其在《死亡圣器》'王子的故事'一章",
  "extraction_prompt_version": "1.0.0",
  "fields": {
    "full_name": "莉莉·玛丽·伊万斯",
    "gender": "女",
    "age": {
      "value": "11-18",
      "format": "range",
      "birth_year": "1960",
      "reference_stage": "亲世代学生时期"
    },
    "appearance": "深红色长发，碧绿色杏仁眼。光彩照人，有一种天然的、不刻意修饰的美丽",
    "personality": "外表开朗温暖，内心有坚定的道德底线。对朋友极其忠诚，但不能容忍她认为是错的事。有时在道德判断上显得非黑即白，这既是她的光芒也是局限",
    "background": "在普通麻瓜家庭长大，与姐姐佩妮关系紧张。发现自己是女巫后兴奋而自豪，视霍格沃茨为真正的家园",
    "abilities": [
      "魔咒学天才（斯拉格霍恩教授称赞有加）",
      "魔药学天赋异禀",
      "天生的魔力控制能力",
      "强大的魔法直觉"
    ],
    "weaknesses": [
      "道德上的非黑即白思维",
      "对有争议的事缺乏耐心",
      "有时在无意识中伤害亲近的人（她的"正确"对对方的自尊心可能是打击）",
      "对麻瓜姐姐佩妮的复杂感情"
    ],
    "motivations": [
      "维护正义和公平",
      "保护被欺负的人",
      "在魔法世界找到归属感",
      "调和麻瓜出身和女巫身份之间的矛盾"
    ],
    "affiliations": ["格兰芬多学院", "鼻涕精俱乐部（非正式，因与斯内普的关系）"],
    "speech_pattern": "语速较快，充满活力和热情。据理力争时吐字清晰有力。对斯内普说话时带有一种熟悉的随意感（源于童年友谊）",
    "arc_type": "positive"
  }
}
```

### 示例卡片 C-003: 詹姆·波特

```json
{
  "id": "C-003-james-potter",
  "type": "character",
  "name": "詹姆·波特",
  "aliases": ["詹姆", "James", "尖头叉子", "波特"],
  "content": "詹姆·波特，格兰芬多学院学生，纯血统，来自富裕而有声望的波特家族。在霍格沃茨是风云人物——魁地奇追球手、恶作剧大师、掠夺者小团体的核心。\n\n他与斯内普的关系从第一次见面就充满敌意，这种敌对贯穿整个学生时代，并在五年级的"倒挂金钟"事件和斯内普被引诱到打人柳事件中达到顶峰。\n\n在本同人项目中，詹姆不是简单的"欺凌者"形象——他的成长弧光是从被宠坏的、以自我为中心的少年，到逐渐理解特权与责任的真谛。他对莉莉的追求和与斯内普的对抗是这一成长的核心驱动力。",
  "summary": "格兰芬多的风云人物，掠夺者领袖，斯内普的宿敌，莉莉的追求者",
  "source": "canon",
  "confidence": 1.0,
  "tags": ["gryffindor", "pureblood", "quidditch", "marauders", "rival"],
  "fandom": "哈利波特",
  "canon_stage": "亲世代（1971-1978）",
  "created_at": "2026-07-20T09:00:00Z",
  "updated_at": "2026-07-21T11:00:00Z",
  "version": 2,
  "status": "confirmed",
  "related_cards": ["C-001-severus-snape", "C-002-lily-evans", "R-001-snape-lily"],
  "conflicts_with": [],
  "parent_card": null,
  "source_document": "L1-hp-canon-044",
  "source_evidence": "系列中多处提到詹姆的学生时代，尤其在《凤凰社》斯内普最糟糕的记忆一章",
  "extraction_prompt_version": "1.0.0",
  "fields": {
    "full_name": "詹姆·弗利蒙·波特",
    "gender": "男",
    "age": {
      "value": "11-18",
      "format": "range",
      "birth_year": "1960",
      "reference_stage": "亲世代学生时期"
    },
    "appearance": "乱蓬蓬的黑发（永远无法梳平），圆形眼镜，身材精瘦但充满运动员的爆发力。总是带着一种漫不经心的自信笑容",
    "personality": "天赋异禀但被宠坏，在青春期早期以自我为中心且缺乏共情。对朋友极其忠诚（为卢平成为阿尼玛格斯），但对不喜欢的对象残忍且毫无歉意。随着成长逐渐理解自己的特权和责任",
    "background": "波特家族独子，在富裕和宠爱中长大。从小被灌输纯血统优越感但以温和的方式（父母晚年得子，格外宠溺）",
    "abilities": [
      "魁地奇天才追球手",
      "变形术天才（15岁成为阿尼玛格斯）",
      "恶作剧魔法大师",
      "天生的领袖魅力"
    ],
    "weaknesses": [
      "傲慢和特权意识（早期）",
      "对不喜欢的对象缺乏共情",
      "容易以崇拜/嫉妒的眼光看待人际关系",
      "在竞争（尤其是争夺莉莉的关注）时失去理性"
    ],
    "motivations": [
      "获得莉莉的关注和喜爱",
      "证明自己是"最好的"（对斯内普的竞争心理）",
      "保护掠夺者朋友们",
      "逐渐觉醒的对正义的追求（后期）"
    ],
    "affiliations": ["格兰芬多学院", "掠夺者", "格兰芬多魁地奇球队"],
    "speech_pattern": "自信且随意，喜欢开玩笑和使用绰号。对斯内普说话时带有明显的蔑视和挑衅。对莉莉说话时会努力变得"正经"但往往失败",
    "arc_type": "positive"
  }
}
```

### 示例卡片 W-001: 斯莱特林公共休息室与宿舍文化

```json
{
  "id": "W-001-slytherin-common-room",
  "type": "world",
  "name": "斯莱特林公共休息室与宿舍文化",
  "aliases": ["斯莱特林地牢", "蛇院公共休息室"],
  "content": "斯莱特林公共休息室位于霍格沃茨城堡的地牢深处，入口隐藏在一道石墙后，需要口令进入。休息室的窗户在湖底，透过窗户可以看到黑湖的水下世界——巨型乌贼、格林迪洛和其他水生魔法生物。\n\n室内常年弥漫着绿银色调的冷光，由天花板上悬挂的魔法灯笼和壁炉中永不熄灭的绿色火焰提供照明。雕刻精美的蛇形装饰遍布墙壁。\n\n宿舍是按年级和家族地位划分的。纯血统家族的子弟通常占据最好的房间，而混血出身的学生（如斯内普）则往往被分配到较小的单人间或在多人宿舍的边缘位置。\n\n斯莱特林内部存在严格的非正式等级制度，其核心是：纯血统 > 混血 > 麻瓜出身（极少数）。但学术才能和与有权势者的关系可以在一定程度上弥补出身的劣势。\n\n公共休息室是各种秘密交易、政治联盟和权力游戏的温床。高年级生对低年级生有不成文的"指导"权利，这种文化使得斯莱特林更像一个政治组织而非普通的学院。",
  "summary": "斯莱特林的湖底地牢，权力游戏和秘密交易的温床，严格的非正式等级制度",
  "source": "derived",
  "confidence": 0.75,
  "tags": ["hogwarts", "slytherin", "dungeon", "house-culture", "hierarchy"],
  "fandom": "哈利波特",
  "canon_stage": "亲世代（1971-1978）",
  "created_at": "2026-07-20T09:30:00Z",
  "updated_at": "2026-07-22T10:00:00Z",
  "version": 2,
  "status": "confirmed",
  "related_cards": ["C-001-severus-snape"],
  "conflicts_with": [],
  "parent_card": null,
  "source_document": "L1-hp-canon-100",
  "source_evidence": "《密室》中描述斯莱特林公共休息室在湖底；《死亡圣器》提到斯内普在校期间的社交状况。等级制度细节为合理推断",
  "extraction_prompt_version": "1.0.0",
  "fields": {
    "category": "social_structure",
    "rules": "非正式等级制度：纯血>混血>麻瓜出身。学术才能可部分弥补出身劣势。高年级生对低年级生有不成文的'指导'权——实为控制权。任何违反内部规范的行为会受到集体的冷遇和'教训'",
    "limitations": "等级制度是非正式的——理论上霍格沃茨不承认任何学院内部的等级差别。在公共区域和课堂上，所有学生名义上平等。极有天赋的混血学生（如斯内普）可以在一定程度上打破等级壁垒",
    "inhabitants": ["C-001-severus-snape", "卢修斯·马尔福（高年级）", "纳西莎·布莱克（高年级）", "埃弗里", "穆尔塞伯"],
    "connected_locations": [],
    "historical_period": "霍格沃茨建校至今",
    "inspirations": ["英国公学内部的fagging系统", "维多利亚时期的社会等级制度", "现代政治组织的权力运作方式"]
  }
}
```

### 示例卡片 R-001: 斯内普与莉莉的关系

```json
{
  "id": "R-001-snape-lily",
  "type": "relationship",
  "name": "斯内普与莉莉——青梅竹马到形同陌路",
  "aliases": ["Snily"],
  "content": "斯内普和莉莉的关系是哈利波特系列中最复杂、最悲剧的人际关系之一。\n\n他们在9岁左右在游乐场相识，斯内普第一个告诉莉莉她是女巫。这种"魔法世界的启蒙者"身份构成了斯内普对莉莉感情的底色——对她而言，他是通往魔法世界的桥梁；对他而言，她是灰暗童年中唯一的光。\n\n进入霍格沃茨后，分院将两人分入对立学院，揭开了关系破裂的序幕。但真正的裂缝是价值观的差异——莉莉不能接受斯内普对黑魔法的迷恋和与未来食死徒的交往。五年级的"泥巴种"事件是压垮骆驼的最后一根稻草。\n\n在同人创作中，这段关系是"如果……会怎样"的富矿。本项目的核心探索是：如果在某个关键节点，斯内普做出了不同的选择，两人的关系是否能走向不同的结局。",
  "summary": "从童年玩伴到分道扬镳——一段关于爱、选择和身份认同的悲剧关系",
  "source": "canon",
  "confidence": 1.0,
  "tags": ["core-relationship", "friendship-to-estrangement", "tragedy", "what-if"],
  "fandom": "哈利波特",
  "canon_stage": "亲世代（1971-1978）",
  "created_at": "2026-07-20T10:00:00Z",
  "updated_at": "2026-07-20T10:00:00Z",
  "version": 1,
  "status": "confirmed",
  "related_cards": ["C-001-severus-snape", "C-002-lily-evans", "C-003-james-potter"],
  "conflicts_with": [],
  "parent_card": null,
  "source_document": "L1-hp-canon-045",
  "source_evidence": "《死亡圣器》第33章'王子的故事'提供了这段关系的完整时间线",
  "extraction_prompt_version": "1.0.0",
  "fields": {
    "participants": ["C-001-severus-snape", "C-002-lily-evans"],
    "relationship_type": "complicated",
    "dynamics": "不对称的情感投入——斯内普对莉莉的情感是定义了他整个人生的爱（无论其性质是浪漫还是灵魂依赖），莉莉对斯内普是深厚的友谊+渐增的失望。权力关系也存在不对称——在魔法知识上斯内普是给予者，在社交地位上莉莉是优势方",
    "history": "1969（9岁）：在游乐场相识，斯内普告知莉莉她是女巫。\n1971（11岁）：一同进入霍格沃茨，被分入对立学院。\n1971-1975（1-5年级）：友谊在学院对立和价值观差异中逐渐磨损。斯内普在黑魔法和食死徒预备团体中越陷越深，莉莉越来越无法接受。\n1975（5年级，OWL考试后）：'泥巴种'事件——斯内普在詹姆的公开羞辱下失控，对莉莉喊出'泥巴种'。莉莉从此与他决裂。\n1976-1978（6-7年级）：两人彻底形同陌路。斯内普在食死徒道路上加速前进，莉莉在与詹姆的关系中逐渐找到幸福",
    "current_state": "negative",
    "is_mutual": false,
    "public_perception": "在格兰芬多看来，莉莉终于'醒悟'了；在斯莱特林看来，斯内普对'泥巴种'的执着是软弱。这段关系在两边都不被理解",
    "key_events": [
      {
        "event": "游乐场初遇",
        "impact": "建立了'魔法世界启蒙者-受启蒙者'的深层纽带",
        "timestamp": "1969年夏"
      },
      {
        "event": "霍格沃茨分院仪式",
        "impact": "物理和象征性地将两人分开，奠定了对立的基础",
        "timestamp": "1971年9月1日"
      },
      {
        "event": "泥巴种事件",
        "impact": "关系到此彻底破裂的不可逆转折点",
        "timestamp": "1976年6月OWL考试后"
      },
      {
        "event": "斯内普被引诱到打人柳/尖叫棚屋事件",
        "impact": "斯内普差点死亡，詹姆救了他——但斯内普不认为这是'救'，加深了仇恨和屈辱",
        "timestamp": "1976年左右"
      }
    ]
  }
}
```

### 示例设定包

```json
{
  "package_id": "PKG-20260723083000-a1b2c3",
  "title": "亲世代斯内普同人——角色与关系设定包",
  "description": "以斯内普为中心的角色设定包，聚焦霍格沃茨学生时代的核心人物和关系网络。作为《蜘蛛尾巷的冬天》同人的基础设定",
  "fandom": "哈利波特",
  "created_at": "2026-07-23T08:30:00Z",
  "updated_at": "2026-07-23T08:30:00Z",
  "assembly_version": "1.0.0",
  "assembly_template": "character_focus",
  "card_count": 5,
  "cards": [
    { "$ref": "C-001-severus-snape (完整SettingCard见上)" },
    { "$ref": "C-002-lily-evans (完整SettingCard见上)" },
    { "$ref": "C-003-james-potter (完整SettingCard见上)" },
    { "$ref": "W-001-slytherin-common-room (完整SettingCard见上)" },
    { "$ref": "R-001-snape-lily (完整SettingCard见上)" }
  ],
  "indices": {
    "characters": ["C-001-severus-snape", "C-002-lily-evans", "C-003-james-potter"],
    "world_settings": ["W-001-slytherin-common-room"],
    "plots": [],
    "relationships": ["R-001-snape-lily"]
  },
  "statistics": {
    "total_cards": 5,
    "by_type": {
      "character": 3,
      "world": 1,
      "plot": 0,
      "relationship": 1
    },
    "by_source": {
      "canon": 3,
      "derived": 1,
      "original": 0
    },
    "average_confidence": 0.90,
    "conflict_count": 1
  },
  "conflict_summary": [
    {
      "conflict_id": "CONFLICT-001",
      "severity": "medium",
      "card_a": "C-001-severus-snape",
      "card_b": "C-007-young-snape",
      "description": "存在另一张斯内普卡片（童年时期），两个卡片对斯内普11岁前魔法能力的描述不一致",
      "resolved": false
    }
  ],
  "check_report": {
    "check_id": "CHK-20260723-001",
    "overall_score": 0.88,
    "passed": true,
    "checked_at": "2026-07-23T08:29:00Z",
    "conflicts": [
      {
        "conflict_id": "CONFLICT-001",
        "type": "character",
        "severity": "medium",
        "description": "C-001-severus-snape中描述早期魔法能力为'非正式魔杖less魔法'，C-007-young-snape中描述为'有意控制的精准魔法'——两者的精度和控制力描述存在差异",
        "card_ids": ["C-001-severus-snape", "C-007-young-snape"],
        "conflicting_fields": {
          "card_a": "C-001-severus-snape",
          "card_b": "C-007-young-snape",
          "field": "fields.abilities",
          "value_a": "魔杖less魔法（非正式）",
          "value_b": "有意控制的精准魔法"
        },
        "resolution_suggestion": "统一描述为'早期的魔杖less魔法表现不稳定，有时是本能反应，有时可以有意控制'。或明确区分不同年龄段的魔法能力"
      }
    ],
    "warnings": [
      {
        "warning_id": "WARN-001",
        "type": "missing_relationship",
        "description": "詹姆·波特(C-003)与莉莉·伊万斯(C-002)之间存在重要的关系演变，但设定包中缺失对应的relationship卡片",
        "card_ids": ["C-003-james-potter", "C-002-lily-evans"]
      }
    ],
    "completeness_report": {
      "required_fields_filled": 38,
      "required_fields_total": 42,
      "missing_relationships": ["詹姆与莉莉的关系卡", "斯内普与詹姆的敌对关系卡"],
      "orphan_cards": []
    }
  },
  "export_formats": [
    {
      "format": "markdown",
      "exported_at": "2026-07-23T08:35:00Z",
      "content_hash": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
    }
  ]
}
```

---

## 与PROMPTS.md和RAG-DESIGN.md的一致性

本文档定义的数据模型与另两份设计文档之间存在以下引用关系：

### 与 PROMPTS.md 的对应

| DATA-MODEL 字段 | PROMPTS 引用 |
|----------------|-------------|
| `SettingCard.extraction_prompt_version` | 对应 PROMPTS.md 中的Prompt版本号，如 P-04 v1.0.0 |
| `SettingCard.source_document` | 对应 Researcher (P-03) 检索结果中的 `doc_id` |
| `SettingCard.source_evidence` | 对应 Extractor (P-04) 输出中的 `extraction_evidence` |
| `SettingCard.source` (canon\|derived\|original) | 对应 Storm (P-02a) / Clear (P-02b) 输出中的 `source` |
| `SettingCard.confidence` | 所有Prompt中统一的置信度标注字段 |
| `SettingPackage.check_report` | 直接对应 Checker (P-05) 的输出结构 |
| `SettingPackage.export_formats` | 对应 Formatter (P-06) 的三种输出格式 |
| Card ID 格式 `{type_initial}-{seq}-{slug}` | Extractor (P-04) 中定义的 card_id 格式 |

### 与 RAG-DESIGN.md 的对应

| DATA-MODEL 结构 | RAG-DESIGN 引用 |
|----------------|----------------|
| `SettingCard` 整体 | L3 Collection `knowledge_l3_private_{project_id}` 中存储的文档单元 |
| `SettingCard.content` | L3向量化的文本来源字段 |
| `SettingCard.id` | L3元数据中的 `card_id` 索引 |
| `SettingCard.source` | L3元数据中的 `canon_status` (canon\|derived\|original) |
| `SettingCard.conflicts_with` | RAG-DESIGN.md 中"私设冲突自动定位"算法的输出写入位置 |
| `SettingCard.related_cards` | 冲突检测时构建关系图的边数据 |
| `SettingCard.type` | L3元数据中的 `card_type` 辅助索引 |
| `SettingPackage.conflict_summary` | 冲突检测完成后从各卡汇总的结果 |
