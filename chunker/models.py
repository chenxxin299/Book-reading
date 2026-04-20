"""
Chunk 数据模型
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Chunk:
    chunk_id: str               # 唯一 ID（用于缓存命中）
    book_title: str
    author: str
    chapter_title: str
    chapter_index: int
    sub_chunk_index: int        # 该章节内第几片（0-based）
    total_sub_chunks: int       # 该章节共几片
    context_header: str         # 提供给 LLM 的上下文提示
    content: str                # 实际文本内容
    token_count: int = 0
    prev_summary: Optional[str] = None  # 前一 chunk 的简要摘要
    toc_text: str = ""
