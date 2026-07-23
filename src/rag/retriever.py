"""多层检索器 — 三路召回 + 融合排序.

检索策略:
- L3 优先: 私设匹配必须压倒一切外部资料 (权重 10x)
- 类型路由: 按查询类型决定检索哪层
- 混合检索: 向量相似度 + 关键词匹配 + 层级权重
"""

from dataclasses import dataclass, field
from typing import Optional

from .knowledge_base import KnowledgeBase, KnowledgeChunk, KnowledgeLayer

# 层级检索权重
LAYER_WEIGHTS: dict[KnowledgeLayer, float] = {
    KnowledgeLayer.L1_GENERAL: 1.0,
    KnowledgeLayer.L2_TECHNIQUE: 0.7,
    KnowledgeLayer.L3_PRIVATE: 10.0,  # 私设优先
}

# 默认检索参数
DEFAULT_TOP_K = {
    KnowledgeLayer.L1_GENERAL: 8,
    KnowledgeLayer.L2_TECHNIQUE: 5,
    KnowledgeLayer.L3_PRIVATE: 10,
}

# 相似度阈值
SIMILARITY_THRESHOLD = {
    KnowledgeLayer.L1_GENERAL: 0.70,
    KnowledgeLayer.L2_TECHNIQUE: 0.70,
    KnowledgeLayer.L3_PRIVATE: 0.75,  # 私设需要更高阈值 → 减少误报
}


@dataclass
class RetrievalResult:
    """单条检索结果."""
    chunk: KnowledgeChunk
    score: float                    # 综合得分
    vector_score: float = 0.0       # 向量相似度
    keyword_score: float = 0.0      # 关键词匹配度
    layer_weight: float = 1.0       # 层级权重

    @property
    def effective_score(self) -> float:
        """最终排序分数 = (向量分 + 关键词分) × 层级权重."""
        return (self.vector_score + self.keyword_score) * self.layer_weight


class MultiLayerRetriever:
    """多层混合检索器.

    检索流程:
    1. L3 先查 (always, 权重 10x)
    2. 按查询类型决定 L1/L2 的检索比例
    3. 三路召回结果融合排序
    """

    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base

    def retrieve(
        self,
        query: str,
        keywords: Optional[list[str]] = None,
        target_layers: Optional[list[KnowledgeLayer]] = None,
        top_k: int = 10,
        query_type: str = "hybrid",
    ) -> list[RetrievalResult]:
        """执行多层检索.

        Args:
            query: 检索查询字符串
            keywords: 额外的关键词
            target_layers: 目标知识层 (None=全部)
            top_k: 返回结果数
            query_type: keyword | semantic | hybrid

        Returns:
            排序后的检索结果列表
        """
        if target_layers is None:
            target_layers = list(KnowledgeLayer)

        all_results: list[RetrievalResult] = []

        for layer in target_layers:
            layer_k = DEFAULT_TOP_K.get(layer, 5)
            layer_results = self._retrieve_layer(
                query=query,
                keywords=keywords,
                layer=layer,
                top_k=layer_k,
                query_type=query_type,
            )
            all_results.extend(layer_results)

        # 融合排序: 按 effective_score 降序
        all_results.sort(key=lambda r: r.effective_score, reverse=True)

        return all_results[:top_k]

    def _retrieve_layer(
        self,
        query: str,
        keywords: Optional[list[str]],
        layer: KnowledgeLayer,
        top_k: int,
        query_type: str,
    ) -> list[RetrievalResult]:
        """在单个知识层内检索."""
        chunks = self.kb.get_chunks_by_layer(layer)
        if not chunks:
            return []

        results: list[RetrievalResult] = []
        threshold = SIMILARITY_THRESHOLD.get(layer, 0.70)
        layer_weight = LAYER_WEIGHTS.get(layer, 1.0)

        for chunk in chunks:
            # 向量相似度 (此处用关键词模拟, 实际应调用 embedding 模型)
            vector_sim = self._compute_keyword_similarity(query, chunk)

            # 关键词匹配度
            kw_score = 0.0
            if keywords:
                kw_score = KnowledgeBase._keyword_match_score(chunk, keywords)

            # 综合分
            if query_type == "keyword":
                score = kw_score
            elif query_type == "semantic":
                score = vector_sim
            else:  # hybrid
                score = 0.6 * vector_sim + 0.4 * kw_score

            if score >= threshold:
                results.append(RetrievalResult(
                    chunk=chunk,
                    score=score,
                    vector_score=vector_sim,
                    keyword_score=kw_score,
                    layer_weight=layer_weight,
                ))

        # 层内排序
        results.sort(key=lambda r: r.effective_score, reverse=True)
        return results[:top_k]

    @staticmethod
    def _compute_keyword_similarity(query: str, chunk: KnowledgeChunk) -> float:
        """计算查询与知识块的文本相似度 (简化实现).

        实际应使用: embedding 模型计算余弦相似度.
        """
        query_lower = query.lower()
        chunk_text = f"{chunk.content} {' '.join(chunk.keywords)}".lower()

        # 简单的 Jaccard 相似度 (字符级)
        query_chars = set(query_lower.split())
        chunk_chars = set(chunk_text.split())
        if not query_chars:
            return 0.0
        intersection = query_chars & chunk_chars
        union = query_chars | chunk_chars
        return len(intersection) / len(union) if union else 0.0

    def retrieve_for_step3(
        self,
        query: str,
        keywords: list[str],
        project_type: str,  # "fanfic" | "original"
    ) -> dict[str, list[RetrievalResult]]:
        """Step3 专用检索: 按项目类型决定检索策略."""
        results: dict[str, list[RetrievalResult]] = {}

        # 同人: L3 私设优先
        if project_type == "fanfic":
            results["private_settings"] = self.retrieve(
                query=query, keywords=keywords,
                target_layers=[KnowledgeLayer.L3_PRIVATE],
            )

        # L1 通用资料
        results["general"] = self.retrieve(
            query=query, keywords=keywords,
            target_layers=[KnowledgeLayer.L1_GENERAL],
        )

        # L2 写作技法 (可选的参考)
        results["technique"] = self.retrieve(
            query=query, keywords=keywords,
            target_layers=[KnowledgeLayer.L2_TECHNIQUE],
        )

        return results

    def retrieve_private_settings(
        self,
        query: str,
        project_id: str,
    ) -> list[RetrievalResult]:
        """检索项目私设 (用于冲突检测)."""
        all_results = self.retrieve(
            query=query,
            target_layers=[KnowledgeLayer.L3_PRIVATE],
            top_k=20,
        )
        # 过滤: 只看指定项目
        return [
            r for r in all_results
            if r.chunk.project_id == project_id
        ]
