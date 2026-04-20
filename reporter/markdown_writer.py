"""
Markdown 报告生成器
将 BookAnalysis 渲染为结构完整的 Markdown 报告
"""
from datetime import datetime
from pathlib import Path

from analyzer.models import BookAnalysis, MindMapNode
from loguru import logger


class MarkdownWriter:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, analysis: BookAnalysis, model_name: str = "claude-opus-4-6") -> Path:
        """将分析结果写入 Markdown 文件，返回文件路径"""
        content = self._render(analysis, model_name)
        safe_title = self._safe_filename(analysis.book_title)
        output_path = self.output_dir / f"{safe_title}_读书报告.md"
        output_path.write_text(content, encoding="utf-8")
        logger.success(f"报告已生成：{output_path}")
        return output_path

    # ── 渲染 ──────────────────────────────────────────────────────────────────

    def _render(self, a: BookAnalysis, model_name: str) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        parts = [
            self._header(a, model_name, now),
            self._section_theme(a),
            self._section_chapters(a),
            self._section_mind_map(a),
            self._section_concepts(a),
            self._section_questions(a),
            self._section_inspirations(a),
            self._footer(),
        ]
        return "\n\n".join(p for p in parts if p)

    def _header(self, a: BookAnalysis, model: str, now: str) -> str:
        return (
            f"# 📚《{a.book_title}》深度解读报告\n\n"
            f"> **作者**：{a.author} | **生成时间**：{now} | **分析模型**：{model}"
        )

    def _section_theme(self, a: BookAnalysis) -> str:
        lines = ["---\n\n## 一、全书主题与核心要点\n\n### 核心主题\n"]
        lines.append(a.book_theme or "*（暂无）*")
        if a.core_points:
            lines.append("\n### 核心要点")
            for i, pt in enumerate(a.core_points, 1):
                lines.append(f"\n{i}. **{pt.title}**：{pt.description}")
        return "\n".join(lines)

    def _section_chapters(self, a: BookAnalysis) -> str:
        if not a.chapter_summaries:
            return ""
        lines = ["---\n\n## 二、章节概要"]
        for ch in sorted(a.chapter_summaries, key=lambda x: x.chapter_index):
            lines.append(f"\n### 第 {ch.chapter_index + 1} 章：{ch.chapter_title}")
            if ch.chapter_summary:
                lines.append(f"\n{ch.chapter_summary}")
            if ch.keywords:
                kw_str = " ".join(f"`{k}`" for k in ch.keywords[:6])
                lines.append(f"\n**关键词**：{kw_str}")
        return "\n".join(lines)

    def _section_mind_map(self, a: BookAnalysis) -> str:
        if not a.mind_map_root:
            return ""
        lines = ["---\n\n## 三、思维导图（层级大纲）\n\n```"]
        lines.append(self._render_mind_map_node(a.mind_map_root, 0))
        lines.append("```")
        return "\n".join(lines)

    def _render_mind_map_node(self, node: MindMapNode, depth: int) -> str:
        prefix = "    " * depth
        connector = "├── " if depth > 0 else ""
        result = f"{prefix}{connector}{node.name}"
        if node.detail:
            result += f"（{node.detail}）"
        children_str = "\n".join(
            self._render_mind_map_node(child, depth + 1)
            for child in node.children
        )
        if children_str:
            result += "\n" + children_str
        return result

    def _section_concepts(self, a: BookAnalysis) -> str:
        if not a.key_concepts:
            return ""
        lines = ["---\n\n## 四、关键概念及解读"]
        for c in a.key_concepts:
            lines.append(f"\n### {c.name}")
            lines.append(f"\n**解读**：{c.explanation}")
            if c.related_chapters:
                lines.append(f"\n**出现章节**：{', '.join(c.related_chapters)}")
        return "\n".join(lines)

    def _section_questions(self, a: BookAnalysis) -> str:
        if not a.key_questions:
            return ""
        lines = ["---\n\n## 五、关键问题（可供追问）"]
        for i, q in enumerate(a.key_questions, 1):
            lines.append(f"\n{i}. **{q.question}**")
            if q.context:
                lines.append(f"   > {q.context}")
        return "\n".join(lines)

    def _section_inspirations(self, a: BookAnalysis) -> str:
        if not a.inspirations:
            return ""
        lines = ["---\n\n## 六、启发与应用"]

        # 按 category 分组
        grouped: dict[str, list[str]] = {}
        for ins in a.inspirations:
            grouped.setdefault(ins.category, []).append(ins.content)

        for category, items in grouped.items():
            lines.append(f"\n### {category}")
            for item in items:
                lines.append(f"- {item}")

        if a.related_books:
            lines.append("\n### 延伸阅读")
            for book in a.related_books:
                lines.append(f"- {book}")

        return "\n".join(lines)

    def _footer(self) -> str:
        return (
            "---\n\n"
            "*本报告由 AI 自动生成，基于 Claude API 分析。"
            "建议结合原书阅读以获得完整体验。*"
        )

    def _safe_filename(self, title: str) -> str:
        """将书名转换为安全文件名"""
        for ch in r'\/:*?"<>|':
            title = title.replace(ch, "_")
        return title[:50]
