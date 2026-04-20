"""
PDF 解析器 - 使用 PyMuPDF (fitz)
策略：提取 TOC 结构 → 按章节切分内容
"""
import re
from pathlib import Path
from typing import List, Tuple

import fitz  # pymupdf

from .base import BaseParser
from .models import Chapter, ParsedBook


class PDFParser(BaseParser):
    def can_handle(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() == ".pdf"

    def parse(self, file_path: str) -> ParsedBook:
        doc = fitz.open(file_path)
        title, author = self._extract_metadata(doc)
        toc = doc.get_toc()  # [[level, title, page], ...]

        if toc:
            chapters = self._parse_with_toc(doc, toc)
        else:
            chapters = self._parse_without_toc(doc)

        toc_text = self._build_toc_text(chapters)
        doc.close()

        return ParsedBook(
            title=title,
            author=author,
            language="zh",
            source_path=file_path,
            chapters=chapters,
            toc_text=toc_text,
        )

    # ── 内部方法 ─────────────────────────────────────────────

    def _extract_metadata(self, doc: fitz.Document) -> Tuple[str, str]:
        meta = doc.metadata or {}
        title = meta.get("title") or Path(doc.name).stem
        author = meta.get("author") or "未知作者"
        return title.strip(), author.strip()

    def _parse_with_toc(self, doc: fitz.Document, toc: list) -> List[Chapter]:
        """基于目录结构切分章节"""
        chapters: List[Chapter] = []
        total_pages = len(doc)

        # 只保留 level 1-2 的条目，过滤过深层级
        entries = [(lvl, title, pg - 1) for lvl, title, pg in toc if lvl <= 2]

        for i, (level, title, page_start) in enumerate(entries):
            page_end = entries[i + 1][2] if i + 1 < len(entries) else total_pages
            page_end = min(page_end, total_pages)

            content = self._extract_pages_text(doc, page_start, page_end)
            if len(content.strip()) < 50:
                continue  # 跳过空章节

            chapters.append(Chapter(
                index=len(chapters),
                title=self._clean_title(title),
                content=content,
                level=level,
                page_start=page_start + 1,
                page_end=page_end,
            ))

        return chapters

    def _parse_without_toc(self, doc: fitz.Document) -> List[Chapter]:
        """无目录时：按页面标题启发式切分"""
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"

        # 用正则识别章节标题（如 "第一章"、"Chapter 1"、"1."）
        pattern = re.compile(
            r"(?m)^(第[零一二三四五六七八九十百\d]+[章节部篇][\s\S]{0,30}|"
            r"Chapter\s+\d+[\s\S]{0,50}|"
            r"\d+\.\s+[A-Z\u4e00-\u9fff][\s\S]{0,50})$"
        )
        splits = list(pattern.finditer(full_text))

        if not splits:
            # 完全无结构：按固定字数切分作为单章
            return [Chapter(index=0, title="全文", content=full_text, level=1)]

        chapters: List[Chapter] = []
        for i, match in enumerate(splits):
            start = match.start()
            end = splits[i + 1].start() if i + 1 < len(splits) else len(full_text)
            content = full_text[start:end].strip()
            if len(content) > 100:
                chapters.append(Chapter(
                    index=len(chapters),
                    title=self._clean_title(match.group(0).strip()[:50]),
                    content=content,
                    level=1,
                ))
        return chapters

    def _extract_pages_text(self, doc: fitz.Document, start: int, end: int) -> str:
        texts = []
        for page_num in range(start, end):
            if page_num < len(doc):
                texts.append(doc[page_num].get_text("text"))
        return "\n".join(texts)

    def _clean_title(self, title: str) -> str:
        return re.sub(r"\s+", " ", title).strip()

    def _build_toc_text(self, chapters: List[Chapter]) -> str:
        lines = []
        for ch in chapters:
            indent = "  " * (ch.level - 1)
            lines.append(f"{indent}{ch.index + 1}. {ch.title}")
        return "\n".join(lines)
