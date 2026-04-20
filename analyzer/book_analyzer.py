"""
全书综合分析器 - 将多个 ChunkAnalysis 聚合后进行全书分析
"""
import json
from loguru import logger

from parsers.models import ParsedBook
from .claude_client import ClaudeClient
from .models import (
    BookAnalysis, ChunkAnalysis, ConceptItem,
    CorePoint, KeyQuestion, Inspiration, MindMapNode
)
from .prompts import BOOK_SYNTHESIS_SYSTEM, make_synthesis_user_prompt


class BookAnalyzer:
    def __init__(self, client: ClaudeClient):
        self.client = client

    def analyze(self, book: ParsedBook, chunk_analyses: list[ChunkAnalysis]) -> BookAnalysis:
        """聚合所有章节分析，进行全书综合分析"""
        logger.info(f"[综合分析] 开始全书综合分析《{book.title}》...")

        # 构建章节摘要汇总（压缩后送给 LLM）
        chunks_summary = self._build_chunks_summary(chunk_analyses)

        user_prompt = make_synthesis_user_prompt(book.title, book.author, chunks_summary)
        raw = self.client.call(
            system_prompt=BOOK_SYNTHESIS_SYSTEM,
            user_content=user_prompt,
            expect_json=True,
        )

        # 合并代表每章的第一个 chunk（用于章节概要展示）
        chapter_summaries = self._dedupe_chapters(chunk_analyses)

        return self._parse_result(book, raw, chapter_summaries)

    # ── 内部方法 ─────────────────────────────────────────────────────────────

    def _build_chunks_summary(self, analyses: list[ChunkAnalysis]) -> str:
        """将各章分析压缩为文字摘要，送给综合分析用"""
        lines = []
        for a in analyses:
            sub = f"（片段 {a.sub_chunk_index + 1}）" if a.sub_chunk_index > 0 else ""
            lines.append(
                f"### 第 {a.chapter_index + 1} 章《{a.chapter_title}》{sub}\n"
                f"**摘要**: {a.chapter_summary}\n"
                f"**核心论点**: {'; '.join(a.key_arguments[:3])}\n"
                f"**关键概念**: {', '.join(c.name for c in a.key_concepts[:4])}\n"
                f"**关键词**: {', '.join(a.keywords[:6])}\n"
            )
        return "\n".join(lines)

    def _dedupe_chapters(self, analyses: list[ChunkAnalysis]) -> list[ChunkAnalysis]:
        """每章保留第一个 chunk 的分析（用于章节概要）"""
        seen: dict[int, ChunkAnalysis] = {}
        for a in analyses:
            if a.chapter_index not in seen:
                seen[a.chapter_index] = a
        return list(seen.values())

    def _parse_result(
        self,
        book: ParsedBook,
        raw: dict,
        chapter_summaries: list[ChunkAnalysis],
    ) -> BookAnalysis:
        core_points = [
            CorePoint(title=p.get("title", ""), description=p.get("description", ""))
            for p in raw.get("core_points", []) if isinstance(p, dict)
        ]
        key_concepts = [
            ConceptItem(
                name=c.get("name", ""),
                explanation=c.get("explanation", ""),
                importance=5,
                related_chapters=c.get("related_chapters", []),
            )
            for c in raw.get("key_concepts", []) if isinstance(c, dict)
        ]
        key_questions = [
            KeyQuestion(
                question=q.get("question", "") if isinstance(q, dict) else str(q),
                context=q.get("context", "") if isinstance(q, dict) else "",
            )
            for q in raw.get("key_questions", [])
        ]
        inspirations = [
            Inspiration(
                category=i.get("category", "启发") if isinstance(i, dict) else "启发",
                content=i.get("content", "") if isinstance(i, dict) else str(i),
            )
            for i in raw.get("inspirations", [])
        ]

        # 解析思维导图
        mind_map_root = self._parse_mind_map(raw.get("mind_map", {}), book.title)

        return BookAnalysis(
            book_title=book.title,
            author=book.author,
            book_theme=raw.get("book_theme", ""),
            core_points=core_points,
            mind_map_root=mind_map_root,
            key_concepts=key_concepts,
            key_questions=key_questions,
            inspirations=inspirations,
            related_books=raw.get("related_books", []),
            chapter_summaries=chapter_summaries,
            raw=raw,
        )

    def _parse_mind_map(self, mm: dict, book_title: str) -> MindMapNode:
        root = MindMapNode(name=mm.get("root", book_title))
        for branch in mm.get("branches", []):
            b_node = MindMapNode(name=branch.get("name", ""))
            for child in branch.get("children", []):
                b_node.children.append(MindMapNode(
                    name=child.get("name", ""),
                    detail=child.get("detail", ""),
                ))
            root.children.append(b_node)
        return root
