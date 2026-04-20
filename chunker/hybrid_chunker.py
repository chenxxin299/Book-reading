"""
混合分块策略：
  1. 章节 ≤ max_tokens → 整章作为一个 Chunk
  2. 章节 > max_tokens → 按段落合并，超出则滑动窗口切分（含 overlap）
"""
import hashlib
from typing import List, Optional

import tiktoken

from parsers.models import ParsedBook, Chapter
from .models import Chunk


class HybridChunker:
    def __init__(
        self,
        max_tokens: int = 6000,
        overlap_tokens: int = 500,
        min_tokens: int = 300,
        encoding_name: str = "cl100k_base",
    ):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_tokens = min_tokens
        self._enc = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        return len(self._enc.encode(text))

    def chunk_book(self, book: ParsedBook) -> List[Chunk]:
        all_chunks: List[Chunk] = []
        prev_summary: Optional[str] = None

        for chapter in book.chapters:
            chapter_chunks = self._chunk_chapter(
                chapter=chapter,
                book=book,
                prev_summary=prev_summary,
            )
            all_chunks.extend(chapter_chunks)
            # 用最后一块的前200字作为下一章的 prev_summary
            if chapter_chunks:
                prev_summary = chapter.content[:300].replace("\n", " ")

        return all_chunks

    # ── 内部方法 ─────────────────────────────────────────────

    def _chunk_chapter(
        self,
        chapter: Chapter,
        book: ParsedBook,
        prev_summary: Optional[str],
    ) -> List[Chunk]:
        token_count = self.count_tokens(chapter.content)

        if token_count <= self.max_tokens:
            # 整章作为单个 Chunk
            return [self._make_chunk(
                book=book, chapter=chapter,
                sub_index=0, total_sub=1,
                content=chapter.content,
                token_count=token_count,
                prev_summary=prev_summary,
            )]
        else:
            # 按段落拆分后滑动窗口合并
            return self._sliding_window(
                book=book, chapter=chapter, prev_summary=prev_summary
            )

    def _sliding_window(
        self,
        book: ParsedBook,
        chapter: Chapter,
        prev_summary: Optional[str],
    ) -> List[Chunk]:
        paragraphs = [p.strip() for p in chapter.content.split("\n\n") if p.strip()]
        chunks: List[Chunk] = []
        buffer: List[str] = []
        buffer_tokens = 0

        def flush(sub_index: int, total_sub: int, _prev: Optional[str]):
            text = "\n\n".join(buffer)
            chunks.append(self._make_chunk(
                book=book, chapter=chapter,
                sub_index=sub_index, total_sub=total_sub,
                content=text, token_count=buffer_tokens,
                prev_summary=_prev,
            ))

        for para in paragraphs:
            para_tokens = self.count_tokens(para)
            if buffer_tokens + para_tokens > self.max_tokens and buffer:
                flush(len(chunks), -1, prev_summary)  # total_sub 后填
                # 保留最后 overlap_tokens 的内容
                overlap_buf: List[str] = []
                overlap_t = 0
                for seg in reversed(buffer):
                    st = self.count_tokens(seg)
                    if overlap_t + st <= self.overlap_tokens:
                        overlap_buf.insert(0, seg)
                        overlap_t += st
                    else:
                        break
                buffer = overlap_buf
                buffer_tokens = overlap_t
                prev_summary = chunks[-1].content[:300].replace("\n", " ")

            buffer.append(para)
            buffer_tokens += para_tokens

        if buffer:
            flush(len(chunks), -1, prev_summary)

        # 回填 total_sub_chunks
        total = len(chunks)
        for i, c in enumerate(chunks):
            object.__setattr__(c, "sub_chunk_index", i) if hasattr(c, "__setattr__") else None
            # dataclass 是可变的，直接赋值
            c.sub_chunk_index = i
            c.total_sub_chunks = total

        return chunks

    def _make_chunk(
        self,
        book: ParsedBook,
        chapter: Chapter,
        sub_index: int,
        total_sub: int,
        content: str,
        token_count: int,
        prev_summary: Optional[str],
    ) -> Chunk:
        chunk_id = hashlib.sha256(
            f"{book.source_path}|{chapter.index}|{sub_index}|{len(content)}".encode()
        ).hexdigest()[:16]

        context_header = self._build_context_header(
            book=book,
            chapter=chapter,
            sub_index=sub_index,
            total_sub=total_sub,
            prev_summary=prev_summary,
        )

        return Chunk(
            chunk_id=chunk_id,
            book_title=book.title,
            author=book.author,
            chapter_title=chapter.title,
            chapter_index=chapter.index,
            sub_chunk_index=sub_index,
            total_sub_chunks=total_sub,
            context_header=context_header,
            content=content,
            token_count=token_count,
            prev_summary=prev_summary,
            toc_text=book.toc_text,
        )

    def _build_context_header(
        self,
        book: ParsedBook,
        chapter: Chapter,
        sub_index: int,
        total_sub: int,
        prev_summary: Optional[str],
    ) -> str:
        parts = [
            f"【书名】：《{book.title}》",
            f"【作者】：{book.author}",
            f"【当前位置】：第 {chapter.index + 1} 章《{chapter.title}》",
        ]
        if total_sub > 1:
            parts.append(f"【分片】：第 {sub_index + 1} / {total_sub} 片")
        if prev_summary:
            parts.append(f"【前文摘要】：{prev_summary[:200]}")
        if book.toc_text:
            parts.append(f"【全书目录】：\n{book.toc_text[:800]}")
        return "\n".join(parts)
