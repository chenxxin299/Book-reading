"""
分析结果数据模型
"""
from dataclasses import dataclass, field
from typing import List, Optional, Any


@dataclass
class ConceptItem:
    name: str
    explanation: str
    importance: int = 3
    related_chapters: List[str] = field(default_factory=list)


@dataclass
class CorePoint:
    title: str
    description: str


@dataclass
class KeyQuestion:
    question: str
    context: str = ""


@dataclass
class Inspiration:
    category: str
    content: str


@dataclass
class MindMapNode:
    name: str
    detail: str = ""
    children: List["MindMapNode"] = field(default_factory=list)


@dataclass
class ChunkAnalysis:
    """单个 Chunk 的分析结果"""
    chunk_id: str
    chapter_index: int
    chapter_title: str
    sub_chunk_index: int
    chapter_summary: str
    key_concepts: List[ConceptItem] = field(default_factory=list)
    key_arguments: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    raw: Any = None  # 原始 JSON 响应


@dataclass
class BookAnalysis:
    """全书综合分析结果"""
    book_title: str
    author: str
    book_theme: str
    core_points: List[CorePoint] = field(default_factory=list)
    mind_map_root: Optional[MindMapNode] = None
    key_concepts: List[ConceptItem] = field(default_factory=list)
    key_questions: List[KeyQuestion] = field(default_factory=list)
    inspirations: List[Inspiration] = field(default_factory=list)
    related_books: List[str] = field(default_factory=list)
    chapter_summaries: List[ChunkAnalysis] = field(default_factory=list)
    raw: Any = None
