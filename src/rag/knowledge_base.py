"""知识库管理 — 三层知识库的初始化、增量更新、Chunk策略."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import uuid4


class KnowledgeLayer(str, Enum):
    """三层知识库."""
    L1_GENERAL = "l1_general"       # 通用资料
    L2_TECHNIQUE = "l2_technique"   # 写作技法
    L3_PRIVATE = "l3_private"       # 项目私设


@dataclass
class KnowledgeChunk:
    """知识块 — 存入向量库的最小单元."""

    chunk_id: str = field(default_factory=lambda: f"chunk-{uuid4().hex[:12]}")
    layer: KnowledgeLayer = KnowledgeLayer.L1_GENERAL
    content: str = ""
    embedding: Optional[list[float]] = None

    # 元数据
    source_title: str = ""
    source_url: str = ""
    source_author: str = ""
    domain: str = ""                # L1: history/geography/culture/science/literature
    category: str = ""              # L2: narrative/character/dialogue/pacing/structure
    project_id: str = ""            # L3: 所属项目ID
    card_id: str = ""               # L3: 来源设定卡ID

    # 检索用
    keywords: list[str] = field(default_factory=list)
    reliability: float = 1.0        # 来源权威度 (0.0-1.0)
    chunk_index: int = 0            # 在文档中的序号

    # 检索权重
    base_weight: float = 1.0        # 层级基础权重

    def __post_init__(self):
        """根据层级设置基础权重."""
        weights = {
            KnowledgeLayer.L1_GENERAL: 1.0,
            KnowledgeLayer.L2_TECHNIQUE: 0.7,
            KnowledgeLayer.L3_PRIVATE: 10.0,  # 私设权重压倒一切
        }
        self.base_weight = weights.get(self.layer, 1.0)

    @property
    def effective_weight(self) -> float:
        """有效检索权重 = 基础权重 × 来源权威度."""
        return self.base_weight * self.reliability

    def to_metadata(self) -> dict:
        """转为 ChromaDB 兼容的元数据格式."""
        return {
            "chunk_id": self.chunk_id,
            "layer": self.layer.value,
            "source_title": self.source_title,
            "source_url": self.source_url,
            "domain": self.domain,
            "category": self.category,
            "project_id": self.project_id,
            "card_id": self.card_id,
            "reliability": self.reliability,
            "chunk_index": self.chunk_index,
            "keywords": ",".join(self.keywords),
        }


class KnowledgeBase:
    """三层知识库管理器.

    负责:
    - 知识库初始化
    - 三层数据的 CRUD
    - Chunk 策略管理
    - 增量更新
    """

    def __init__(self, persist_dir: str = "./data/knowledge"):
        self.persist_dir = persist_dir
        self._collections: dict[KnowledgeLayer, list[KnowledgeChunk]] = {
            KnowledgeLayer.L1_GENERAL: [],
            KnowledgeLayer.L2_TECHNIQUE: [],
            KnowledgeLayer.L3_PRIVATE: [],
        }

    def add_chunk(self, chunk: KnowledgeChunk) -> None:
        """添加知识块到对应层级."""
        self._collections[chunk.layer].append(chunk)

    def add_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        """批量添加."""
        for chunk in chunks:
            self.add_chunk(chunk)

    def get_chunks_by_layer(self, layer: KnowledgeLayer) -> list[KnowledgeChunk]:
        """获取某层的所有知识块."""
        return self._collections.get(layer, [])

    def get_chunk_by_id(self, chunk_id: str) -> Optional[KnowledgeChunk]:
        """按 ID 查找."""
        for chunks in self._collections.values():
            for chunk in chunks:
                if chunk.chunk_id == chunk_id:
                    return chunk
        return None

    def remove_chunk(self, chunk_id: str) -> bool:
        """移除知识块."""
        for layer, chunks in self._collections.items():
            for i, chunk in enumerate(chunks):
                if chunk.chunk_id == chunk_id:
                    self._collections[layer].pop(i)
                    return True
        return False

    def update_chunk(self, chunk_id: str, updates: dict) -> Optional[KnowledgeChunk]:
        """更新知识块."""
        chunk = self.get_chunk_by_id(chunk_id)
        if chunk is None:
            return None
        for key, value in updates.items():
            if hasattr(chunk, key):
                setattr(chunk, key, value)
        return chunk

    def search_by_keywords(
        self,
        keywords: list[str],
        layers: Optional[list[KnowledgeLayer]] = None,
        limit: int = 10,
    ) -> list[KnowledgeChunk]:
        """关键词检索 (精确匹配)."""
        if layers is None:
            layers = list(KnowledgeLayer)

        results = []
        for layer in layers:
            for chunk in self._collections.get(layer, []):
                score = self._keyword_match_score(chunk, keywords)
                if score > 0:
                    results.append((chunk, score))

        # 排序: 先按 effective_weight, 再按匹配分数
        results.sort(key=lambda x: (x[0].effective_weight, x[1]), reverse=True)
        return [chunk for chunk, _ in results[:limit]]

    @staticmethod
    def _keyword_match_score(chunk: KnowledgeChunk, keywords: list[str]) -> float:
        """计算关键词匹配度."""
        if not keywords:
            return 0.0
        chunk_text = f"{chunk.content} {' '.join(chunk.keywords)}".lower()
        hits = sum(1 for kw in keywords if kw.lower() in chunk_text)
        return hits / len(keywords)

    @property
    def stats(self) -> dict:
        """知识库统计."""
        return {
            "total_chunks": sum(len(v) for v in self._collections.values()),
            "l1_general": len(self._collections[KnowledgeLayer.L1_GENERAL]),
            "l2_technique": len(self._collections[KnowledgeLayer.L2_TECHNIQUE]),
            "l3_private": len(self._collections[KnowledgeLayer.L3_PRIVATE]),
        }
