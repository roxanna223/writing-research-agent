"""Embedding 服务封装 — 统一文本向量化接口.

支持:
- OpenAI text-embedding-3-small (云端, 需要 API key)
- 本地 fallback: TF-IDF + 关键词匹配 (零依赖, 始终可用)
"""

import hashlib
import logging
import math
import os
import re
from collections import Counter
from typing import Optional

logger = logging.getLogger(__name__)


class Embedder:
    """文本向量化服务.

    优先使用 API 模型, 无 API key 时自动降级为本地 TF-IDF.
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        dims: int = 512,
        use_api: bool = True,
    ):
        self.model = model
        self.dims = dims
        self.use_api = use_api
        self._api_client = None
        self._corpus_vocab: dict[str, int] = {}
        self._corpus_docs: list[str] = []

    def embed(self, text: str) -> list[float]:
        """将文本转为向量."""
        if self.use_api:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                return self._embed_api(text)

        # 本地 fallback
        return self._embed_local(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量向量化."""
        return [self.embed(t) for t in texts]

    def fit_corpus(self, documents: list[str]) -> None:
        """在语料库上拟合词汇表 (TF-IDF 需要)."""
        self._corpus_docs = documents
        self._corpus_vocab = _build_vocabulary(documents)

    # --- API 实现 ---
    def _embed_api(self, text: str) -> list[float]:
        """调用 OpenAI Embedding API."""
        try:
            from openai import OpenAI
        except ImportError:
            logger.warning("openai not installed, falling back to local embedding")
            return self._embed_local(text)

        if self._api_client is None:
            self._api_client = OpenAI()

        response = self._api_client.embeddings.create(
            model=self.model,
            input=text,
            dimensions=self.dims,
        )
        return response.data[0].embedding

    # --- 本地 TF-IDF 实现 ---
    def _embed_local(self, text: str) -> list[float]:
        """本地 TF-IDF 向量化 (确定性, 零外部依赖).

        TF-IDF 计算:
        - TF: 词在本文中的频率
        - IDF: 逆文档频率 (基于已拟合的语料库)
        - 输出: 固定维度的稀疏向量
        """
        tokens = _tokenize(text)
        if not tokens:
            return [0.0] * self.dims

        # TF 计算
        tf = Counter(tokens)
        max_tf = max(tf.values()) if tf else 1

        # 向量化 (通过 hash 映射到固定维度)
        vector = [0.0] * self.dims
        for token, count in tf.items():
            # 跳过停用词
            if len(token) <= 1:
                continue

            # TF 归一化
            tf_norm = count / max_tf

            # IDF (简化)
            if self._corpus_vocab:
                idf = math.log(
                    (len(self._corpus_docs) + 1)
                    / (self._corpus_vocab.get(token, 0) + 1)
                ) + 1
            else:
                idf = 1.0

            # Hash 到固定维度
            idx = _hash_to_dim(token, self.dims)
            vector[idx] += tf_norm * idf

        # L2 归一化
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    def similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """计算两个向量的余弦相似度."""
        if len(vec1) != len(vec2):
            raise ValueError(f"Dimension mismatch: {len(vec1)} vs {len(vec2)}")
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)


# --- 本地工具函数 ---

def _tokenize(text: str) -> list[str]:
    """中文+英文混合分词."""
    # 提取中文单字 + 英文单词
    tokens = []
    # 英文单词
    tokens.extend(re.findall(r'[a-zA-Z]{2,}', text.lower()))
    # 中文单字+双字组合
    chinese = re.findall(r'[一-鿿]+', text)
    for segment in chinese:
        for char in segment:
            tokens.append(char)
        for i in range(len(segment) - 1):
            tokens.append(segment[i:i + 2])
    return tokens


def _build_vocabulary(documents: list[str]) -> dict[str, int]:
    """构建语料库词汇表 (文档频率)."""
    vocab: dict[str, int] = {}
    for doc in documents:
        seen = set()
        for token in _tokenize(doc):
            if token not in seen and len(token) > 1:
                vocab[token] = vocab.get(token, 0) + 1
                seen.add(token)
    return vocab


def _hash_to_dim(token: str, dims: int) -> int:
    """将 token 哈希到固定维度索引."""
    h = hashlib.md5(token.encode()).hexdigest()
    return int(h, 16) % dims
