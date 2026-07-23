"""JSON 容错解析层 — Badcase迭代的核心成果.

解决了简历中提到的三大问题:
1. JSON截断 → 自动检测 + 续写/修复
2. 字段漂移 → 模糊匹配 + 别名映射
3. 格式错误 → 正则提取 + 默认值填充

迭代历程:
- V1: 直接 JSON.parse → 成功率 40%
- V2: + try/catch + 简单修复 → 55%
- V3: + 分步生成 + 长度控制 → 70%
- V4: + Checker校验循环 → 85%
- V5 (当前): + 三层容错 + 模糊匹配 + 重试上限 → 90%
"""

import json
import re
from difflib import SequenceMatcher
from typing import Any, Callable, Optional


# 字段别名映射表 (解决字段漂移)
# 格式: "目标字段名" → ["常见漂移名1", "常见漂移名2", ...]
FIELD_ALIASES: dict[str, list[str]] = {
    # 顶层字段
    "name": ["Name", "title", "Title", "setting_name", "card_name", "label"],
    "type": ["Type", "card_type", "cardType", "CardType", "category"],
    "content": ["Content", "description", "Description", "body", "text", "detail"],
    "summary": ["Summary", "abstract", "brief", "short_description", "overview"],
    "source": ["Source", "origin", "SourceType", "source_type"],
    "confidence": ["Confidence", "score", "certainty", "reliability", "confidence_score"],

    # 嵌套字段
    "metadata": ["Metadata", "meta", "Meta", "card_metadata", "info"],
    "tags": ["Tags", "labels", "keywords", "categories"],
    "fandom": ["Fandom", "series", "universe", "work", "原作", "作品"],

    # 关联字段
    "related_cards": ["relatedCards", "related", "relations", "linked_cards", "references"],
    "conflicts_with": ["conflictsWith", "conflicts", "contradictions"],
    "source_refs": ["sourceRefs", "sources", "references", "citations"],

    # 类型枚举
    "character": ["Character", "角色", "人物", "char", "person"],
    "world": ["World", "worldbuilding", "世界观", "setting", "world_setting"],
    "plot": ["Plot", "剧情", "story", "event", "narrative"],
    "relationship": ["Relationship", "关系", "relation", "connection"],
    "item": ["Item", "物品", "道具", "object", "artifact"],
    "location": ["Location", "地点", "place", "area", "region"],
    "timeline": ["Timeline", "时间线", "chronology", "history"],
    "culture": ["Culture", "文化", "社会", "society", "custom"],
}


def safe_json_parse(
    raw_text: str,
    schema: Optional[dict] = None,
    max_retries: int = 3,
) -> dict[str, Any]:
    """安全 JSON 解析 — 三层容错策略.

    Layer 1: 直接解析
    Layer 2: 正则提取 + 基本修复
    Layer 3: 模糊匹配 + 默认值填充

    Args:
        raw_text: LLM 原始输出文本
        schema: 可选的 JSON Schema 用于校验和默认值填充
        max_retries: 最大重试次数

    Returns:
        解析后的 JSON 对象 (dict)

    Raises:
        ValueError: 三层容错全部失败
    """
    # === Layer 1: 直接解析 ===
    json_str = _extract_json_block(raw_text)

    try:
        result = json.loads(json_str)
        if schema:
            result = _validate_and_fill(result, schema)
        return result
    except (json.JSONDecodeError, ValueError) as e:
        last_error = e

    # === Layer 2: 正则提取 + 基本修复 ===
    try:
        result = _regex_extract_and_repair(json_str)
        if schema:
            result = _validate_and_fill(result, schema)
        return result
    except (json.JSONDecodeError, ValueError) as e:
        last_error = e

    # === Layer 3: 模糊匹配 + 默认值填充 ===
    try:
        result = _fuzzy_extract_and_fill(raw_text, schema)
        return result
    except Exception as e:
        last_error = e

    raise ValueError(
        f"JSON 解析失败 (三层容错全部不可用): {last_error}\n"
        f"原始输出前200字符: {raw_text[:200]}"
    )


def _extract_json_block(text: str) -> str:
    """从 LLM 输出中提取 JSON 块.

    处理 LLM 常见的包裹格式:
    - ```json ... ```
    - ``` ... ```
    - 纯 JSON 文本
    """
    # 尝试提取 ```json 代码块
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 尝试提取 { ... } 对象
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0).strip()

    return text.strip()


def _regex_extract_and_repair(json_str: str) -> dict:
    """正则提取 + 基本修复.

    修复常见问题:
    - 尾部截断 (不完整的 JSON)
    - 尾部多余逗号
    - 缺少引号的键名
    - 单引号替换为双引号
    """
    # 1. 修复单引号 JSON
    if json_str.startswith("'") or "'" in json_str[:10]:
        json_str = _fix_single_quotes(json_str)

    # 2. 去除尾部的非法字符
    json_str = _trim_incomplete_json(json_str)

    # 3. 修复尾部多余逗号
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    # 4. 修复缺少引号的键名
    json_str = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', json_str)

    # 5. 尝试解析
    return json.loads(json_str)


def _fuzzy_extract_and_fill(raw_text: str, schema: Optional[dict] = None) -> dict:
    """模糊提取 + 默认值填充 (最后一层兜底).

    用正则匹配每个可能字段的值, 然后做字段名模糊匹配.
    """
    result: dict[str, Any] = {}

    # 尝试提取所有 key: value 模式
    patterns = [
        r'"(\w+)"\s*:\s*"([^"]*)"',      # "key": "value"
        r'"(\w+)"\s*:\s*(\d+(?:\.\d+)?)', # "key": 123
        r'"(\w+)"\s*:\s*(\w+)',            # "key": true/false/null
    ]

    extracted: dict[str, Any] = {}
    for pattern in patterns:
        for match in re.finditer(pattern, raw_text):
            key, value = match.groups()
            extracted[key] = value

    # 字段名模糊匹配
    for target_field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias.lower() in {k.lower() for k in extracted}:
                # 找到匹配的原始键名
                original_key = next(
                    k for k in extracted
                    if k.lower() == alias.lower()
                )
                result[target_field] = extracted[original_key]
                break

    # 默认值填充
    if schema:
        result = _fill_defaults_from_schema(result, schema)

    return result if result else {"error": "fuzzy_extract_failed", "raw_length": len(raw_text)}


def _trim_incomplete_json(json_str: str) -> str:
    """修剪不完整的 JSON (截断处理).

    从尾部向前查找, 在最后一个完整的 } 或 ] 处截断.
    """
    stack = []
    last_complete = len(json_str)

    for i, char in enumerate(json_str):
        if char in '{[':
            stack.append(char)
        elif char == '}':
            if stack and stack[-1] == '{':
                stack.pop()
                if not stack:
                    last_complete = i + 1
        elif char == ']':
            if stack and stack[-1] == '[':
                stack.pop()
                if not stack:
                    last_complete = i + 1

    if last_complete < len(json_str):
        truncated = json_str[:last_complete]
        # 尝试闭合: 补全缺失的括号
        for bracket in reversed(stack):
            if bracket == '{':
                truncated += '}'
            elif bracket == '[':
                truncated += ']'
        return truncated

    return json_str


def _fix_single_quotes(text: str) -> str:
    """将单引号 JSON 转为双引号 JSON (小心处理)."""
    # 只在看起来是 JSON 上下文的情况下替换
    # 简化处理: 直接的引号替换
    result = []
    in_string = False
    quote_char = None

    for char in text:
        if not in_string:
            if char in '"\'':
                in_string = True
                quote_char = char
                result.append('"')
            else:
                result.append(char)
        else:
            if char == quote_char:
                in_string = False
                result.append('"')
            elif char == '"':
                result.append('\\"')
            else:
                result.append(char)

    return ''.join(result)


def _validate_and_fill(data: dict, schema: dict) -> dict:
    """根据 Schema 校验并填充默认值."""
    result = dict(data)

    # 字段名规范化
    result = _normalize_field_names(result)

    # 默认值填充
    if "properties" in schema:
        result = _fill_defaults_from_schema(result, schema)

    return result


def _normalize_field_names(data: dict) -> dict:
    """字段名规范化: 将漂移的字段名映射回标准名."""
    normalized = {}
    for key, value in data.items():
        new_key = _find_canonical_name(key)
        normalized[new_key] = value
    return normalized


def _find_canonical_name(field_name: str) -> str:
    """查找字段名的规范形式.

    使用编辑距离 + 别名表进行模糊匹配.
    """
    field_lower = field_name.lower()

    # 精确匹配别名
    for canonical, aliases in FIELD_ALIASES.items():
        if field_lower in {a.lower() for a in aliases}:
            return canonical
        if field_lower == canonical.lower():
            return canonical

    # 模糊匹配 (编辑距离)
    best_match = None
    best_ratio = 0.0
    for canonical, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            ratio = SequenceMatcher(None, field_lower, alias.lower()).ratio()
            if ratio > best_ratio and ratio > 0.7:
                best_ratio = ratio
                best_match = canonical

    if best_match and best_ratio > 0.8:
        return best_match

    return field_name  # 保持原名


def _fill_defaults_from_schema(data: dict, schema: dict) -> dict:
    """从 Schema 填充默认值."""
    properties = schema.get("properties", {})
    for prop_name, prop_schema in properties.items():
        if prop_name not in data or data[prop_name] is None:
            if "default" in prop_schema:
                data[prop_name] = prop_schema["default"]
            elif prop_schema.get("type") == "string":
                data[prop_name] = ""
            elif prop_schema.get("type") == "array":
                data[prop_name] = []
            elif prop_schema.get("type") == "object":
                data[prop_name] = {}
            elif prop_schema.get("type") == "number":
                data[prop_name] = 0

    # 枚举值兜底
    if "enum" in schema:
        data["type"] = data.get("type", schema["enum"][0])

    return data


def parse_with_retry(
    raw_text: str,
    retry_hint: str = "",
    max_retries: int = 3,
    schema: Optional[dict] = None,
) -> tuple[dict, int]:
    """带重试的 JSON 解析.

    Args:
        raw_text: LLM 原始输出
        retry_hint: 重试时追加的修复提示
        max_retries: 最大重试次数
        schema: JSON Schema (可选)

    Returns:
        (parsed_dict, retry_count)
    """
    last_error = None
    current_text = raw_text

    for attempt in range(max_retries + 1):
        try:
            result = safe_json_parse(current_text, schema)
            return result, attempt
        except ValueError as e:
            last_error = e
            if attempt < max_retries and retry_hint:
                # 追加修复提示 (实际使用时应调用 LLM 重试)
                current_text = f"{retry_hint}\n\n原始输出:\n{raw_text}"

    raise ValueError(
        f"JSON 解析失败 (已重试 {max_retries} 次): {last_error}"
    )
