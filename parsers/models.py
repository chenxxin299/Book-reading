"""
数据模型：Book、Chapter、ParsedBook
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Chapter:
    index: int                      # 章节序号（0-based）
    title: str                      # 章节标题
    content: str                    # 章节纯文本内容
    level: int = 1                  # 标题层级（1=章, 2=节, 3=小节）
    page_start: Optional[int] = None
    page_end: Optional[int] = None


@dataclass
class ParsedBook:
    title: str
    author: str
    language: str
    source_path: str
    chapters: List[Chapter] = field(default_factory=list)
    toc_text: str = ""              # 目录纯文本（给 LLM 看的）

    @property
    def total_chapters(self) -> int:
        return len(self.chapters)

    @property
    def total_chars(self) -> int:
        return sum(len(c.content) for c in self.chapters)
