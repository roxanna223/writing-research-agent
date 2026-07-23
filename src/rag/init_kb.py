"""知识库初始化 — 三层知识库的种子数据填充.

用法:
    python src/rag/init_kb.py --seed   # 填充种子数据
    python src/rag/init_kb.py --reset  # 重置所有数据
    python src/rag/init_kb.py --stats  # 查看统计
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.knowledge_base import KnowledgeBase, KnowledgeChunk, KnowledgeLayer

# ============================================================
# 种子数据: L1 通用资料 — HP 世界观基础知识
# ============================================================
L1_SEED_DATA: list[dict] = [
    {
        "content": (
            "霍格沃茨魔法学校是英国魔法界唯一的魔法教育机构，位于苏格兰高地。"
            "学校有四个学院：格兰芬多（勇敢）、斯莱特林（野心）、"
            "拉文克劳（智慧）、赫奇帕奇（忠诚）。"
            "学生11岁入学，学制七年。五年级参加O.W.L.考试，七年级参加N.E.W.T.考试。"
        ),
        "source_title": "霍格沃茨魔法学校",
        "domain": "literature",
        "keywords": ["霍格沃茨", "学院", "格兰芬多", "斯莱特林", "拉文克劳", "赫奇帕奇"],
    },
    {
        "content": (
            "魔法部是英国魔法界的政府机构，部长为魔法部部长。"
            "主要部门包括：魔法法律执行司、魔法事故和灾害司、"
            "神奇动物管理控制司、国际魔法合作司、神秘事务司。"
            "魔法部位于伦敦白厅地下，通过电话亭和马桶入口进入。"
        ),
        "source_title": "魔法部",
        "domain": "literature",
        "keywords": ["魔法部", "傲罗", "魔法法律", "神秘事务司"],
    },
    {
        "content": (
            "魔杖是西方巫师施法的核心工具，由木材、杖芯和长度三个要素构成。"
            "杖芯通常使用凤凰羽毛、龙心弦或独角兽尾毛。"
            "魔杖会选择巫师——「魔杖选择巫师」是奥利凡德的名言。"
            "不同木材和杖芯的组合会影响魔法的倾向性和强度。"
        ),
        "source_title": "魔杖学",
        "domain": "literature",
        "keywords": ["魔杖", "奥利凡德", "凤凰羽毛", "龙心弦", "魔法工具"],
    },
    {
        "content": (
            "魔法世界的货币体系：1加隆=17西可，1西可=29纳特。"
            "古灵阁巫师银行是唯一已知的魔法银行，由妖精运营。"
            "金库位于伦敦地下深处，由龙或其他魔法生物看守。"
        ),
        "source_title": "魔法经济与货币",
        "domain": "culture",
        "keywords": ["加隆", "西可", "纳特", "古灵阁", "妖精", "货币"],
    },
    {
        "content": (
            "巫师世界的交通方式包括：飞天扫帚（个人飞行）、飞路网（壁炉传送）、"
            "门钥匙（定点传送）、幻影移形（高级巫师技能，需考证）、"
            "骑士公共汽车（紧急交通）和霍格沃茨特快列车（学生专列）。"
        ),
        "source_title": "魔法交通",
        "domain": "culture",
        "keywords": ["飞天扫帚", "飞路网", "门钥匙", "幻影移形", "骑士公共汽车"],
    },
    {
        "content": (
            "第二次巫师战争（1995-1998）以伏地魔的最终失败告终。"
            "霍格沃茨大战（1998年5月2日）是关键转折点。"
            "战后，魔法部进行了大规模改革，废除纯血统优先法案，"
            "傲罗司由哈利·波特重组，金斯莱·沙克尔出任魔法部部长。"
        ),
        "source_title": "第二次巫师战争",
        "domain": "history",
        "keywords": ["战争", "伏地魔", "霍格沃茨大战", "战后", "1998"],
    },
]

# ============================================================
# 种子数据: L2 写作技法
# ============================================================
L2_SEED_DATA: list[dict] = [
    {
        "content": (
            "人物弧光（Character Arc）是角色在故事中的内在转变轨迹。"
            "三种基本类型：正向弧（成长）、负向弧（堕落）、平弧（坚守）。"
            "在同人创作中，可以利用读者对原角色的既有认知，"
            "通过「改变关键事件」来创造与原作不同的人物弧光。"
        ),
        "source_title": "人物弧光理论",
        "category": "character",
        "keywords": ["人物弧光", "角色成长", "转变", "同人创作"],
    },
    {
        "content": (
            "世界观构建的核心原则：一致性 > 新奇性。"
            "魔法体系需要明确的规则和限制——读者接受的不是「任何事都可能」，"
            "而是「在这个世界的规则下，任何事都可能」。"
            "建议方法：先写「魔法不能做什么」，再写「魔法能做什么」。"
        ),
        "source_title": "世界观构建方法论",
        "category": "narrative",
        "keywords": ["世界观", "魔法体系", "一致性", "规则", "限制"],
    },
    {
        "content": (
            "同人写作中处理原创角色（OC）的核心挑战："
            "避免 Mary Sue / Gary Stu 陷阱。"
            "检查清单：① 角色是否有明确的弱点？② 角色是否改变了原有的权力平衡？"
            "③ 角色是否「抢走」了原角色的高光时刻？"
            "④ 角色的存在是否让故事更有趣而不是更简单？"
        ),
        "source_title": "同人OC创作指南",
        "category": "character",
        "keywords": ["原创角色", "OC", "Mary Sue", "同人写作", "角色设计"],
    },
    {
        "content": (
            "三幕结构是同人/原创通用的叙事框架："
            "第一幕（建立）：介绍世界观、人物、冲突种子。占25%。"
            "第二幕（对抗）：冲突升级、角色面临最大挑战。占50%。"
            "第三幕（解决）：高潮+结局。占25%。"
            "在同人中，可以利用原作已有的「第一幕」，直接从「第二幕」开始。"
        ),
        "source_title": "三幕结构",
        "category": "structure",
        "keywords": ["三幕结构", "叙事", "情节", "高潮", "同人技巧"],
    },
]

# ============================================================
# 种子数据: L3 项目私设 (示例)
# ============================================================
L3_SEED_DATA: list[dict] = [
    {
        "content": (
            "原创私设：中国符箓魔法体系。"
            "林家传承千年的东方魔法体系，以符文和符纸为载体。"
            "与西方魔杖魔法不互斥——已确认符箓魔法与魔杖魔法可以协同施法。"
            "约束：符箓需要提前绘制，不能在战斗中即时生成。"
        ),
        "project_id": "demo-hp-east",
        "card_id": "card-east-001",
        "keywords": ["符箓", "东方魔法", "林家", "中国", "原创设定"],
    },
]


def seed_knowledge_base(kb: KnowledgeBase, reset: bool = False) -> dict:
    """填充种子数据.

    Args:
        kb: KnowledgeBase 实例
        reset: 是否先清空

    Returns:
        统计信息
    """
    if reset:
        for layer in KnowledgeLayer:
            kb._collections[layer] = []

    stats = {"l1": 0, "l2": 0, "l3": 0}

    # L1 种子
    for item in L1_SEED_DATA:
        chunk = KnowledgeChunk(
            layer=KnowledgeLayer.L1_GENERAL,
            content=item["content"],
            source_title=item["source_title"],
            domain=item.get("domain", ""),
            keywords=item.get("keywords", []),
            reliability=0.9,
        )
        kb.add_chunk(chunk)
        stats["l1"] += 1

    # L2 种子
    for item in L2_SEED_DATA:
        chunk = KnowledgeChunk(
            layer=KnowledgeLayer.L2_TECHNIQUE,
            content=item["content"],
            source_title=item["source_title"],
            category=item.get("category", ""),
            keywords=item.get("keywords", []),
            reliability=0.85,
        )
        kb.add_chunk(chunk)
        stats["l2"] += 1

    # L3 种子
    for item in L3_SEED_DATA:
        chunk = KnowledgeChunk(
            layer=KnowledgeLayer.L3_PRIVATE,
            content=item["content"],
            source_title="项目私设",
            project_id=item.get("project_id", ""),
            card_id=item.get("card_id", ""),
            keywords=item.get("keywords", []),
            reliability=1.0,
        )
        kb.add_chunk(chunk)
        stats["l3"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="知识库初始化")
    parser.add_argument("--seed", action="store_true", help="填充种子数据")
    parser.add_argument("--reset", action="store_true", help="重置后填充")
    parser.add_argument("--stats", action="store_true", help="查看统计")
    parser.add_argument(
        "--persist-dir",
        default="./data/knowledge",
        help="持久化目录 (默认: ./data/knowledge)",
    )
    args = parser.parse_args()

    kb = KnowledgeBase(persist_dir=args.persist_dir)

    if args.stats:
        s = kb.stats
        print(f"知识库统计:")
        print(f"  L1 通用资料: {s['l1_general']} chunks")
        print(f"  L2 写作技法: {s['l2_technique']} chunks")
        print(f"  L3 项目私设: {s['l3_private']} chunks")
        print(f"  总计: {s['total_chunks']} chunks")
        return

    if args.seed or args.reset:
        stats = seed_knowledge_base(kb, reset=args.reset)
        print(f"种子数据填充完成:")
        print(f"  L1 通用资料: +{stats['l1']} chunks")
        print(f"  L2 写作技法: +{stats['l2']} chunks")
        print(f"  L3 项目私设: +{stats['l3']} chunks")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
