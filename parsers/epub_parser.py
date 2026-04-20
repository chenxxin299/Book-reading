"""
EPUB 解析器 - 使用 ebooklib + BeautifulSoup
"""
import re
from pathlib import Path
from typing import List

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

from .base import BaseParser
from .models import Chapter, ParsedBook


class EPUBParser(BaseParser):
    def can_handle(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in (".epub",)

    def parse(self, file_path: str) -> ParsedBook:
        book = epub.read_epub(file_path, options={"ignore_ncx": False})

        title = self._get_meta(book, "title") or Path(file_path).stem
        author = self._get_meta(book, "creator") or "未知作者"

        chapters = self._extract_chapters(book)
        toc_text = self._build_toc_text(chapters)

        return ParsedBook(
            title=title,
            author=author,
            language="zh",
            source_path=file_path,
            chapters=chapters,
            toc_text=toc_text,
        )

    # ── 内部方法 ─────────────────────────────────────────────

    def _get_meta(self, book: epub.EpubBook, name: str) -> str:
        items = book.get_metadata("DC", name)
        if items:
            val = items[0][0]
            return val.strip() if isinstance(val, str) else ""
        return ""

    def _extract_chapters(self, book: epub.EpubBook) -> List[Chapter]:
        chapters: List[Chapter] = []

        # 按 spine 顺序遍历文档
        for item_id, _ in book.spine:
            item = book.get_item_with_id(item_id)
            if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
                continue

            html_content = item.get_content().decode("utf-8", errors="replace")
            soup = BeautifulSoup(html_content, "lxml")

            # 提取标题
            title_tag = soup.find(["h1", "h2", "h3"])
            title = title_tag.get_text(strip=True) if title_tag else item.get_name()
            level = int(title_tag.name[1]) if title_tag else 1

            # 提取纯文本内容
            content = self._html_to_text(soup)
            if len(content.strip()) < 50:
                continue

            chapters.append(Chapter(
                index=len(chapters),
                title=self._clean_title(title),
                content=content,
                level=min(level, 3),
            ))

        return chapters

    def _html_to_text(self, soup: BeautifulSoup) -> str:
        # 移除脚注、图片 alt、script、style
        for tag in soup(["script", "style", "aside", "figure"]):
            tag.decompose()

        lines = []
        for element in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "blockquote"]):
            text = element.get_text(" ", strip=True)
            if text:
                lines.append(text)

        return "\n\n".join(lines)

    def _clean_title(self, title: str) -> str:
        return re.sub(r"\s+", " ", title).strip()[:100]

    def _build_toc_text(self, chapters: List[Chapter]) -> str:
        lines = []
        for ch in chapters:
            indent = "  " * (ch.level - 1)
            lines.append(f"{indent}{ch.index + 1}. {ch.title}")
        return "\n".join(lines)
